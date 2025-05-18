from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError
import urllib.parse
from urllib.parse import urlparse, parse_qs
import re
import logging
import os
import tempfile
import subprocess
import time
from facebook_ads_uploader.image_downloader import download_image_from_url
from facebook_ads_uploader.video_downloader import download_video_from_url
from facebook_ads_uploader.video_thumbnail import extract_video_thumbnail


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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

# List of EU country codes for DSA compliance checks
EU_COUNTRIES = [
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
]


# Custom exceptions
class FacebookAPIError(Exception):
    """Base exception for Facebook API errors."""

    pass


class FacebookAPIInitError(FacebookAPIError):
    """Exception raised when Facebook API initialization fails."""

    pass


class FacebookCampaignCreationError(FacebookAPIError):
    """Exception raised when campaign creation fails."""

    pass


class FacebookAdSetCreationError(FacebookAPIError):
    """Exception raised when ad set creation fails."""

    pass


class FacebookCreativeError(FacebookAPIError):
    """Exception raised when ad creative creation fails."""

    pass


class FacebookAdCreationError(FacebookAPIError):
    """Exception raised when ad creation fails."""

    pass


def get_optimization_goal_enum(optimization_goal_string: str):
    """
    Convert a string optimization goal to the corresponding AdSet.OptimizationGoal enum value.

    Args:
        optimization_goal_string: String representation of optimization goal

    Returns:
        The corresponding AdSet.OptimizationGoal enum value or the original string if no match
    """
    # Create a mapping of string values to enum values
    optimization_goals = {
        "NONE": AdSet.OptimizationGoal.none,
        "APP_INSTALLS": AdSet.OptimizationGoal.app_installs,
        "AD_RECALL_LIFT": AdSet.OptimizationGoal.ad_recall_lift,
        "ENGAGED_USERS": AdSet.OptimizationGoal.engaged_users,
        "EVENT_RESPONSES": AdSet.OptimizationGoal.event_responses,
        "IMPRESSIONS": AdSet.OptimizationGoal.impressions,
        "LEAD_GENERATION": AdSet.OptimizationGoal.lead_generation,
        "QUALITY_LEAD": AdSet.OptimizationGoal.quality_lead,
        "LINK_CLICKS": AdSet.OptimizationGoal.link_clicks,
        "OFFSITE_CONVERSIONS": AdSet.OptimizationGoal.offsite_conversions,
        "PAGE_LIKES": AdSet.OptimizationGoal.page_likes,
        "POST_ENGAGEMENT": AdSet.OptimizationGoal.post_engagement,
        "QUALITY_CALL": AdSet.OptimizationGoal.quality_call,
        "REACH": AdSet.OptimizationGoal.reach,
        "LANDING_PAGE_VIEWS": AdSet.OptimizationGoal.landing_page_views,
        "VISIT_INSTAGRAM_PROFILE": AdSet.OptimizationGoal.visit_instagram_profile,
        "VALUE": AdSet.OptimizationGoal.value,
        "THRUPLAY": AdSet.OptimizationGoal.thruplay,
        "DERIVED_EVENTS": AdSet.OptimizationGoal.derived_events,
        "APP_INSTALLS_AND_OFFSITE_CONVERSIONS": AdSet.OptimizationGoal.app_installs_and_offsite_conversions,
        "CONVERSATIONS": AdSet.OptimizationGoal.conversations,
        "IN_APP_VALUE": AdSet.OptimizationGoal.in_app_value,
        "MESSAGING_PURCHASE_CONVERSION": AdSet.OptimizationGoal.messaging_purchase_conversion,
        "SUBSCRIBERS": AdSet.OptimizationGoal.subscribers,
        "REMINDERS_SET": AdSet.OptimizationGoal.reminders_set,
        "MEANINGFUL_CALL_ATTEMPT": AdSet.OptimizationGoal.meaningful_call_attempt,
        "PROFILE_VISIT": AdSet.OptimizationGoal.profile_visit,
        "PROFILE_AND_PAGE_ENGAGEMENT": AdSet.OptimizationGoal.profile_and_page_engagement,
        "ADVERTISER_SILOED_VALUE": AdSet.OptimizationGoal.advertiser_siloed_value,
        "MESSAGING_APPOINTMENT_CONVERSION": AdSet.OptimizationGoal.messaging_appointment_conversion,
    }

    # Log what we're trying to convert
    logger.debug(
        f"Converting optimization goal string '{optimization_goal_string}' to enum"
    )

    # Get the enum value or return the original string
    enum_value = optimization_goals.get(
        optimization_goal_string, optimization_goal_string
    )

    # Log the result
    if enum_value != optimization_goal_string:
        logger.debug(f"Converted to enum value: {enum_value}")
    else:
        logger.warning(
            f"No enum mapping found for optimization goal: {optimization_goal_string}"
        )

    return enum_value


def init_facebook_api(
    app_id: str, app_secret: str, access_token: str, api_version: str = None
):
    """
    Initialize the Facebook Marketing API with provided credentials.
    """
    try:
        if api_version:
            FacebookAdsApi.init(
                app_id, app_secret, access_token, api_version=api_version
            )
        else:
            FacebookAdsApi.init(app_id, app_secret, access_token)
        logger.info("Facebook API initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Facebook API: {e}")
        raise FacebookAPIInitError(
            f"Facebook API initialization failed: {str(e)}"
        ) from e


def normalize_country_code(country_value: str) -> str:
    """
    Normalize a country name or code to a two-letter ISO country code.
    Handles both single country values and comma-separated lists of countries.

    Args:
        country_value: String representing a country name, code, or comma-separated list

    Returns:
        Normalized country code or comma-separated list of country codes
    """
    if not country_value:
        return ""

    # Handle comma-separated values
    if "," in str(country_value):
        # Process each country code separately and rejoin with commas
        country_codes = []
        for single_value in str(country_value).split(","):
            normalized = normalize_single_country_code(single_value)
            if normalized:
                country_codes.append(normalized)

        # Return comma-separated string of normalized codes
        return ",".join(country_codes)
    else:
        # Process single country code
        return normalize_single_country_code(country_value)


def is_api_version_greater_equal(version: str, compare_to: str) -> bool:
    """
    Compare two API versions to determine if the first version is greater than or equal to the second version.

    Args:
        version: The version to check (e.g., "v22.0")
        compare_to: The version to compare against (e.g., "v22.0")

    Returns:
        True if version >= compare_to, False otherwise
    """
    if not version or not compare_to:
        return False

    # Remove 'v' prefix if present
    v1 = version[1:] if version.startswith("v") else version
    v2 = compare_to[1:] if compare_to.startswith("v") else compare_to

    # Split into major and minor versions
    try:
        v1_parts = [int(part) for part in v1.split(".")]
        v2_parts = [int(part) for part in v2.split(".")]

        # Compare major version first
        if v1_parts[0] > v2_parts[0]:
            return True
        elif v1_parts[0] < v2_parts[0]:
            return False

        # If major versions are equal, compare minor versions
        if len(v1_parts) > 1 and len(v2_parts) > 1:
            return v1_parts[1] >= v2_parts[1]

        # If one version doesn't have minor version, assume it's equal to 0
        return True
    except (ValueError, IndexError):
        # If parsing fails, default to False
        return False


def normalize_single_country_code(country_value: str) -> str:
    """
    Normalize a single country name or code to a two-letter ISO country code.

    Args:
        country_value: String representing a country name or code

    Returns:
        Normalized country code
    """
    if not country_value:
        return ""

    country_value = str(country_value).strip()

    # If it's "WW" or "Worldwide", return as is
    if country_value.upper() == "WW" or country_value.lower() == "worldwide":
        return "WW"

    # If already 2 letters, assume it's a code and return uppercase
    if len(country_value) == 2:
        normalized_code = country_value.upper()
        logger.debug(f"Using provided 2-letter country code: {normalized_code}")
        return normalized_code

    # Try to map full country name to code using our mapping
    code = COUNTRY_NAME_TO_CODE.get(country_value.lower())
    if code:
        logger.debug(f"Mapped country name '{country_value}' to code: {code}")
        return code

    # Fallback: take first letters of words (for unexpected inputs)
    parts = country_value.split()
    if len(parts) > 1:
        normalized_code = (parts[0][0] + parts[1][0]).upper()
        logger.debug(
            f"Created fallback country code for '{country_value}': {normalized_code}"
        )
        return normalized_code
    else:
        normalized_code = country_value[:2].upper()
        logger.debug(
            f"Created fallback country code using first 2 chars: {normalized_code}"
        )
        return normalized_code


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
    Supports comma-separated, space-separated and pipe-separated ("|") URLs.
    Filters out non-URL entries.

    Args:
        media_value: String that may contain multiple URLs separated by commas, whitespace or |

    Returns:
        List of valid media URLs
    """
    if not media_value:
        return []

    # First try splitting by comma (preferred format)
    if "," in media_value:
        items = [url.strip() for url in str(media_value).split(",") if url.strip()]
        logger.debug(f"Split media value by comma, found {len(items)} potential URLs")
    # Then try splitting by "|" (old format)
    elif "|" in media_value:
        items = [url.strip() for url in str(media_value).split("|") if url.strip()]
        logger.debug(f"Split media value by pipe, found {len(items)} potential URLs")
    else:
        # If no "," or "|" found, split by whitespace
        items = [url.strip() for url in str(media_value).split() if url.strip()]
        logger.debug(
            f"Split media value by whitespace, found {len(items)} potential URLs"
        )

    # Filter out non-URL entries - only include items that start with http:// or https://
    urls = [item for item in items if item.startswith(("http://", "https://"))]

    # Log any items that were filtered out
    if len(items) > len(urls):
        logger.warning(
            f"Filtered out {len(items) - len(urls)} invalid media URLs that didn't start with http:// or https://"
        )
        for item in items:
            if not item.startswith(("http://", "https://")):
                logger.warning(f"Invalid media URL: {item}")

    logger.debug(f"Extracted {len(urls)} valid media URLs from {len(items)} items")

    # If no valid URLs were found but there were items, log a warning
    if not urls and items:
        logger.warning(
            f"No valid URLs found in '{media_value}'. URLs must start with http:// or https://"
        )

    return urls


def is_google_drive_url(url: str) -> bool:
    """
    Determine if a URL is a Google Drive link.

    Args:
        url: The URL to check

    Returns:
        True if it's a Google Drive URL, False otherwise
    """
    return url and ("drive.google.com" in url or "docs.google.com" in url)


def extract_google_drive_id(url: str) -> str:
    """
    Extract the file ID from a Google Drive URL.
    Supports various Google Drive URL formats.

    Args:
        url: The Google Drive URL

    Returns:
        The file ID or None if it couldn't be extracted
    """
    if not url:
        return None

    # Format: https://drive.google.com/file/d/FILE_ID/view
    if "/file/d/" in url:
        try:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return file_id
        except:
            pass

    # Format: https://drive.google.com/open?id=FILE_ID
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if "id" in query_params:
        return query_params["id"][0]

    # Format: https://drive.google.com/uc?export=view&id=FILE_ID
    if parsed_url.path == "/uc" and "id" in query_params:
        return query_params["id"][0]

    return None


def convert_google_drive_url_for_facebook(url: str, media_type: str = "image") -> str:
    """
    Convert Google Drive URLs to direct download URLs when possible.

    Args:
        url: The Google Drive URL to convert
        media_type: The type of media (image or video)

    Returns:
        A direct download URL if conversion is possible, otherwise the original URL
    """
    # If it's not a Google Drive URL, check for other special cases
    if not is_google_drive_url(url):
        # Special handling for cloud storage URLs
        if "storage.googleapis.com" in url:
            logger.info(f"📦 Using direct Google Cloud Storage URL: {url}")
            return url
        if "cloudfront.net" in url or "amazonaws.com" in url:
            logger.info(f"📦 Using direct AWS URL: {url}")
            return url
        return url

    try:
        # Extract file ID using the comprehensive extraction function
        file_id = extract_google_drive_id(url)

        if file_id:
            # For videos, use the direct download URL format
            if (
                media_type.lower() == "video"
                or url.lower().endswith((".mp4", ".mov", ".avi"))
                or "/videos/" in url
            ):
                logger.info(f"🎬 Converting Google Drive video URL with ID: {file_id}")
                return f"https://drive.google.com/uc?export=download&id={file_id}"

            # For images, use the view format which is better for images
            logger.info(f"🖼️ Converting Google Drive image URL with ID: {file_id}")
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    except Exception as e:
        logger.warning(f"⚠️ Failed to convert Google Drive URL: {e}")

    # Return original URL if we can't convert it
    logger.warning(
        f"⚠️ Using original Google Drive URL: {url} - this may not work with Facebook API"
    )
    return url


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


def is_targeting_eu_country(targeting: dict) -> bool:
    """
    Determine if the targeting includes any EU country.

    Args:
        targeting: The targeting dictionary

    Returns:
        True if targeting includes any EU country, False otherwise
    """
    if not targeting or "geo_locations" not in targeting:
        return False

    geo_locations = targeting.get("geo_locations", {})
    if "countries" not in geo_locations:
        return False

    target_countries = [c.upper() for c in geo_locations.get("countries", [])]

    # Check if any target country is in the EU
    for country in target_countries:
        if country in EU_COUNTRIES:
            return True

    return False


def detect_media_type_from_url(url: str) -> str:
    """
    Detect the media type (video or image) from a URL.

    Args:
        url: The URL to analyze

    Returns:
        "video" if the URL appears to be a video, "image" otherwise
    """
    if not url:
        # Default to image if no URL provided
        return "image"

    url_lower = url.lower()
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    query = parsed_url.query.lower()

    # Special case for Facebook CDN URLs (fbcdn.net)
    if "fbcdn.net" in url_lower:
        logger.info(f"🔍 Detected Facebook CDN URL")
        # Look specifically for video indicators in Facebook CDN URLs
        if (
            any(ext in url_lower for ext in [".mp4", ".mov", ".avi"])
            or "/videos/" in url_lower
        ):
            logger.info(
                f"🔍 Detected Facebook CDN video URL based on extensions or /videos/ path"
            )
            return "video"
        # Also check for video in query params which is common in FB CDN URLs
        if "video" in url_lower or "mp4" in url_lower:
            logger.info(
                f"🔍 Detected Facebook CDN video URL based on URL containing video/mp4"
            )
            return "video"

    # Check for video file extensions in the path
    video_extensions = [
        ".mp4",
        ".mov",
        ".avi",
        ".wmv",
        ".flv",
        ".webm",
        ".mkv",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
    ]
    if any(path.endswith(ext) for ext in video_extensions):
        logger.info(f"🔍 Detected video from file extension in URL path")
        return "video"

    # Check for video extensions in query parameters
    query_params = parse_qs(query)
    for param_value in query_params.values():
        if param_value and any(
            str(val).lower().endswith(tuple(video_extensions)) for val in param_value
        ):
            logger.info(
                f"🔍 Detected video from file extension in URL query parameters"
            )
            return "video"

    # Check for video-related patterns in URL
    video_patterns = [
        "/videos/",
        "/video/",
        "video.",
        "video=",
        "video-",
        ".mp4",
        "watch?v=",
        "youtu.be",
        "youtube.com",
        "vimeo.com",
        "player",
        "stream",
        "movie",
    ]
    if any(pattern in url_lower for pattern in video_patterns):
        logger.info(f"🔍 Detected video from URL pattern matching")
        return "video"

    # Check for video hosting domains
    video_domains = [
        "youtube.com",
        "youtu.be",
        "vimeo.com",
        "dailymotion.com",
        "wistia.com",
        "vzaar.com",
        "brightcove.com",
        "jwplayer.com",
        "vidyard.com",
        "facebook.com/watch",
    ]
    if any(domain in url_lower for domain in video_domains):
        logger.info(f"🔍 Detected video from video hosting domain")
        return "video"

    # Check for image file extensions
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".svg",
        ".heic",
    ]
    if any(path.endswith(ext) for ext in image_extensions):
        logger.info(f"🔍 Detected image from file extension in URL")
        return "image"

    # Check for image patterns in URL
    image_patterns = [
        "/images/",
        "/image/",
        "image.",
        "image=",
        "image-",
        "photo",
        "picture",
        ".jpg",
        ".png",
    ]
    if any(pattern in url_lower for pattern in image_patterns):
        logger.info(f"🔍 Detected image from URL pattern matching")
        return "image"

    # Check for image hosting domains
    image_domains = [
        "flickr.com",
        "imgur.com",
        "unsplash.com",
        "pexels.com",
        "shutterstock.com",
    ]
    if any(domain in url_lower for domain in image_domains):
        logger.info(f"🔍 Detected image from image hosting domain")
        return "image"

    # Special case for Google Drive - check for video patterns in the URL or filename
    if "drive.google.com" in url_lower or "docs.google.com" in url_lower:
        if any(pattern in url_lower for pattern in video_patterns):
            logger.info(f"🔍 Detected Google Drive video URL")
            return "video"

        # Also check query parameters for file types
        query_params = parse_qs(parsed_url.query)
        if "name" in query_params and any(
            query_params["name"][0].lower().endswith(ext) for ext in video_extensions
        ):
            logger.info(f"🔍 Detected Google Drive video from query parameters")
            return "video"

    logger.info(
        f"🔍 Could not definitively identify media type from URL, defaulting to image"
    )
    # Default to image if we can't determine
    return "image"


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

    Now with proper image download and upload for Google Drive URLs.
    """
    # Validate required parameters
    if not ad_account_id:
        raise ValueError("Missing ad_account_id parameter")
    if not page_id:
        raise ValueError("Missing page_id parameter")

    # Get the API version
    api_version = os.getenv("FB_API_VERSION")
    logger.info(f"Using Facebook API version: {api_version}")

    # Get the FB_PBIA (Page-Backed Instagram Account)
    fb_pbia = os.getenv("FB_PBIA")
    if fb_pbia:
        logger.info(f"Found FB_PBIA environment variable: {fb_pbia}")

    # Check if Instagram Page ID is provided, else fallback to FB_PBIA from environment
    instagram_page_id = row_data.get("Instagram Page ID") or row_data.get(
        "instagram page id"
    )
    if not instagram_page_id and fb_pbia:
        instagram_page_id = fb_pbia
        logger.info(
            f"Using FB_PBIA from environment as Instagram Page ID: {instagram_page_id}"
        )

    # Flag to indicate if we're using Facebook Page for Instagram (PBIA)
    using_pbia = bool(fb_pbia and (instagram_page_id == fb_pbia))
    if using_pbia:
        logger.info(
            f"🔷 Will use Facebook Page-Backed Instagram Account (PBIA): {fb_pbia}"
        )

    # Extract platform from campaign name (first part before underscore)
    platform = campaign_name.split("_")[0] if "_" in campaign_name else None

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
    # Check if Daily Budget or Budget column exists in the row data and use it if available
    budget_value = (
        row_data.get("Daily Budget")
        or row_data.get("Budget")
        or row_data.get("budget")
        or row_data.get("daily budget")
    )
    if budget_value and str(budget_value).strip():
        try:
            # Convert budget to cents (minor units)
            daily_budget = int(float(str(budget_value).strip()) * 100)
            logger.info(
                f"Using budget from spreadsheet: ${budget_value} ({daily_budget} minor units)"
            )
        except (ValueError, TypeError):
            # Fallback to default budget
            daily_budget = adset_defaults.get("daily_budget", 1000)
            logger.warning(
                f"Invalid budget value '{budget_value}'. Using default: {daily_budget} minor units."
            )
    else:
        daily_budget = adset_defaults.get("daily_budget", 1000)

    billing_event = adset_defaults.get("billing_event", "IMPRESSIONS")
    bid_strategy = adset_defaults.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP")

    # Use OFFSITE_CONVERSIONS as optimization goal
    optimization_goal = adset_defaults.get("optimization_goal", "OFFSITE_CONVERSIONS")
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
    media_column_found = False

    # Check if "Media Path" or "Media Paths" columns are present and contain data
    for key in row_data.keys():
        if key.lower().startswith("media") and not key.lower() == "media paths count":
            media_field_value = str(row_data.get(key) or "")
            if media_field_value:
                media_column_found = True
                logger.info(f"Processing media from column: {key}")
                urls = extract_media_urls(media_field_value)
                if urls:
                    media_urls.extend(urls)
                    logger.info(f"Extracted {len(urls)} valid URLs from '{key}' column")
                    break
                else:
                    logger.warning(f"No valid URLs found in the '{key}' column")

    if not media_column_found:
        logger.warning("No media columns found in spreadsheet row")

    # Check if we have a Media Paths Count column to validate the number of URLs
    media_paths_count = row_data.get("Media Paths Count")
    if media_paths_count:
        try:
            expected_count = int(media_paths_count)
            if len(media_urls) != expected_count:
                logger.warning(
                    f"⚠️ Media Paths Count mismatch: expected {expected_count}, found {len(media_urls)} URLs"
                )
                if len(media_urls) < expected_count:
                    logger.warning("Some media paths may be missing or invalid")
                elif len(media_urls) > expected_count:
                    logger.warning("Extra media paths found - using all detected URLs")
            else:
                logger.info(
                    f"✅ Media Paths Count matches: {expected_count} URLs as expected"
                )
        except (ValueError, TypeError):
            logger.warning(f"Invalid Media Paths Count value: {media_paths_count}")

    # Log the extracted URLs for debugging
    logger.info(f"Found {len(media_urls)} media URLs to process")

    if not media_urls:
        raise RuntimeError(
            "No valid media URLs provided for creative. URLs must start with http:// or https://"
        )

    logger.info(
        f"Creating campaign '{campaign_name}' with {len(media_urls)} media items"
    )

    # Track resources for cleanup in case of failure
    campaign_id = None
    adset_id = None
    creative_ids = []
    ad_ids = []
    temp_files = []  # Track temporary files to clean up

    # Store DSA information for later use with ads
    targeting_eu = False
    dsa_beneficiary = None
    dsa_payor = None

    try:
        ad_account = AdAccount(ad_account_id)

        # 1. Create Campaign
        campaign_params = {
            "name": campaign_name,
            "objective": objective,
            "buying_type": buying_type,
            "status": campaign_status,
            "special_ad_categories": special_ad_categories,
        }

        try:
            campaign = ad_account.create_campaign(params=campaign_params)
            campaign_id = campaign["id"]
            logger.info(f"Created campaign '{campaign_name}' with ID {campaign_id}")
        except FacebookRequestError as e:
            error_msg = f"Facebook API error creating campaign: {e.api_error_message()}"
            logger.error(error_msg)
            raise FacebookCampaignCreationError(error_msg) from e
        except Exception as e:
            error_msg = f"Error creating campaign '{campaign_name}': {str(e)}"
            logger.error(error_msg)
            raise FacebookCampaignCreationError(error_msg) from e

        # 2. Create Ad Set
        targeting = dict(targeting_template) if targeting_template else {}

        # Remove device_targeting from the targeting dictionary since it's not a valid FB API field
        if "device_targeting" in targeting:
            del targeting["device_targeting"]

        # First check if Country_code is provided
        country_code = row_data.get("Country_code") or row_data.get("country_code")
        if not country_code:
            # Fall back to normalizing the country name
            country_val = row_data.get("Country") or row_data.get("country") or ""
            country_code = normalize_country_code(country_val)
            logger.info(
                f"Normalized country value '{country_val}' to code: {country_code}"
            )
        else:
            # Normalize the provided country code to ensure proper formatting
            country_code = normalize_country_code(country_code)
            logger.info(f"Using provided country code (normalized): {country_code}")

        if country_code and country_code.upper() != "WW":
            # Handle multiple country codes (comma-separated)
            if "," in country_code:
                # Split and clean each code
                country_codes = [
                    code.strip().upper()
                    for code in country_code.split(",")
                    if code.strip()
                ]
                logger.info(f"Processing multiple country codes: {country_codes}")

                # Validate all country codes before setting targeting
                valid_codes = []
                for code in country_codes:
                    if len(code) == 2:
                        valid_codes.append(code)
                    else:
                        logger.warning(
                            f"⚠️ Skipping invalid country code: {code} (must be 2 letters)"
                        )

                if not valid_codes:
                    logger.warning(f"⚠️ No valid country codes found in: {country_code}")
                    logger.info(f"ℹ️ Using worldwide targeting as fallback")
                else:
                    targeting.setdefault("geo_locations", {"countries": valid_codes})
                    logger.info(f"✅ Set geo targeting to countries: {valid_codes}")
            else:
                # Single country code case
                if len(country_code) == 2:
                    targeting.setdefault(
                        "geo_locations", {"countries": [country_code.upper()]}
                    )
                    logger.info(
                        f"✅ Set geo targeting to country: {country_code.upper()}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Invalid country code: {country_code} (must be 2 letters)"
                    )
                    logger.info(f"ℹ️ Using worldwide targeting as fallback")
        elif country_code.upper() == "WW":
            logger.info(f"🌎 Using worldwide targeting (WW)")
        else:
            logger.warning(
                f"⚠️ No country code provided, using worldwide targeting as fallback"
            )

        # Check if pixel ID is valid
        valid_pixel = pixel_id and isinstance(pixel_id, str) and pixel_id.strip()
        promoted_object = None
        if valid_pixel:
            promoted_object = {
                "pixel_id": pixel_id.strip(),
                "custom_event_type": "PURCHASE",
            }

        # Prepare base ad set parameters
        adset_params = {
            "name": campaign_name,
            "campaign_id": campaign_id,
            "daily_budget": daily_budget,
            "billing_event": billing_event,
            "bid_strategy": bid_strategy,
            "optimization_goal": optimization_goal,
            "targeting": targeting,
            "status": campaign_status,
        }

        # Add promoted_object if valid
        if promoted_object:
            adset_params["promoted_object"] = promoted_object

        # Check if targeting EU countries (for DSA compliance)
        targeting_eu = is_targeting_eu_country(targeting)
        if targeting_eu:
            # Get beneficiary and payor from row data or use default
            beneficiary = row_data.get("Beneficiary") or row_data.get("beneficiary")
            if not beneficiary:
                # Use default beneficiary from ad_set defaults
                beneficiary = adset_defaults.get("beneficiary", "PRISTIVO LTD")

            payor = row_data.get("Payor") or row_data.get("payor")
            if not payor:
                # Use the same value as beneficiary if no specific payor is provided
                payor = beneficiary

            # Store for later use with ads
            dsa_beneficiary = beneficiary
            dsa_payor = payor

            # Add DSA parameters as simple strings (NOT as objects with name property)
            adset_params["dsa_beneficiary"] = beneficiary
            logger.info(f"Added DSA beneficiary '{beneficiary}' for EU compliance")

            # Add dsa_payor parameter (always required for EU, even if same as beneficiary)
            adset_params["dsa_payor"] = payor
            logger.info(f"Added DSA payor '{payor}' for EU compliance")

        try:
            adset = ad_account.create_ad_set(params=adset_params)
            adset_id = adset["id"]
            logger.info(f"Created ad set with ID {adset_id}")
        except FacebookRequestError as e:
            error_msg = f"Facebook API error creating ad set: {e.api_error_message()}"
            logger.error(error_msg)
            # Clean up the campaign before raising the exception
            if campaign_id:
                try:
                    Campaign(campaign_id).api_delete()
                    logger.info(f"Deleted campaign {campaign_id} during cleanup")
                except Exception as cleanup_error:
                    logger.error(f"Error during campaign cleanup: {cleanup_error}")
            raise FacebookAdSetCreationError(error_msg) from e
        except Exception as e:
            error_msg = f"Error creating ad set: {str(e)}"
            logger.error(error_msg)
            # Clean up the campaign before raising the exception
            if campaign_id:
                try:
                    Campaign(campaign_id).api_delete()
                    logger.info(f"Deleted campaign {campaign_id} during cleanup")
                except Exception as cleanup_error:
                    logger.error(f"Error during campaign cleanup: {cleanup_error}")
            raise FacebookAdSetCreationError(error_msg) from e

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

            # Setup creative spec with appropriate actor ID configurations
            creative_spec = {
                "page_id": page_id,
                "link_data": link_data,
            }
            # Use PBIA if available
            if instagram_page_id:
                creative_spec["instagram_user_id"] = instagram_page_id

            # Check if we want to enable Instagram Page-backed identity
            instagram_page_id = row_data.get("Instagram Page ID") or row_data.get(
                "instagram page id"
            )
            if not instagram_page_id:
                # If no Instagram Page ID is provided, use Facebook Page for Instagram content
                creative_spec["use_page_actor_override"] = True

            try:
                # Handle the image - different approach for direct URLs vs Google Drive
                image_hash = None
                temp_file_path = None

                if is_google_drive_url(media_url):
                    # For Google Drive URLs, download the image to a temp file first
                    try:
                        # Use our helper function to detect media type from URL
                        auto_detected_type = detect_media_type_from_url(media_url)

                        # Check Media Type column in spreadsheet
                        media_type_column = row_data.get("Media Type", "")

                        if media_type_column and media_type_column.lower() == "video":
                            # Spreadsheet takes priority if specified
                            media_type = "video"
                            logger.info(
                                f"🎬 Using video type from Media Type column for Google Drive"
                            )
                        elif auto_detected_type == "video":
                            # URL-based detection is secondary
                            media_type = "video"
                            logger.info(
                                f"🎬 Detected video from Google Drive URL pattern"
                            )
                        else:
                            # Default to image if nothing else matches
                            media_type = "image"
                            logger.info(
                                f"🖼️ Defaulting to image type for Google Drive content"
                            )

                        logger.info(
                            f"🔍 Google Drive: determined media type: {media_type}"
                        )

                        # First convert to a direct download URL format with the correct media type
                        converted_url = convert_google_drive_url_for_facebook(
                            media_url, media_type
                        )
                        logger.info(
                            f"🔄 Using converted Google Drive URL: {converted_url}"
                        )

                        # Download the media to a temporary file, specifying the media type
                        logger.info(f"🔽 Downloading {media_type} from Google Drive...")
                        if media_type == "video":
                            temp_file_path = download_video_from_url(converted_url)
                        else:
                            temp_file_path = download_image_from_url(
                                converted_url, media_type
                            )
                        temp_files.append(temp_file_path)  # Track for cleanup
                        logger.info(f"✅ Download completed: {temp_file_path}")

                        if media_type == "video":
                            # Upload as video
                            logger.info(
                                f"🎬 Processing Google Drive content as video: {temp_file_path}"
                            )
                            video = AdVideo(parent_id=ad_account_id)
                            video[AdVideo.Field.filepath] = temp_file_path
                            video.remote_create()
                            video_id = video[AdVideo.Field.id]

                            # Use video in creative
                            video_data = {
                                "video_id": video_id,
                                "message": primary_text,
                                "call_to_action": {
                                    "type": call_to_action_type,
                                    "value": {"link": landing_page_url},
                                },
                                "title": headline,
                            }

                            # Check if Instagram Page ID is available
                            instagram_page_id = row_data.get(
                                "Instagram Page ID"
                            ) or row_data.get("instagram page id")

                            # Get the FB_PBIA from environment variables if not provided in row data
                            if not instagram_page_id and fb_pbia:
                                instagram_page_id = fb_pbia
                                logger.info(
                                    f"Using FB_PBIA from environment for creative: {instagram_page_id}"
                                )

                            # Create object story spec for both Facebook and Instagram
                            creative_spec["object_story_spec"] = {
                                "page_id": page_id,
                                "video_data": video_data,
                                "use_page_actor_override": True,  # Always enable Use Facebook Page
                            }

                            # Add Instagram actor ID or user ID based on API version
                            if instagram_page_id:
                                if is_api_version_greater_equal(api_version, "v22.0"):
                                    creative_spec["object_story_spec"][
                                        "instagram_user_id"
                                    ] = instagram_page_id
                                    logger.info(
                                        f"Using instagram_user_id for API version {api_version}"
                                    )
                                else:
                                    creative_spec["object_story_spec"][
                                        "instagram_actor_id"
                                    ] = instagram_page_id
                                    logger.info(
                                        f"Using instagram_actor_id for API version {api_version}"
                                    )

                                logger.info(
                                    f"✅ Set Instagram Page ID in Google Drive video creative: {instagram_page_id}"
                                )
                            else:
                                creative_spec["object_story_spec"] = {
                                    "page_id": page_id,
                                    "video_data": video_data,
                                }
                            # Remove link_data as we're using video_data instead
                            if "link_data" in creative_spec:
                                del creative_spec["link_data"]

                            # Create the creative with video_data
                            creative_params = {
                                "name": f"{campaign_name} Creative {i + 1}",
                                "object_story_spec": creative_spec["object_story_spec"],
                            }
                            creative = ad_account.create_ad_creative(
                                params=creative_params
                            )

                            logger.info(
                                f"✅ Successfully uploaded Google Drive video with ID: {video_id}"
                            )
                        else:
                            # Upload as image
                            logger.info(
                                f"🖼️ Processing Google Drive content as image: {temp_file_path}"
                            )
                            image = AdImage(parent_id=ad_account_id)
                            image[AdImage.Field.filename] = temp_file_path
                            image.remote_create()
                            image_hash = image[AdImage.Field.hash]

                            # Use the image hash in the creative
                            creative_spec["link_data"]["image_hash"] = image_hash

                            # Create the creative with link_data containing image hash
                            creative_params = {
                                "name": f"{campaign_name} Creative {i + 1}",
                                "object_story_spec": {
                                    "page_id": page_id,
                                    "link_data": creative_spec["link_data"],
                                },
                            }

                            # Add use_page_actor_override at the root level of creative_params, not in object_story_spec
                            if using_pbia:
                                creative_params["use_page_actor_override"] = True
                                logger.info(
                                    f"🔷 Enabling use_page_actor_override for PBIA in Google Drive image creative (root level)"
                                )

                            # Add Instagram actor ID if available
                            if instagram_page_id:
                                # Add Instagram actor ID or user ID based on API version
                                if is_api_version_greater_equal(api_version, "v22.0"):
                                    creative_params["instagram_user_id"] = (
                                        instagram_page_id
                                    )
                                    logger.info(
                                        f"Using instagram_user_id for API version {api_version}"
                                    )
                                else:
                                    creative_params["instagram_actor_id"] = (
                                        instagram_page_id
                                    )
                                    logger.info(
                                        f"Using instagram_actor_id for API version {api_version}"
                                    )

                            creative = ad_account.create_ad_creative(
                                params=creative_params
                            )

                            logger.info(
                                f"✅ Successfully uploaded Google Drive image and got hash: {image_hash}"
                            )
                    except Exception as img_error:
                        logger.error(
                            f"Error processing Google Drive image: {str(img_error)}"
                        )
                        raise
                elif media_url.startswith("http://") or media_url.startswith(
                    "https://"
                ):
                    # For direct URLs that are not Google Drive, determine the media type and handle appropriately
                    # Use our helper function to detect media type from URL
                    auto_detected_type = detect_media_type_from_url(media_url)

                    # Check Media Type column in spreadsheet
                    media_type_column = row_data.get("Media Type", "")

                    if media_type_column and media_type_column.lower() == "video":
                        # Spreadsheet takes priority if specified
                        media_type = "video"
                        logger.info(f"🎬 Using video type from Media Type column")
                    elif auto_detected_type == "video":
                        # URL-based detection is secondary
                        media_type = "video"
                        logger.info(
                            f"🎬 Detected video URL by pattern analysis: {media_url}"
                        )
                    else:
                        # Default to image if nothing else matches
                        media_type = "image"
                        logger.info(f"🖼️ Defaulting to image type")

                    logger.info(f"🔍 Final media type determined for URL: {media_type}")

                    # For Facebook CDN URLs or complex URLs, always download first instead of using directly
                    is_complex_url = "fbcdn.net" in media_url or len(media_url) > 200

                    if media_type == "video":
                        # For videos, we need to download and upload
                        logger.info(f"🎬 Processing direct URL as video: {media_url}")
                        try:
                            temp_file_path = download_video_from_url(media_url)
                            temp_files.append(temp_file_path)

                            # Verify the file exists and has content
                            if (
                                not os.path.exists(temp_file_path)
                                or os.path.getsize(temp_file_path) == 0
                            ):
                                raise RuntimeError(
                                    f"Downloaded video file is empty or does not exist: {temp_file_path}"
                                )

                            video = AdVideo(parent_id=ad_account_id)
                            video[AdVideo.Field.filepath] = temp_file_path
                            video.remote_create()
                            video_id = video[AdVideo.Field.id]

                            # Extract thumbnail from the video
                            thumbnail_path = extract_video_thumbnail(temp_file_path)
                            thumbnail_hash = None

                            if thumbnail_path:
                                try:
                                    # Upload the thumbnail as an image
                                    thumbnail_image = AdImage(parent_id=ad_account_id)
                                    thumbnail_image[AdImage.Field.filename] = (
                                        thumbnail_path
                                    )
                                    thumbnail_image.remote_create()
                                    thumbnail_hash = thumbnail_image[AdImage.Field.hash]
                                    logger.info(
                                        f"✅ Successfully uploaded video thumbnail with hash: {thumbnail_hash}"
                                    )
                                    # Add the thumbnail path to temp_files for cleanup
                                    temp_files.append(thumbnail_path)
                                except Exception as e:
                                    logger.error(
                                        f"❌ Failed to upload video thumbnail: {e}"
                                    )
                            else:
                                logger.warning(
                                    "⚠️ No thumbnail extracted from video, creative creation may fail"
                                )

                            logger.info(
                                f"✅ Successfully uploaded video with ID: {video_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"❌ Failed to download or upload video from {media_url}: {e}"
                            )
                            raise RuntimeError(
                                f"Failed to process video from URL: {media_url}. Error: {e}"
                            )

                        # Use video in creative
                        video_data = {
                            "video_id": video_id,
                            "message": primary_text,
                            "call_to_action": {
                                "type": call_to_action_type,
                                "value": {"link": landing_page_url},
                            },
                            "title": headline,
                        }

                        # Add thumbnail to video_data if available
                        if thumbnail_hash:
                            video_data["image_hash"] = thumbnail_hash
                            logger.info(
                                f"✅ Using extracted thumbnail for video creative with hash: {thumbnail_hash}"
                            )
                        else:
                            # Try to use the "Media Thumbnail" column if available
                            media_thumbnail = row_data.get("Media Thumbnail")
                            if (
                                media_thumbnail
                                and isinstance(media_thumbnail, str)
                                and media_thumbnail.startswith("http")
                            ):
                                try:
                                    logger.info(
                                        f"🖼️ Trying to use Media Thumbnail URL: {media_thumbnail}"
                                    )
                                    # Download and upload the thumbnail
                                    thumb_temp_path = download_image_from_url(
                                        media_thumbnail, "image"
                                    )
                                    temp_files.append(thumb_temp_path)

                                    thumbnail_image = AdImage(parent_id=ad_account_id)
                                    thumbnail_image[AdImage.Field.filename] = (
                                        thumb_temp_path
                                    )
                                    thumbnail_image.remote_create()
                                    thumbnail_hash = thumbnail_image[AdImage.Field.hash]

                                    video_data["image_hash"] = thumbnail_hash
                                    logger.info(
                                        f"✅ Using Media Thumbnail URL for video creative with hash: {thumbnail_hash}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"❌ Failed to use Media Thumbnail URL: {e}"
                                    )
                                    # Try using an image_url approach as a last resort
                                    try:
                                        # Use a reliable public image URL as a fallback thumbnail
                                        fallback_image_url = "https://img.freepik.com/free-vector/video-media-player-button-design_1017-30453.jpg"
                                        logger.info(
                                            f"🖼️ Using fallback image URL for thumbnail: {fallback_image_url}"
                                        )
                                        # Use image_url instead of image_hash
                                        video_data["image_url"] = fallback_image_url
                                        logger.info(
                                            f"✅ Set fallback image_url in video_data for creative"
                                        )
                                    except Exception as url_error:
                                        logger.error(
                                            f"❌ Failed to set fallback image URL: {url_error}"
                                        )
                                        logger.warning(
                                            "⚠️ Video creative will be created without a thumbnail and may fail"
                                        )
                            else:
                                logger.warning(
                                    "⚠️ No thumbnail available for video creative - trying fallback URL"
                                )
                                # Try using an image_url approach as a last resort
                                try:
                                    # Use a reliable public image URL as a fallback thumbnail
                                    fallback_image_url = "https://img.freepik.com/free-vector/video-media-player-button-design_1017-30453.jpg"
                                    logger.info(
                                        f"🖼️ Using fallback image URL for thumbnail: {fallback_image_url}"
                                    )
                                    # Use image_url instead of image_hash
                                    video_data["image_url"] = fallback_image_url
                                    logger.info(
                                        f"✅ Set fallback image_url in video_data for creative"
                                    )
                                except Exception as url_error:
                                    logger.error(
                                        f"❌ Failed to set fallback image URL: {url_error}"
                                    )
                                    logger.warning(
                                        "⚠️ Video creative will be created without a thumbnail and may fail"
                                    )

                        # Check if Instagram Page ID is available
                        instagram_page_id = row_data.get(
                            "Instagram Page ID"
                        ) or row_data.get("instagram page id")

                        # Get the FB_PBIA from environment variables if not provided in row data
                        if not instagram_page_id and fb_pbia:
                            instagram_page_id = fb_pbia
                            logger.info(
                                f"Using FB_PBIA from environment for creative: {instagram_page_id}"
                            )

                        # Create object story spec for both Facebook and Instagram
                        creative_spec["object_story_spec"] = {
                            "page_id": page_id,
                            "video_data": video_data,
                            "use_page_actor_override": True,  # Always enable Use Facebook Page
                        }

                        # Add Instagram actor ID or user ID based on API version
                        if instagram_page_id:
                            if is_api_version_greater_equal(api_version, "v22.0"):
                                creative_spec["object_story_spec"][
                                    "instagram_user_id"
                                ] = instagram_page_id
                                logger.info(
                                    f"Using instagram_user_id for API version {api_version}"
                                )
                            else:
                                creative_spec["object_story_spec"][
                                    "instagram_actor_id"
                                ] = instagram_page_id
                                logger.info(
                                    f"Using instagram_actor_id for API version {api_version}"
                                )

                            logger.info(
                                f"✅ Set Instagram Page ID in video creative: {instagram_page_id}"
                            )
                        else:
                            creative_spec["object_story_spec"] = {
                                "page_id": page_id,
                                "video_data": video_data,
                            }
                        # Remove link_data as we're using video_data instead
                        if "link_data" in creative_spec:
                            del creative_spec["link_data"]

                        # Create the ad creative using video_data
                        creative_params = {
                            "name": f"{campaign_name} Creative {i + 1}",
                            "object_story_spec": creative_spec["object_story_spec"],
                        }

                        # Create the creative
                        try:
                            creative = ad_account.create_ad_creative(
                                params=creative_params
                            )
                            logger.info(
                                f"✅ Created video creative with video ID: {video_id}"
                            )
                        except Exception as e:
                            logger.error(f"❌ Failed to create video creative: {e}")
                            logger.error(f"Creative params: {creative_params}")
                            raise RuntimeError(f"Failed to create video creative: {e}")
                    else:
                        # For Facebook CDN or complex URLs, always download first
                        if is_complex_url:
                            logger.info(
                                f"🖼️ Complex URL detected, downloading from: {media_url}"
                            )
                            temp_file_path = download_image_from_url(
                                media_url, media_type
                            )
                            temp_files.append(temp_file_path)

                            # Upload the image to Facebook to get a hash
                            image = AdImage(parent_id=ad_account_id)
                            image[AdImage.Field.filename] = temp_file_path
                            image.remote_create()
                            image_hash = image[AdImage.Field.hash]

                            # Use the image hash in the creative
                            creative_spec["link_data"]["image_hash"] = image_hash
                            logger.info(
                                f"✅ Successfully uploaded image and got hash: {image_hash}"
                            )

                            # Create the creative with link_data containing image hash
                            creative_params = {
                                "name": f"{campaign_name} Creative {i + 1}",
                                "object_story_spec": {
                                    "page_id": page_id,
                                    "link_data": creative_spec["link_data"],
                                    "use_page_actor_override": True,  # Critical for PBIA integration
                                },
                            }

                            # Add Instagram actor ID if available
                            if instagram_page_id:
                                # Add Instagram actor ID or user ID based on API version
                                if is_api_version_greater_equal(api_version, "v22.0"):
                                    creative_params["object_story_spec"][
                                        "instagram_user_id"
                                    ] = instagram_page_id
                                    logger.info(
                                        f"Using instagram_user_id for API version {api_version}"
                                    )
                                else:
                                    creative_params["object_story_spec"][
                                        "instagram_actor_id"
                                    ] = instagram_page_id
                                    logger.info(
                                        f"Using instagram_actor_id for API version {api_version}"
                                    )

                            # Create the ad creative
                            creative = ad_account.create_ad_creative(
                                params=creative_params
                            )
                            logger.info(
                                f"✅ Created image creative with PBIA integration"
                            )
                        else:
                            # For standard image URLs, try using directly first, fallback to download if needed
                            try:
                                logger.info(f"🖼️ Using image URL directly: {media_url}")
                                # This approach may not work always, so we have a fallback
                                creative_spec["link_data"]["picture"] = media_url

                                # Create the creative with link_data containing picture URL
                                creative_params = {
                                    "name": f"{campaign_name} Creative {i + 1}",
                                    "object_story_spec": {
                                        "page_id": page_id,
                                        "link_data": creative_spec["link_data"],
                                    },
                                }

                                # Add use_page_actor_override at the root level of creative_params, not in object_story_spec
                                if using_pbia:
                                    creative_params["use_page_actor_override"] = True
                                    logger.info(
                                        f"🔷 Enabling use_page_actor_override for PBIA in image creative (root level)"
                                    )

                                # Add Instagram actor ID if available
                                if instagram_page_id:
                                    # Add Instagram actor ID or user ID based on API version
                                    if is_api_version_greater_equal(
                                        api_version, "v22.0"
                                    ):
                                        creative_params["instagram_user_id"] = (
                                            instagram_page_id
                                        )
                                        logger.info(
                                            f"Using instagram_user_id for API version {api_version}"
                                        )
                                    else:
                                        creative_params["instagram_actor_id"] = (
                                            instagram_page_id
                                        )
                                        logger.info(
                                            f"Using instagram_actor_id for API version {api_version}"
                                        )

                                creative = ad_account.create_ad_creative(
                                    params=creative_params
                                )
                                logger.info(
                                    f"✅ Created creative using direct image URL"
                                )
                            except Exception as e:
                                # If direct URL fails, download and upload it
                                logger.info(
                                    f"⚠️ Direct URL failed, downloading media from: {media_url} - Error: {e}"
                                )
                                temp_file_path = download_image_from_url(
                                    media_url, media_type
                                )
                                temp_files.append(temp_file_path)  # Track for cleanup

                                # Upload the image to Facebook to get a hash
                                image = AdImage(parent_id=ad_account_id)
                                image[AdImage.Field.filename] = temp_file_path
                                image.remote_create()
                                image_hash = image[AdImage.Field.hash]

                                # Use the image hash in the creative
                                if "picture" in creative_spec["link_data"]:
                                    del creative_spec["link_data"][
                                        "picture"
                                    ]  # Remove picture URL if using hash
                                creative_spec["link_data"]["image_hash"] = image_hash

                                # Create the creative with link_data containing image hash
                                creative_params = {
                                    "name": f"{campaign_name} Creative {i + 1}",
                                    "object_story_spec": {
                                        "page_id": page_id,
                                        "link_data": creative_spec["link_data"],
                                        "use_page_actor_override": True,  # Always enable Use Facebook Page
                                    },
                                }

                                # Add Instagram actor ID if available
                                if instagram_page_id:
                                    # Add Instagram actor ID or user ID based on API version
                                    if is_api_version_greater_equal(
                                        api_version, "v22.0"
                                    ):
                                        creative_params["object_story_spec"][
                                            "instagram_user_id"
                                        ] = instagram_page_id
                                        logger.info(
                                            f"Using instagram_user_id for API version {api_version}"
                                        )
                                    else:
                                        creative_params["object_story_spec"][
                                            "instagram_actor_id"
                                        ] = instagram_page_id
                                        logger.info(
                                            f"Using instagram_actor_id for API version {api_version}"
                                        )

                                creative = ad_account.create_ad_creative(
                                    params=creative_params
                                )
                                logger.info(
                                    f"✅ Used downloaded image and got hash: {image_hash}"
                                )
                else:
                    # If it's a local file path
                    image = AdImage(parent_id=ad_account_id)
                    image[AdImage.Field.filename] = media_url
                    image.remote_create()
                    image_hash = image[AdImage.Field.hash]
                    creative_spec["link_data"]["image_hash"] = image_hash

                    # Create the ad creative with proper creative_params setup
                    creative_params = {
                        "name": f"{campaign_name} Creative {i + 1}",
                        "object_story_spec": {
                            "page_id": page_id,
                            "link_data": creative_spec["link_data"],
                        },
                    }

                    # Add use_page_actor_override at the root level of creative_params, not in object_story_spec
                    if using_pbia:
                        creative_params["use_page_actor_override"] = True
                        logger.info(
                            f"🔷 Enabling use_page_actor_override for PBIA in local image creative (root level)"
                        )

                    # Add Instagram actor ID if available
                    if instagram_page_id:
                        # Add Instagram actor ID or user ID based on API version
                        if is_api_version_greater_equal(api_version, "v22.0"):
                            creative_params["instagram_user_id"] = instagram_page_id
                            logger.info(
                                f"Using instagram_user_id for API version {api_version}"
                            )
                        else:
                            creative_params["instagram_actor_id"] = instagram_page_id
                            logger.info(
                                f"Using instagram_actor_id for API version {api_version}"
                            )

                    # Create the ad creative
                    creative = ad_account.create_ad_creative(params=creative_params)
                    logger.info(
                        f"✅ Created creative using local image file with hash: {image_hash}"
                    )

                # Get the creative ID for all paths
                if not creative:
                    logger.error(
                        f"❌ Creative was not created successfully for URL: {media_url}"
                    )
                    raise RuntimeError(
                        f"Creative was not created for media URL: {media_url}"
                    )

                creative_id = creative["id"]
                creative_ids.append(creative_id)
                logger.info(
                    f"🎨 Created creative {i+1} with ID {creative_id} for media URL: {media_url}"
                )

                # Prepare ad parameters
                ad_params = {
                    "name": f"{campaign_name} Ad {i + 1}",
                    "adset_id": adset_id,
                    "creative": {"creative_id": creative_id},
                    "status": ad_status,
                }

                # Check if Instagram Page ID is available in the platform config
                instagram_page_id = row_data.get("Instagram Page ID") or row_data.get(
                    "instagram page id"
                )

                # Get the FB_PBIA from environment variables if not provided in row data
                if not instagram_page_id and fb_pbia:
                    instagram_page_id = fb_pbia
                    logger.info(
                        f"Using FB_PBIA from environment for ad: {instagram_page_id}"
                    )

                # Re-check if we're using PBIA for this specific ad
                using_pbia_for_ad = bool(fb_pbia and (instagram_page_id == fb_pbia))

                # Set use_page_actor_override only when actually using PBIA
                if using_pbia_for_ad:
                    ad_params["use_page_actor_override"] = True
                    logger.info(f"🔷 Enabling use_page_actor_override for PBIA in ad")

                if instagram_page_id:
                    # Use Instagram Page ID
                    if is_api_version_greater_equal(api_version, "v22.0"):
                        ad_params["instagram_user_id"] = instagram_page_id
                        logger.info(
                            f"🔷 Setting ad to use Instagram User ID (v22.0+): {instagram_page_id}"
                        )
                    else:
                        ad_params["instagram_actor_id"] = instagram_page_id
                        logger.info(
                            f"🔷 Setting ad to use Instagram Actor ID (pre-v22.0): {instagram_page_id}"
                        )

                    # Add specific log for PBIA usage
                    if using_pbia_for_ad:
                        logger.info(
                            f"✅ Ad will use Facebook Page's PBIA for Instagram placement"
                        )

                # Add DSA parameters to ad level for EU targeting
                if targeting_eu and dsa_beneficiary:
                    if dsa_beneficiary:
                        ad_params["dsa_beneficiary"] = dsa_beneficiary
                    if dsa_payor:
                        ad_params["dsa_payor"] = dsa_payor

                # Create the ad with retries (sometimes FB can be flaky)
                max_retries = 3
                retry_count = 0
                ad_created = False

                while retry_count < max_retries and not ad_created:
                    try:
                        # Create ad with full error trace
                        ad = ad_account.create_ad(params=ad_params)
                        ad_id = ad["id"]
                        ad_ids.append(ad_id)
                        logger.info(
                            f"✅ Created ad {i+1} with ID {ad_id} - Facebook Page identity enabled"
                        )
                        ad_created = True
                    except FacebookRequestError as e:
                        error_msg = f"Facebook API error creating ad {i+1}: {e.api_error_message()}"
                        logger.error(error_msg)
                        logger.error(f"Full error: {e}")

                        # Increment retry counter
                        retry_count += 1

                        if retry_count < max_retries:
                            logger.info(
                                f"Retrying ad creation ({retry_count}/{max_retries})..."
                            )
                            # Wait a bit before retrying (give FB time to process)
                            import time

                            time.sleep(2)
                        else:
                            logger.error(
                                f"Failed to create ad after {max_retries} attempts"
                            )
                            # Continue with other creatives even if one fails after all retries
                            break
                    except Exception as e:
                        logger.error(f"Error creating ad {i+1}: {str(e)}")
                        # Continue with other creatives even if one fails
                        break

            except FacebookRequestError as e:
                logger.error(
                    f"Facebook API error creating creative/ad {i+1} with URL {media_url}: {e.api_error_message()}"
                )
                # Continue with other creatives even if one fails
                continue
            except Exception as e:
                logger.error(
                    f"Error creating creative/ad {i+1} with URL {media_url}: {str(e)}"
                )
                # Continue with other creatives even if one fails
                continue

        # Return campaign ID if at least one ad was created successfully
        if ad_ids:
            return campaign_id
        else:
            raise RuntimeError("Failed to create any ads for this campaign")

    except Exception as e:
        logger.error(f"Error creating campaign '{campaign_name}': {e}")
        # If any step fails, attempt cleanup
        try:
            # Delete any created ads
            for ad_id in ad_ids:
                try:
                    Ad(ad_id).api_delete()
                    logger.info(f"Deleted ad {ad_id} during cleanup")
                except Exception as cleanup_error:
                    logger.error(f"Error during ad cleanup: {cleanup_error}")

            # Delete any created creatives
            for creative_id in creative_ids:
                try:
                    AdCreative(creative_id).api_delete()
                    logger.info(f"Deleted creative {creative_id} during cleanup")
                except Exception as cleanup_error:
                    logger.error(f"Error during creative cleanup: {cleanup_error}")

            # Delete the campaign (will also delete ad sets)
            if campaign_id:
                try:
                    Campaign(campaign_id).api_delete()
                    logger.info(f"Deleted campaign {campaign_id} during cleanup")
                except Exception as cleanup_error:
                    logger.error(f"Error during campaign cleanup: {cleanup_error}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")

        # Always clean up temporary files
        finally:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.info(f"Removed temporary file: {temp_file}")
                except Exception as file_cleanup_error:
                    logger.error(f"Error removing temporary file: {file_cleanup_error}")

        # Re-raise the original exception
        raise

    except Exception as e:
        logger.error(f"❌ Error creating placeholder thumbnail: {e}")
        return None
