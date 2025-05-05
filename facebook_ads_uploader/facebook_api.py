from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError
import urllib.parse
import re

# Mapping for common country names to ISO country codes
COUNTRY_NAME_TO_CODE = {
    "united kingdom": "GB",
    "united states": "US",
    "australia": "AU",
    "new zealand": "NZ",
    "canada": "CA",
    "ireland": "IE",
    "united arab emirates": "AE",
    "uae": "AE",
    "mexico": "MX",
    "germany": "DE",
    "spain": "ES",
    "italy": "IT",
    "chile": "CL",
}


def init_facebook_api(
    app_id: str, app_secret: str, access_token: str, api_version: str = None
):
    """
    Initialize the Facebook Marketing API with provided credentials.
    """
    if api_version:
        FacebookAdsApi.init(app_id, app_secret, access_token, api_version=api_version)
    else:
        FacebookAdsApi.init(app_id, app_secret, access_token)
    # No return needed; global state is initialized


def normalize_country_code(country_value: str) -> str:
    """
    Normalize a country name or code to a two-letter ISO country code.
    """
    if not country_value:
        return ""
    country_value = str(country_value).strip()
    # If already 2 letters, assume it's a code
    if len(country_value) == 2:
        return country_value.upper()
    # Try to map full country name to code
    code = COUNTRY_NAME_TO_CODE.get(country_value.lower())
    if code:
        return code
    # Fallback: take first letters of words (for unexpected inputs)
    parts = country_value.split()
    if len(parts) > 1:
        return (parts[0][0] + parts[1][0]).upper()
    else:
        return country_value[:2].upper()


def get_device_targeting_specs(targeting_option: str) -> dict:
    """
    Convert device targeting option to the appropriate Facebook targeting specification.

    Args:
        targeting_option: One of 'all', 'android_only', 'ios_only'

    Returns:
        Dictionary with Facebook-compatible device targeting specifications
    """
    base_spec = {}

    # Always target mobile devices
    base_spec["device_platforms"] = ["mobile"]

    if targeting_option == "android_only":
        base_spec["user_os"] = ["Android"]
    elif targeting_option == "ios_only":
        base_spec["user_os"] = ["iOS"]
    # For "all", we don't need to specify user_os

    return base_spec


def extract_media_urls(media_value: str) -> list:
    """
    Extract multiple media URLs from the media field.

    Args:
        media_value: String that may contain multiple URLs separated by whitespace

    Returns:
        List of media URLs
    """
    if not media_value:
        return []

    # Split by whitespace and filter empty strings
    urls = [url.strip() for url in str(media_value).split() if url.strip()]
    return urls


def modify_landing_page_url(base_url: str, query: str, layer_index: int = 0) -> str:
    """
    Modify landing page URL to increment the channel parameter for each ad layer.

    Args:
        base_url: The base landing page URL with placeholders
        query: The search query to append
        layer_index: The index of the current ad layer (0-based)

    Returns:
        Modified URL with incremented channel parameter
    """
    # Encode the query
    encoded_query = urllib.parse.quote_plus(str(query))

    # If this is the first layer (index 0), use the URL as is
    if layer_index == 0:
        return base_url + encoded_query

    # For subsequent layers, increment the YYY channel parameter
    # Find the channel parameter in the URL
    channel_match = re.search(r"channel=([A-Za-z]+)(\d+)", base_url)

    if channel_match:
        # Extract the channel prefix and number
        channel_prefix = channel_match.group(1)
        channel_num = int(channel_match.group(2))

        # Increment the channel number
        new_channel_num = channel_num + layer_index

        # Replace the old channel with the new one
        new_url = base_url.replace(
            f"channel={channel_prefix}{channel_num}",
            f"channel={channel_prefix}{new_channel_num}",
        )

        return new_url + encoded_query
    else:
        # If no channel parameter with number found, just use the base URL
        return base_url + encoded_query


def upload_campaign(
    ad_account_id: str,
    page_id: str,
    pixel_id: str,
    campaign_name: str,
    row_data: dict,
    defaults: dict,
):
    """
    Create a Facebook campaign, ad set, and ad according to the row_data and defaults.
    Returns the created Campaign ID on success, or raises an Exception on failure.

    Now supports:
    - Multiple ad layers from multiple media URLs
    - Device targeting (Android, iOS, or both)
    - Special ad categories from the spreadsheet
    - Auto-incrementing landing page channel for each ad layer
    """
    # Load default settings
    campaign_defaults = defaults.get("campaign", {})
    adset_defaults = defaults.get("ad_set", {})
    ad_defaults = defaults.get("ad", {})

    # Basic campaign settings
    objective = campaign_defaults.get("objective", "OUTCOME_SALES")
    buying_type = campaign_defaults.get("buying_type", "AUCTION")
    campaign_status = campaign_defaults.get("status", "ACTIVE")

    # Get special ad categories from row data if available
    special_ad_categories = []
    special_ad_category_column = row_data.get("Special Ad Category") or row_data.get(
        "special ad category"
    )
    if special_ad_category_column:
        # Parse value as comma-separated list and uppercase each item
        categories = [
            cat.strip().upper()
            for cat in str(special_ad_category_column).split(",")
            if cat.strip()
        ]
        special_ad_categories = categories

    # Ad set settings
    daily_budget = adset_defaults.get("daily_budget", 1000)
    billing_event = adset_defaults.get("billing_event", "IMPRESSIONS")
    bid_strategy = adset_defaults.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP")
    optimization_goal = adset_defaults.get("optimization_goal", "OFFSITE_CONVERSIONS")
    promoted_object = adset_defaults.get("promoted_object", {})
    if pixel_id and "pixel_id" in promoted_object:
        promoted_object["pixel_id"] = pixel_id

    # Get targeting template and device targeting
    targeting_template = dict(adset_defaults.get("targeting", {}))
    device_targeting_option = targeting_template.get("device_targeting", "all")

    # Check if device targeting is specified in the row
    row_device_targeting = row_data.get("Device Targeting") or row_data.get(
        "device targeting"
    )
    if row_device_targeting:
        row_device_targeting = str(row_device_targeting).strip().lower()
        if row_device_targeting in ["all", "android_only", "ios_only"]:
            device_targeting_option = row_device_targeting

    # Apply device targeting specifications
    device_specs = get_device_targeting_specs(device_targeting_option)
    for key, value in device_specs.items():
        targeting_template[key] = value

    # Ad settings
    ad_status = ad_defaults.get("status", "ACTIVE")
    call_to_action_type = ad_defaults.get("call_to_action_type", "LEARN_MORE")

    # Prepare ad creative fields from the row
    primary_text = row_data.get("Body", "") or row_data.get("body", "")
    headline = row_data.get("Title", "") or row_data.get("title", "")
    query_text = row_data.get("Query", "") or row_data.get("query", "")
    landing_page_prefix = defaults.get("landing_page_prefix")
    if not landing_page_prefix:
        raise RuntimeError("Landing page prefix URL is not configured in defaults.")

    # Get all media URLs
    media_urls = []
    for key in row_data.keys():
        if key.lower().startswith("media"):
            media_field_value = str(row_data.get(key) or "")
            if media_field_value:
                urls = extract_media_urls(media_field_value)
                if urls:
                    media_urls.extend(urls)
                    break

    if not media_urls:
        raise RuntimeError("No media URLs provided for creative.")

    campaign_id = None
    adset_id = None
    creative_ids = []
    ad_ids = []

    try:
        ad_account = AdAccount(ad_account_id)

        # 1. Create Campaign
        campaign = ad_account.create_campaign(
            params={
                "name": campaign_name,
                "objective": objective,
                "buying_type": buying_type,
                "status": campaign_status,
                "special_ad_categories": special_ad_categories,
            }
        )
        campaign_id = campaign["id"]

        # 2. Create Ad Set
        targeting = dict(targeting_template) if targeting_template else {}
        country_val = row_data.get("Country", "") or row_data.get("country", "")
        country_code = normalize_country_code(country_val)
        if country_code and country_code.upper() != "WW":
            targeting.setdefault("geo_locations", {"countries": [country_code]})

        adset_params = {
            "name": campaign_name,
            "campaign_id": campaign_id,
            "daily_budget": daily_budget,
            "billing_event": billing_event,
            "bid_strategy": bid_strategy,
            "optimization_goal": getattr(
                AdSet.OptimizationGoal, optimization_goal.lower(), optimization_goal
            ),
            "targeting": targeting,
            "status": campaign_status,
        }

        if promoted_object:
            adset_params["promoted_object"] = promoted_object

        adset = ad_account.create_ad_set(params=adset_params)
        adset_id = adset["id"]

        # 3. Create multiple Ad Creatives and Ads (one for each media URL)
        for i, media_url in enumerate(media_urls):
            # Generate landing page URL with incremented channel for each layer
            landing_page_url = modify_landing_page_url(
                landing_page_prefix, query_text, i
            )

            # Create ad creative
            link_data = {
                "message": primary_text,
                "link": landing_page_url,
                "name": headline,
                "call_to_action": {
                    "type": call_to_action_type,
                    "value": {"link": landing_page_url},
                },
            }

            creative_spec = {"page_id": page_id, "link_data": link_data}

            if media_url.startswith("http://") or media_url.startswith("https://"):
                # Use media URL directly
                creative_spec["link_data"]["picture"] = media_url
            else:
                # Upload local image and use its hash
                img = AdImage(parent_id=ad_account_id)
                img[AdImage.Field.filename] = media_url
                img.remote_create()
                image_hash = img[AdImage.Field.hash]
                creative_spec["link_data"]["image_hash"] = image_hash

            creative = ad_account.create_ad_creative(
                params={
                    "name": f"{campaign_name} Creative {i + 1}",
                    "object_story_spec": creative_spec,
                }
            )
            creative_id = creative["id"]
            creative_ids.append(creative_id)

            # Create ad
            ad = ad_account.create_ad(
                params={
                    "name": f"{campaign_name} Ad {i + 1}",
                    "adset_id": adset_id,
                    "creative": {"creative_id": creative_id},
                    "status": ad_status,
                }
            )
            ad_ids.append(ad["id"])

        return campaign_id

    except Exception as e:
        # If any step fails, attempt cleanup
        try:
            # Delete any created ads
            for ad_id in ad_ids:
                Ad(ad_id).api_delete()
        except Exception:
            pass

        try:
            # Delete any created creatives
            for creative_id in creative_ids:
                AdCreative(creative_id).api_delete()
        except Exception:
            pass

        try:
            # Delete the campaign (will also delete ad sets)
            if campaign_id:
                Campaign(campaign_id).api_delete()
        except Exception:
            pass

        raise
