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
import logging
import os
from facebook_ads_uploader.image_downloader import download_image_from_url


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
    Supports both space-separated and pipe-separated ("|") URLs.

    Args:
        media_value: String that may contain multiple URLs separated by whitespace or |

    Returns:
        List of media URLs
    """
    if not media_value:
        return []

    # First try splitting by " | " and strip each value
    if " | " in media_value:
        urls = [url.strip() for url in str(media_value).split(" | ") if url.strip()]
        logger.debug(f"Extracted {len(urls)} media URLs using pipe separator")
        return urls

    # If no "|" found, split by whitespace
    urls = [url.strip() for url in str(media_value).split() if url.strip()]
    logger.debug(f"Extracted {len(urls)} media URLs using space separator")
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


def convert_google_drive_url_for_facebook(url: str) -> str:
    """
    Convert Google Drive URLs to direct download URLs when possible.

    Args:
        url: The Google Drive URL to convert

    Returns:
        A direct download URL if conversion is possible, otherwise the original URL
    """
    if not is_google_drive_url(url):
        return url

    # Example of converting to direct download URL for public files
    # Format: https://drive.google.com/file/d/FILE_ID/view -> https://drive.google.com/uc?export=view&id=FILE_ID
    if "/file/d/" in url:
        try:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        except Exception as e:
            logger.warning(f"Failed to convert Google Drive URL: {e}")

    # Return original URL if we can't convert it
    logger.warning(
        f"Using original Google Drive URL: {url} - this may not work with Facebook API"
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

    logger.info(
        f"Creating campaign '{campaign_name}' with {len(media_urls)} media items"
    )

    # Track resources for cleanup in case of failure
    campaign_id = None
    adset_id = None
    creative_ids = []
    ad_ids = []
    temp_files = []  # Track temporary files to clean up

    try:
        ad_account = AdAccount(ad_account_id)

        # 1. Create Campaign
        try:
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
            "optimization_goal": optimization_goal,
            "targeting": targeting,
            "status": campaign_status,
            "promoted_object": (
                {"pixel_id": pixel_id, "custom_event_type": "PURCHASE"}
                if pixel_id
                else None
            ),
        }

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
                # "image_crops": {},  # Add this to disable cropping
                # "crop_type": "original_dimensions",  # Add this to use original dimensions
            }

            creative_spec = {
                "page_id": page_id,
                # "instagram_actor_id": page_id,
                "link_data": link_data,
            }

            try:
                # Handle the image - different approach for direct URLs vs Google Drive
                image_hash = None
                temp_file_path = None

                if is_google_drive_url(media_url):
                    # For Google Drive URLs, download the image to a temp file first
                    try:
                        # First convert to a direct download URL format
                        converted_url = convert_google_drive_url_for_facebook(media_url)
                        logger.info(
                            f"Using converted Google Drive URL: {converted_url}"
                        )

                        # Download the image to a temporary file
                        temp_file_path = download_image_from_url(converted_url)
                        temp_files.append(temp_file_path)  # Track for cleanup

                        # Upload the image to Facebook to get a hash
                        image = AdImage(parent_id=ad_account_id)
                        image[AdImage.Field.filename] = temp_file_path
                        image.remote_create()
                        image_hash = image[AdImage.Field.hash]

                        # Use the image hash in the creative
                        creative_spec["link_data"]["image_hash"] = image_hash
                        logger.info(
                            f"Successfully uploaded image and got hash: {image_hash}"
                        )
                    except Exception as img_error:
                        logger.error(
                            f"Error processing Google Drive image: {str(img_error)}"
                        )
                        raise
                elif media_url.startswith("http://") or media_url.startswith(
                    "https://"
                ):
                    # For direct URLs that are not Google Drive, try using them directly
                    # If that fails, fall back to downloading and uploading
                    try:
                        # First try using the URL directly
                        creative_spec["link_data"]["picture"] = media_url
                    except Exception:
                        # If direct URL fails, download and upload it
                        logger.info(
                            f"Direct URL failed, downloading image from: {media_url}"
                        )
                        temp_file_path = download_image_from_url(media_url)
                        temp_files.append(temp_file_path)  # Track for cleanup

                        # Upload the image to Facebook to get a hash
                        image = AdImage(parent_id=ad_account_id)
                        image[AdImage.Field.filename] = temp_file_path
                        image.remote_create()
                        image_hash = image[AdImage.Field.hash]

                        # Use the image hash in the creative
                        creative_spec["link_data"]["image_hash"] = image_hash
                        logger.info(f"Used downloaded image and got hash: {image_hash}")
                else:
                    # If it's a local file path
                    image = AdImage(parent_id=ad_account_id)
                    image[AdImage.Field.filename] = media_url
                    image.remote_create()
                    image_hash = image[AdImage.Field.hash]
                    creative_spec["link_data"]["image_hash"] = image_hash

                # Create the ad creative with the image
                creative = ad_account.create_ad_creative(
                    params={
                        "name": f"{campaign_name} Creative {i + 1}",
                        "object_story_spec": creative_spec,
                    }
                )
                creative_id = creative["id"]
                creative_ids.append(creative_id)
                logger.info(
                    f"Created creative {i+1} with ID {creative_id} for media URL: {media_url}"
                )

                # Create ad
                ad = ad_account.create_ad(
                    params={
                        "name": f"{campaign_name} Ad {i + 1}",
                        "adset_id": adset_id,
                        "creative": {"creative_id": creative_id},
                        "status": ad_status,
                    }
                )
                ad_id = ad["id"]
                ad_ids.append(ad_id)
                logger.info(f"Created ad {i+1} with ID {ad_id}")
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
