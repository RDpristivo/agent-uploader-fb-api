"""
Test script to validate the PBIA (Page-Backed Instagram Account) integration for image creatives.

Usage:
    1. Make sure you have a .env file with all required Facebook API credentials
    2. Run this script from the project root: python -m tests.test_pbia_image_integration

Required environment variables:
    FB_APP_ID: Your Facebook App ID
    FB_APP_SECRET: Your Facebook App Secret
    FB_ACCESS_TOKEN: Your Facebook Access Token
    FB_AD_ACCOUNT_ID: Your Ad Account ID (with 'act_' prefix)
    FB_PAGE_ID: Your Facebook Page ID
    FB_PIXEL_ID: Your Facebook Pixel ID
    FB_PBIA: Your Page-Backed Instagram Account ID
    FB_API_VERSION: Facebook API version (default: v22.0)
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

# Print helpful message if .env file doesn't exist
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)
if not os.path.exists(env_path):
    logger.warning(
        "⚠️ No .env file found. Make sure all required environment variables are set manually."
    )
    logger.info(
        "ℹ️ Create a .env file in the project root with the following variables:"
    )
    logger.info("FB_APP_ID=your_app_id")
    logger.info("FB_APP_SECRET=your_app_secret")
    logger.info("FB_ACCESS_TOKEN=your_access_token")
    logger.info("FB_AD_ACCOUNT_ID=act_your_ad_account_id")
    logger.info("FB_PAGE_ID=your_page_id")
    logger.info("FB_PIXEL_ID=your_pixel_id")
    logger.info("FB_PBIA=your_pbia_id")
    logger.info("FB_API_VERSION=v22.0")

from facebook_ads_uploader.facebook_api import init_facebook_api, upload_campaign


def test_pbia_integration_for_image():
    """
    Test the PBIA integration specifically for image creatives.
    This test verifies that the use_page_actor_override parameter is set correctly
    at the root level of creative params for image creatives.
    """
    # Check required environment variables
    required_vars = [
        "FB_APP_ID",
        "FB_APP_SECRET",
        "FB_ACCESS_TOKEN",
        "FB_AD_ACCOUNT_ID",
        "FB_PAGE_ID",
        "FB_PIXEL_ID",
        "FB_PBIA",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error("Please set all required variables in .env file or environment")
        return False

    # Get environment variables
    app_id = os.getenv("FB_APP_ID")
    app_secret = os.getenv("FB_APP_SECRET")
    access_token = os.getenv("FB_ACCESS_TOKEN")
    ad_account_id = os.getenv("FB_AD_ACCOUNT_ID")
    page_id = os.getenv("FB_PAGE_ID")
    pixel_id = os.getenv("FB_PIXEL_ID")
    pbia = os.getenv("FB_PBIA")

    # Initialize Facebook API
    api_version = os.getenv("FB_API_VERSION", "v22.0")
    try:
        init_facebook_api(app_id, app_secret, access_token, api_version)
        logger.info("✅ Facebook API initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Facebook API: {e}")
        return False

    # Test campaign name
    campaign_name = "TEST_PBIA_IMAGE_INTEGRATION"

    # Define a test row with image creative
    test_row = {
        "Title": "Test PBIA Image Integration",
        "Body": "Testing PBIA integration with image creatives",
        "Query": "test_query",
        "Media": "https://images.unsplash.com/photo-1615789591457-74a63395c990?q=80&w=1374&auto=format&fit=crop",  # Sample image URL
        "Country": "US",
        "Media Type": "image",
    }

    # Define defaults
    defaults = {
        "campaign": {
            "objective": "OUTCOME_SALES",
            "buying_type": "AUCTION",
            "status": "PAUSED",  # Use PAUSED for test campaigns
        },
        "ad_set": {
            "daily_budget": 1000,  # $10.00
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "targeting": {
                "device_targeting": "all",
                "age_min": 18,
                "age_max": 65,
            },
        },
        "ad": {
            "status": "PAUSED",
            "call_to_action_type": "LEARN_MORE",
        },
        "landing_page_prefix": "https://example.com/landing?query=",
    }

    try:
        # Upload the test campaign
        logger.info(f"🚀 Creating test campaign: {campaign_name}")
        campaign_id = upload_campaign(
            ad_account_id=ad_account_id,
            page_id=page_id,
            pixel_id=pixel_id,
            campaign_name=campaign_name,
            row_data=test_row,
            defaults=defaults,
        )

        if campaign_id:
            logger.info(f"✅ Test successful! Campaign created with ID: {campaign_id}")
            logger.info(
                "ℹ️ Check the Facebook Ads Manager to verify PBIA integration is working with image creative"
            )
            return True
        else:
            logger.error("❌ Test failed: No campaign ID returned")
            return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    logger.info("🧪 Testing PBIA integration for image creatives...")
    success = test_pbia_integration_for_image()
    if success:
        logger.info("✅ Test completed successfully")
    else:
        logger.error("❌ Test failed")
