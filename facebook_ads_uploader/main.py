import sys
import argparse
import traceback
from datetime import datetime

from facebook_ads_uploader import config as config_module
from facebook_ads_uploader import sheet as sheet_module
from facebook_ads_uploader import facebook_api
from facebook_ads_uploader import twilio_notifier

from concurrent.futures import ThreadPoolExecutor, as_completed


def run():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Automate Facebook Ads campaign uploads from Google Sheets."
    )
    parser.add_argument(
        "--tab",
        "-t",
        type=str,
        help="Spreadsheet tab name to use (default: today’s date DD/MM).",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode for verbose output.",
    )
    args = parser.parse_args()
    tab_name = args.tab
    debug = args.debug

    # Load configuration
    try:
        config = config_module.load_config("defaults.yaml")
    except Exception as e:
        print("Failed to load configuration:", e)
        sys.exit(1)

    # Determine tab name (today's date if not provided)
    if not tab_name:
        tab_name = datetime.now().strftime("%d/%m")
    display_date = tab_name.replace("/", "-")

    # Fetch rows to process from Google Sheet
    try:
        worksheet, rows_to_process = sheet_module.get_rows_to_upload(
            config["google_sheets"]["credentials_file"],
            config["google_sheets"]["spreadsheet_id"],
            tab_name,
        )
    except Exception as e:
        print(f"Error: Could not get data from Google Sheet tab '{tab_name}' - {e}")
        sys.exit(1)

    if debug:
        print(f"Retrieved {len(rows_to_process)} rows from sheet '{tab_name}'.")

    # Filter rows where 'upload' is 'yes' and 'platform' is 'fb api'
    filtered_rows = []
    for row_idx, record in rows_to_process:
        upload_value = (
            str(record.get("Upload") or record.get("upload") or "").strip().lower()
        )
        platform_value = (
            str(record.get("Platform") or record.get("platform") or "").strip().lower()
        )

        if upload_value == "yes" and platform_value == "fb api":
            filtered_rows.append((row_idx, record))
        elif debug:
            reason = []
            if upload_value != "yes":
                reason.append(f"'upload' is '{upload_value}' not 'yes'")
            if platform_value != "fb api":
                reason.append(f"'platform' is '{platform_value}' not 'fb api'")
            print(f"Skipping row {row_idx}: {', '.join(reason)}")

    # Replace the original rows with filtered rows
    rows_to_process = filtered_rows

    if not rows_to_process:
        if debug:
            print("No campaigns marked for upload. Exiting.")
        # Optionally send an SMS indicating nothing to do
        try:
            sms_msg = f"No Facebook campaigns to upload for {tab_name}."
            twilio_cfg = config.get("twilio")
            if twilio_cfg:
                twilio_notifier.send_sms(
                    twilio_cfg.get("account_sid"),
                    twilio_cfg.get("auth_token"),
                    twilio_cfg.get("from_number"),
                    twilio_cfg.get("to_number"),
                    sms_msg,
                )
            if debug:
                print("Sent SMS notification for no uploads.")
        except Exception as sms_e:
            if debug:
                print("Failed to send Twilio SMS:", sms_e)
        sys.exit(0)

    # Ensure Status and Error columns exist
    status_col_index, error_col_index = sheet_module.ensure_status_columns(worksheet)

    # Initialize Facebook API
    fb_cfg = config.get("facebook", {})
    try:
        facebook_api.init_facebook_api(
            fb_cfg.get("app_id"),
            fb_cfg.get("app_secret"),
            fb_cfg.get("access_token"),
            fb_cfg.get("api_version"),
        )
    except Exception as e:
        print("Failed to initialize Facebook API:", e)
        sys.exit(1)
    ad_account_id = fb_cfg.get("ad_account_id")
    page_id = fb_cfg.get("page_id")
    pixel_id = fb_cfg.get("pixel_id")

    # Prepare upload tasks
    tasks = []
    counters = {}  # track counts for (topic, country_code) to assign version letters
    for row_idx, record in rows_to_process:
        topic = str(record.get("Topic") or record.get("topic") or "").strip()
        country_val = record.get("Country") or record.get("country") or ""
        country_code = facebook_api.normalize_country_code(country_val)
        key = (topic, country_code)
        counters[key] = counters.get(key, 0) + 1
        version_letter = chr(ord("A") + counters[key] - 1)
        hash_id = str(record.get("Hash ID") or record.get("hash id") or "")
        campaign_name = (
            f"{topic}_{country_code}_Agent_{version_letter}_{display_date}_{hash_id}"
        )
        if debug:
            print(f"Prepared campaign '{campaign_name}' (Row {row_idx}) for upload.")
        tasks.append((row_idx, campaign_name, record))

    # Upload campaigns with up to 3 concurrent workers
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_task = {}
        for row_idx, campaign_name, record in tasks:
            future = executor.submit(
                facebook_api.upload_campaign,
                ad_account_id,
                page_id,
                pixel_id,
                campaign_name,
                record,
                config,
            )
            future_to_task[future] = (row_idx, campaign_name)
        for future in as_completed(future_to_task):
            row_idx, campaign_name = future_to_task[future]
            try:
                future.result()  # raises exception if the upload failed
                results.append((row_idx, "SUCCESS", ""))
                if debug:
                    print(f"[SUCCESS] {campaign_name} (Row {row_idx})")
            except Exception as exc:
                err_msg = str(exc)
                results.append((row_idx, "FAILED", err_msg))
                if debug:
                    print(f"[FAILED] {campaign_name} (Row {row_idx}) -> {err_msg}")
                    traceback.print_exc()

    # Sort results by row index (to update in order)
    results.sort(key=lambda x: x[0])

    # Update the Google Sheet with status results
    try:
        sheet_module.update_status_rows(
            worksheet, status_col_index, error_col_index, results
        )
        if debug:
            print("Spreadsheet updated with status and error information.")
    except Exception as e:
        print("Error updating spreadsheet statuses:", e)

    # Compose SMS summary
    total = len(results)
    success_count = sum(1 for _, status, _ in results if status == "SUCCESS")
    fail_count = sum(1 for _, status, _ in results if status == "FAILED")
    sms_message = f"FB Ads upload complete: {success_count} succeeded, {fail_count} failed out of {total}."
    if fail_count > 0:
        error_texts = []
        for _, status, error in results:
            if status == "FAILED":
                err = error or ""
                if len(err) > 100:
                    err = err[:97] + "..."
                error_texts.append(err)
        if error_texts:
            error_summary = " | ".join(error_texts)
            if len(error_summary) > 300:
                error_summary = error_summary[:297] + "..."
            sms_message += " Errors: " + error_summary

    # Send Twilio SMS
    twilio_cfg = config.get("twilio")
    if twilio_cfg:
        try:
            twilio_notifier.send_sms(
                twilio_cfg.get("account_sid"),
                twilio_cfg.get("auth_token"),
                twilio_cfg.get("from_number"),
                twilio_cfg.get("to_number"),
                sms_message,
            )
            if debug:
                print("Twilio SMS sent.")
        except Exception as e:
            print("Failed to send Twilio SMS notification:", e)
    else:
        if debug:
            print("Twilio configuration not provided; skipping SMS notification.")


if __name__ == "__main__":
    run()
