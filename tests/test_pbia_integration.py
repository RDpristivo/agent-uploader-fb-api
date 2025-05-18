#!/usr/bin/env python
"""
Test module for Facebook API PBIA functionality.
Run this module from the root direc        # Call the function
        result = self.upload_campaign(
            ad_account_id='act_1        # Call the function
        result = self.upload_campaign(
            ad_account_id='act_12345',
            page_id='123456789',
            pixel_id='987654321',
            campaign_name='Test_Campaign_US_Video_PBIA',
            row_data=row_data,
            defaults={
                'ad': {},
                'adset': {},
                'campaign': {},
                # Add landing page prefix URL to defaults
                'landing_page': {
                    'prefix': 'https://example.com/',
                    'utm_params': True
                }
            },
        )          page_id='123456789',
            pixel_id='987654321',
            campaign_name='Test_Campaign_US_Image_PBIA',
            row_data=row_data,
            defaults={
                'ad': {},
                'adset': {},
                'campaign': {},
                # Add landing page prefix URL to defaults
                'landing_page': {
                    'prefix': 'https://example.com/',
                    'utm_params': True
                }
            },
        )hon -m tests.test_pbia_integration
"""

import os
import sys
import unittest
import logging
import yaml
from unittest.mock import patch, MagicMock
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad

# Setup logging with stdout handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class MockResponse:
    """Mock response for Facebook API calls."""

    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data


class PBIAIntegrationTests(unittest.TestCase):
    """Test cases for PBIA (Page-Backed Instagram Account) integration functionality."""

    def setUp(self):
        """Set up before each test."""
        print(f"\n{'='*70}")
        self.pbia_id = "17841473288315687"  # Example PBIA ID for testing

        # Load test defaults
        test_defaults_path = os.path.join(
            os.path.dirname(__file__), "test_defaults.yaml"
        )
        try:
            with open(test_defaults_path, "r") as f:
                self.test_defaults = yaml.safe_load(f)
            print(f"Loaded test defaults from {test_defaults_path}")
        except Exception as e:
            print(f"Warning: Could not load test defaults: {e}")
            self.test_defaults = {
                "landing_page": {"prefix": "https://example.com/", "utm_params": True},
                "ad": {},
                "adset": {},
                "campaign": {},
            }

        # Mock environment variables
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "FB_PBIA": self.pbia_id,
                "FB_APP_ID": "mock_app_id",
                "FB_APP_SECRET": "mock_app_secret",
                "FB_ACCESS_TOKEN": "mock_access_token",
                "FB_AD_ACCOUNT_ID": "act_12345",
                "FB_PAGE_ID": "123456789",
            },
        )
        self.env_patcher.start()

        # Import after patching environment
        from facebook_ads_uploader.facebook_api import upload_campaign

        self.upload_campaign = upload_campaign

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()

    @patch("facebook_ads_uploader.facebook_api.FacebookAdsApi")
    @patch("facebook_ads_uploader.facebook_api.AdAccount")
    def test_image_creative_pbia_integration(self, mock_ad_account, mock_fb_api):
        """Test that PBIA is correctly applied to image creatives."""
        print("\nTEST: Image Creative PBIA Integration")
        print("------------------------------------")

        # Mock the Facebook API responses
        mock_ad_account_instance = MagicMock()
        mock_ad_account.return_value = mock_ad_account_instance

        # Mock the campaign creation
        mock_campaign = {"id": "123456789"}
        mock_ad_account_instance.create_campaign.return_value = mock_campaign

        # Mock the ad set creation
        mock_adset = {"id": "987654321"}
        mock_ad_account_instance.create_ad_set.return_value = mock_adset

        # Mock the creative creation - capture the params
        creative_params_captured = {}

        def mock_create_creative(params):
            nonlocal creative_params_captured
            creative_params_captured = params
            return {"id": "111222333"}

        mock_ad_account_instance.create_ad_creative.side_effect = mock_create_creative

        # Mock the ad creation
        mock_ad_account_instance.create_ad.return_value = {"id": "444555666"}

        # Prepare test data - simulate a row from the spreadsheet with an image
        row_data = {
            "Topic": "Test Campaign",
            "Daily Budget": "$5",
            "Country": "US",
            "Title": "Test Headline",
            "Body": "Test Description",
            "Query": "test-query",
            "Media Path": "https://example.com/test-image.jpg",
            "Media Type": "image",
        }

        # Call the function
        result = self.upload_campaign(
            ad_account_id="act_12345",
            page_id="123456789",
            pixel_id="987654321",
            campaign_name="Test_Campaign_US_Image_PBIA",
            row_data=row_data,
            defaults={"ad": {}, "adset": {}, "campaign": {}},
        )

        # Check if the creative has the correct PBIA parameters
        self.assertIn("object_story_spec", creative_params_captured)
        object_story_spec = creative_params_captured.get("object_story_spec", {})

        # Verify use_page_actor_override is True
        self.assertIn("use_page_actor_override", object_story_spec)
        self.assertTrue(object_story_spec["use_page_actor_override"])

        # Verify instagram_user_id is correctly set
        self.assertIn("instagram_user_id", object_story_spec)
        self.assertEqual(object_story_spec["instagram_user_id"], self.pbia_id)

        print(f"✅ Image creative correctly configured with PBIA ID: {self.pbia_id}")
        print(
            f"✅ use_page_actor_override correctly set to: {object_story_spec['use_page_actor_override']}"
        )

    @patch("facebook_ads_uploader.facebook_api.FacebookAdsApi")
    @patch("facebook_ads_uploader.facebook_api.AdAccount")
    @patch("facebook_ads_uploader.facebook_api.download_video_from_url")
    @patch("facebook_ads_uploader.facebook_api.AdVideo")
    def test_video_creative_pbia_integration(
        self, mock_video, mock_download, mock_ad_account, mock_fb_api
    ):
        """Test that PBIA is correctly applied to video creatives."""
        print("\nTEST: Video Creative PBIA Integration")
        print("------------------------------------")

        # Mock the download video function
        mock_download.return_value = "/tmp/test-video.mp4"

        # Mock the video upload
        mock_video_instance = MagicMock()
        mock_video_instance.__getitem__.return_value = "777888999"  # video ID
        mock_video.return_value = mock_video_instance

        # Mock the Facebook API responses
        mock_ad_account_instance = MagicMock()
        mock_ad_account.return_value = mock_ad_account_instance

        # Mock the campaign creation
        mock_campaign = {"id": "123456789"}
        mock_ad_account_instance.create_campaign.return_value = mock_campaign

        # Mock the ad set creation
        mock_adset = {"id": "987654321"}
        mock_ad_account_instance.create_ad_set.return_value = mock_adset

        # Mock the creative creation - capture the params
        creative_params_captured = {}

        def mock_create_creative(params):
            nonlocal creative_params_captured
            creative_params_captured = params
            return {"id": "111222333"}

        mock_ad_account_instance.create_ad_creative.side_effect = mock_create_creative

        # Mock the ad creation
        mock_ad_account_instance.create_ad.return_value = {"id": "444555666"}

        # Prepare test data - simulate a row from the spreadsheet with a video
        row_data = {
            "Topic": "Test Campaign",
            "Daily Budget": "$5",
            "Country": "US",
            "Title": "Test Headline",
            "Body": "Test Description",
            "Query": "test-query",
            "Media Path": "https://example.com/test-video.mp4",
            "Media Type": "video",
        }

        # Call the function
        result = self.upload_campaign(
            ad_account_id="act_12345",
            page_id="123456789",
            pixel_id="987654321",
            campaign_name="Test_Campaign_US_Video_PBIA",
            row_data=row_data,
            defaults={"ad": {}, "adset": {}, "campaign": {}},
        )

        # Check if the creative has the correct PBIA parameters
        self.assertIn("object_story_spec", creative_params_captured)
        object_story_spec = creative_params_captured.get("object_story_spec", {})

        # Verify use_page_actor_override is True
        self.assertIn("use_page_actor_override", object_story_spec)
        self.assertTrue(object_story_spec["use_page_actor_override"])

        # Verify instagram_user_id is correctly set
        self.assertIn("instagram_user_id", object_story_spec)
        self.assertEqual(object_story_spec["instagram_user_id"], self.pbia_id)

        print(f"✅ Video creative correctly configured with PBIA ID: {self.pbia_id}")
        print(
            f"✅ use_page_actor_override correctly set to: {object_story_spec['use_page_actor_override']}"
        )


# Simplify running from command line
if __name__ == "__main__":
    unittest.main()
