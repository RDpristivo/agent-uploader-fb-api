"""
MCP Tool Implementation for Facebook Ads Uploader

This module implements a custom function that can be exposed through Claude's
Model Context Protocol (MCP) to allow Claude to create Facebook ad campaigns
directly from conversations.
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from facebook_ads_uploader import config as config_module
from facebook_ads_uploader import facebook_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def sanitize_string(s):
    """Sanitize a string for use in a filename or URL"""
    if not s:
        return ""
    # Replace spaces and special characters with underscores
    return "".join(c if c.isalnum() else "_" for c in str(s))


def extract_google_drive_id(url):
    """
    Extract the file ID from a Google Drive URL.
    Supports various Google Drive URL formats.
    """
    if not url or "drive.google.com" not in url:
        return None

    parsed_url = urlparse(url)

    # Format: https://drive.google.com/file/d/FILE_ID/view
    if "file/d/" in url:
        file_id = url.split("file/d/")[1].split("/")[0]
        return file_id

    # Format: https://drive.google.com/open?id=FILE_ID
    query_params = parse_qs(parsed_url.query)
    if "id" in query_params:
        return query_params["id"][0]

    return None


def create_maximizer_campaign(
    topic: str,
    country: str,
    title: str,
    body: str,
    query: str = None,
    media_path: str = None,
    extra_prompt: str = None,
):
    """
    Create a Facebook ad campaign directly through MCP function calls.

    Args:
        topic: Campaign topic/name
        country: Target country (name or 2-letter code)
        title: Ad headline
        body: Ad primary text
        query: Search query for landing page URL (optional)
        media_path: Image URL(s) separated by pipes (|) (optional)
        extra_prompt: Additional configuration options (optional)

    Returns:
        Dict containing status and details of the operation
    """
    logger.info(f"Creating campaign for topic: {topic}, country: {country}")

    try:
        # Load configuration
        config = config_module.load_config("defaults.yaml")
        platforms = config_module.load_platforms_config("platforms.yaml")

        # Use fb api as default platform
        platform_id = "fb api"

        # Parse extra_prompt for additional configuration
        extra_config = {}
        if extra_prompt:
            # Example format: "platform: fb api 2, device: ios_only"
            parts = [p.strip() for p in extra_prompt.split(",")]
            for part in parts:
                if ":" in part:
                    key, value = [p.strip() for p in part.split(":", 1)]
                    extra_config[key.lower()] = value

            # Check if platform is specified
            if "platform" in extra_config and extra_config["platform"] in platforms:
                platform_id = extra_config["platform"]
                logger.info(f"Using specified platform: {platform_id}")

        # Get platform configuration
        platform_config = platforms.get(platform_id)
        if not platform_config:
            return {
                "status": "error",
                "message": f"Platform '{platform_id}' not found in configuration",
            }

        # Initialize Facebook API
        facebook_api.init_facebook_api(
            platform_config.get("app_id"),
            platform_config.get("app_secret"),
            platform_config.get("access_token"),
            platform_config.get("api_version"),
        )

        # Create a record dict similar to what we'd get from the spreadsheet
        record = {
            "Topic": topic,
            "Country": country,
            "Title": title,
            "Body": body,
            "Query": query or "",
            "Media Path": media_path or "",
            "Special Ad Category": extra_config.get("special_ad_category", ""),
        }

        # Add device targeting if specified
        if "device" in extra_config and extra_config["device"].lower() in [
            "all",
            "android_only",
            "ios_only",
        ]:
            record["Device Targeting"] = extra_config["device"]

        # Generate a campaign name
        display_date = datetime.now().strftime("%d-%m")
        country_code = facebook_api.normalize_country_code(country)
        campaign_name = (
            f"{sanitize_string(topic)}_{country_code}_Agent_A_{display_date}"
        )

        # Process media URLs - if they're Google Drive links, note that they need special handling
        if media_path and "drive.google.com" in media_path:
            # Note: In a production environment, you would implement a function to
            # download from Google Drive using the Drive API and the file ID
            logger.warning(
                "Google Drive links require additional authentication - will use URL directly"
            )

        # Upload campaign
        ad_account_id = platform_config.get("ad_account_id")
        page_id = platform_config.get("page_id")
        pixel_id = platform_config.get("pixel_id")

        campaign_id = facebook_api.upload_campaign(
            ad_account_id,
            page_id,
            pixel_id,
            campaign_name,
            record,
            config,
        )

        return {
            "status": "success",
            "message": f"Campaign '{campaign_name}' created successfully",
            "campaign_id": campaign_id,
            "platform": platform_id,
            "ad_account_id": ad_account_id,
        }

    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        return {"status": "error", "message": str(e)}


def ping():
    """
    Simple function to check if the MCP server is responding.

    Returns:
        Dict with status message
    """
    return {"status": "ok", "message": "Facebook Ads Uploader MCP tool is running"}
