import sys
import argparse
import traceback
import logging
from datetime import datetime

from facebook_ads_uploader import config as config_module
from facebook_ads_uploader import sheet as sheet_module
from facebook_ads_uploader import facebook_api
from facebook_ads_uploader import twilio_notifier

from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("facebook_ads_uploader")


def run():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Automate Facebook Ads campaign uploads from Google Sheets."
    )
    parser.add_argument(
        "--tab",
        "-t",
        type=str,
        help="Spreadsheet tab name to use (default: today's date DD/MM).",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode for verbose output.",
    )
    parser.add_argument(
        "--platforms-config",
        type=str,
        default="platforms.yaml",
        help="Path to platforms configuration file.",
    )
    args = parser.parse_args()
    tab_name = args.tab
    debug = args.debug

    # Set logging level based on debug flag
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    # Load configuration
    try:
        config = config_module.load_config("defaults.yaml")
        platforms = config_module.load_platforms_config(args.platforms_config)
        logger.info(f"Loaded {len(platforms)} platform configurations")
        if debug and platforms:
            platform_names = ", ".join(platforms.keys())
            logger.debug(f"Loaded platforms: {platform_names}")

        if not platforms:
            logger.error(
                "No platform configurations found. Please check your platforms.yaml file."
            )
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        if debug:
            traceback.print_exc()
        sys.exit(1)

    # Determine tab name (today's date if not provided)
    if not tab_name:
        tab_name = datetime.now().strftime("%d/%m")
    display_date = tab_name.replace("/", "-")
    logger.info(f"Using spreadsheet tab: {tab_name}")

    # Fetch rows to process from Google Sheet
    try:
        worksheet, rows_to_process = sheet_module.get_rows_to_upload(
            config.get("google_sheets", {}).get(
                "credentials_file", "service_account_credentials.json"
            ),
            config.get("google_sheets", {}).get("spreadsheet_id"),
            tab_name,
        )
        logger.info(f"Retrieved {len(rows_to_process)} rows from sheet '{tab_name}'.")
    except Exception as e:
        logger.error(
            f"Error: Could not get data from Google Sheet tab '{tab_name}' - {e}"
        )
        if debug:
            traceback.print_exc()
        sys.exit(1)

    # Filter rows where 'upload' is 'yes' and 'platform' is one of our supported platforms
    filtered_rows = []
    skipped_rows_count = 0

    for row_idx, record in rows_to_process:
        upload_value = (
            str(record.get("Upload") or record.get("upload") or "").strip().lower()
        )
        # Get platform value while preserving original case
        platform_value = str(
            record.get("Platform") or record.get("platform") or ""
        ).strip()

        # Check if the platform exists in the platforms dictionary
        if upload_value == "yes" and platform_value in platforms:
            filtered_rows.append((row_idx, record))
            logger.debug(
                f"Added row {row_idx} for processing (platform: {platform_value})"
            )
        else:
            skipped_rows_count += 1

    # Log the total number of skipped rows rather than individual ones
    if skipped_rows_count > 0:
        logger.debug(f"Skipped {skipped_rows_count} rows that didn't match criteria")

    # Replace the original rows with filtered rows
    rows_to_process = filtered_rows

    if not rows_to_process:
        logger.info("No campaigns marked for upload. Exiting.")
        # Optionally send an SMS indicating nothing to do
        try:
            sms_msg = f"No Facebook campaigns to upload for {tab_name}."
            twilio_cfg = config.get("twilio")
            if twilio_cfg and all(
                twilio_cfg.get(k)
                for k in ["account_sid", "auth_token", "from_number", "to_number"]
            ):
                twilio_notifier.send_sms(
                    twilio_cfg.get("account_sid"),
                    twilio_cfg.get("auth_token"),
                    twilio_cfg.get("from_number"),
                    twilio_cfg.get("to_number"),
                    sms_msg,
                )
                logger.info("Sent SMS notification for no uploads.")
        except Exception as sms_e:
            logger.error(f"Failed to send Twilio SMS: {sms_e}")
        sys.exit(0)

    # Ensure Status and Error columns exist
    status_col_index, error_col_index = sheet_module.ensure_status_columns(worksheet)

    # Group rows by platform
    rows_by_platform = {}
    for row_idx, record in rows_to_process:
        platform_value = str(
            record.get("Platform") or record.get("platform") or ""
        ).strip()
        if platform_value not in rows_by_platform:
            rows_by_platform[platform_value] = []
        rows_by_platform[platform_value].append((row_idx, record))

    # Process each platform and prepare upload tasks
    tasks = []
    for platform, platform_rows in rows_by_platform.items():
        platform_config = platforms.get(platform, {})
        logger.info(f"Processing {len(platform_rows)} rows for platform '{platform}'")

        # Initialize Facebook API for this platform
        try:
            facebook_api.init_facebook_api(
                platform_config.get("app_id"),
                platform_config.get("app_secret"),
                platform_config.get("access_token"),
                platform_config.get("api_version"),
            )
            logger.info(f"Initialized Facebook API for platform '{platform}'")
        except Exception as e:
            logger.error(
                f"Failed to initialize Facebook API for platform '{platform}': {e}"
            )
            # Mark all rows for this platform as failed
            for row_idx, record in platform_rows:
                tasks.append(
                    (
                        row_idx,
                        None,  # No campaign name
                        None,  # No record
                        None,  # No ad account
                        None,  # No page ID
                        None,  # No pixel ID
                        platform,
                        str(e),  # Store the error message
                    )
                )
            # Skip to the next platform
            continue

        ad_account_id = platform_config.get("ad_account_id")
        page_id = platform_config.get("page_id")
        pixel_id = platform_config.get("pixel_id")

        if not ad_account_id or not page_id:
            error_msg = f"Missing required credentials for platform '{platform}'"
            logger.error(error_msg)
            # Mark all rows for this platform as failed
            for row_idx, record in platform_rows:
                tasks.append(
                    (
                        row_idx,
                        None,  # No campaign name
                        None,  # No record
                        None,  # No ad account
                        None,  # No page ID
                        None,  # No pixel ID
                        platform,
                        error_msg,  # Store the error message
                    )
                )
            # Skip to the next platform
            continue

        # Process rows for this platform
        counters = (
            {}
        )  # track counts for (topic, country_code) to assign version letters
        for row_idx, record in platform_rows:
            topic = str(record.get("Topic") or record.get("topic") or "").strip()
            country_val = record.get("Country") or record.get("country") or ""
            country_code = facebook_api.normalize_country_code(country_val)
            key = (topic, country_code)
            counters[key] = counters.get(key, 0) + 1
            version_letter = chr(ord("A") + counters[key] - 1)
            hash_id = str(record.get("Hash ID") or record.get("hash id") or "")
            campaign_name = f"{platform}_{topic}_{country_code}_Agent_{version_letter}_{display_date.replace('-', '.')}_{hash_id}"

            logger.debug(
                f"Prepared campaign '{campaign_name}' (Row {row_idx}) for upload with platform '{platform}'"
            )
            tasks.append(
                (
                    row_idx,
                    campaign_name,
                    record,
                    ad_account_id,
                    page_id,
                    pixel_id,
                    platform,
                    None,  # No error
                )
            )

    # Upload campaigns with up to 3 concurrent workers
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_task = {}
        for (
            row_idx,
            campaign_name,
            record,
            ad_account_id,
            page_id,
            pixel_id,
            platform,
            error_msg,
        ) in tasks:
            if error_msg:  # This row had a pre-execution error
                results.append((row_idx, "FAILED", error_msg))
                logger.error(
                    f"[FAILED] Row {row_idx} (Platform: {platform}) -> {error_msg}"
                )
                continue

            future = executor.submit(
                facebook_api.upload_campaign,
                ad_account_id,
                page_id,
                pixel_id,
                campaign_name,
                record,
                config,
            )
            future_to_task[future] = (row_idx, campaign_name, platform)

        for future in as_completed(future_to_task):
            row_idx, campaign_name, platform = future_to_task[future]
            try:
                campaign_id = future.result()  # raises exception if the upload failed
                results.append((row_idx, "SUCCESS", f"Campaign ID: {campaign_id}"))
                logger.info(
                    f"[SUCCESS] {campaign_name} (Row {row_idx}, Platform: {platform})"
                )
            except Exception as exc:
                err_msg = str(exc)
                results.append((row_idx, "FAILED", err_msg))
                logger.error(
                    f"[FAILED] {campaign_name} (Row {row_idx}, Platform: {platform}) -> {err_msg}"
                )
                if debug:
                    traceback.print_exc()

    # Sort results by row index (to update in order)
    results.sort(key=lambda x: x[0])

    # Update the Google Sheet with status results
    try:
        sheet_module.update_status_rows(
            worksheet, status_col_index, error_col_index, results
        )
        logger.info("Spreadsheet updated with status and error information.")
    except Exception as e:
        logger.error(f"Error updating spreadsheet statuses: {e}")
        if debug:
            traceback.print_exc()

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
    if twilio_cfg and all(
        twilio_cfg.get(k)
        for k in ["account_sid", "auth_token", "from_number", "to_number"]
    ):
        try:
            twilio_notifier.send_sms(
                twilio_cfg.get("account_sid"),
                twilio_cfg.get("auth_token"),
                twilio_cfg.get("from_number"),
                twilio_cfg.get("to_number"),
                sms_message,
            )
            logger.info("Twilio SMS sent.")
        except Exception as e:
            logger.error(f"Failed to send Twilio SMS notification: {e}")
    else:
        logger.info(
            "Twilio configuration not provided or incomplete; skipping SMS notification."
        )


if __name__ == "__main__":
    run()
