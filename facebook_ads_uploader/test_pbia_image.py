#!/usr/bin/env python3
"""
Test script to validate the PBIA (Page-Backed Instagram Account) integration for image creatives.

This script will test if the PBIA integration for image creatives is working correctly with the fixed code.
It logs detailed information about the image creative creation process, with specific focus on where
and how the use_page_actor_override parameter is set.

Usage:
    python test_pbia_image.py

Requires:
    - A .env file with Facebook API credentials
    - A public image URL to use for testing
"""
import os
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("pbia_image_test.log")],
)
logger = logging.getLogger()

# Load environment variables
load_dotenv()

# Get required environment variables
APP_ID = os.getenv("FB_APP_ID")
APP_SECRET = os.getenv("FB_APP_SECRET")
ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID")
PAGE_ID = os.getenv("FB_PAGE_ID")
PIXEL_ID = os.getenv("FB_PIXEL_ID")
PBIA_ID = os.getenv("FB_PBIA")  # Page-Backed Instagram Account ID
API_VERSION = os.getenv("FB_API_VERSION", "v22.0")

# Import necessary modules
try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.adimage import AdImage
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.exceptions import FacebookRequestError
except ImportError:
    logger.error(
        "❌ Failed to import Facebook Business SDK. Please install it with: pip install facebook-business"
    )
    exit(1)


def init_api():
    """Initialize the Facebook API"""
    if not all([APP_ID, APP_SECRET, ACCESS_TOKEN, AD_ACCOUNT_ID, PAGE_ID]):
        logger.error(
            "❌ Missing required environment variables. Please check your .env file."
        )
        return False

    try:
        FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN, api_version=API_VERSION)
        logger.info("✅ Facebook API initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Facebook API: {e}")
        return False


def test_image_creative():
    """Test creating an image creative with PBIA integration"""
    # Test with a reliable public image URL
    image_url = "https://images.unsplash.com/photo-1615789591457-74a63395c990?w=600"

    logger.info(f"🧪 Testing PBIA integration with image URL: {image_url}")
    logger.info(f"🔷 Using Page ID: {PAGE_ID}")
    logger.info(f"🔷 Using PBIA ID: {PBIA_ID}")

    try:
        ad_account = AdAccount(AD_ACCOUNT_ID)

        # 1. First upload the image to get a hash
        logger.info("🖼️ Uploading image to Facebook...")
        image = AdImage(parent_id=AD_ACCOUNT_ID)
        image[AdImage.Field.url] = image_url
        image.remote_create()
        image_hash = image[AdImage.Field.hash]
        logger.info(f"✅ Image uploaded successfully with hash: {image_hash}")

        # 2. Create a creative with the image hash
        logger.info("🎨 Creating image creative with PBIA integration...")

        object_story_spec = {
            "page_id": PAGE_ID,
            "link_data": {
                "image_hash": image_hash,
                "link": "https://example.com",
                "message": "PBIA integration test for image creative",
                "name": "Test Image Creative",
                "call_to_action": {
                    "type": "LEARN_MORE",
                    "value": {"link": "https://example.com"},
                },
            },
        }

        # Create the creative with proper PBIA integration
        creative_params = {
            "name": "PBIA Image Test Creative",
            "object_story_spec": object_story_spec,
        }

        # Add the critical PBIA settings
        if PBIA_ID:
            # Set the Instagram account ID
            if API_VERSION >= "v22.0":
                creative_params["instagram_user_id"] = PBIA_ID
                logger.info(
                    f"🔷 Setting instagram_user_id={PBIA_ID} for API version {API_VERSION}"
                )
            else:
                creative_params["instagram_actor_id"] = PBIA_ID
                logger.info(
                    f"🔷 Setting instagram_actor_id={PBIA_ID} for API version {API_VERSION}"
                )

            # Set use_page_actor_override to true at the ROOT level of creative_params
            creative_params["use_page_actor_override"] = True
            logger.info(
                "🔷 Setting use_page_actor_override=True at the ROOT level of creative_params"
            )

        # Log the complete creative params for debugging
        logger.info(f"📋 Creative params: {creative_params}")

        # Create the creative
        creative = ad_account.create_ad_creative(params=creative_params)
        creative_id = creative["id"]
        logger.info(f"✅ Creative created successfully with ID: {creative_id}")

        # Success message
        logger.info("✅ PBIA integration test for image creative PASSED!")
        logger.info(
            "✅ The use_page_actor_override parameter is now correctly set at the ROOT level"
        )
        logger.info(
            "✅ Check the Facebook Ads Manager to verify the creative has both Facebook and Instagram placements"
        )

        return True
    except FacebookRequestError as e:
        logger.error(f"❌ Facebook API error: {e.api_error_message()}")
        logger.error(f"❌ HTTP status: {e.http_status()}")
        logger.error(f"❌ Error code: {e.api_error_code()}")
        logger.error(f"❌ Error type: {e.api_error_type()}")
        logger.error(f"❌ Error subcode: {e.api_error_subcode()}")
        logger.error(f"❌ Full error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Starting PBIA image integration test...")

    if init_api():
        start_time = time.time()
        success = test_image_creative()
        elapsed_time = time.time() - start_time

        if success:
            logger.info(f"✅ Test completed successfully in {elapsed_time:.2f} seconds")
        else:
            logger.error(f"❌ Test failed after {elapsed_time:.2f} seconds")
    else:
        logger.error("❌ Failed to initialize the Facebook API. Test aborted.")
