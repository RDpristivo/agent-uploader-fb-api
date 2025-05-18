#!/usr/bin/env python
"""
Test module for Facebook API functionality.
Run this module from the root directory:
python -m tests.test_facebook_api
"""

import os
import sys
import unittest
import tempfile
import logging
from facebook_ads_uploader.facebook_api import extract_video_thumbnail

# Setup logging with stdout handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class ThumbnailExtractionTests(unittest.TestCase):
    """Test cases for video thumbnail extraction functionality."""

    def setUp(self):
        """Set up before each test."""
        print(f"\n{'='*70}")

    def test_fallback_thumbnail_creation(self):
        """Test that the fallback thumbnail mechanism works properly."""
        print("\nTEST: Fallback Thumbnail Creation")
        print("--------------------------------")

        # Create a non-existent video path
        video_path = os.path.join(tempfile.gettempdir(), "nonexistent_video.mp4")

        # Make sure it really doesn't exist
        if os.path.exists(video_path):
            os.remove(video_path)

        print(f"Testing with non-existent video: {video_path}")
        thumbnail_path = extract_video_thumbnail(video_path)

        # Verify thumbnail was created
        self.assertIsNotNone(thumbnail_path, "Fallback thumbnail should be created")
        self.assertTrue(os.path.exists(thumbnail_path), "Thumbnail file should exist")
        self.assertGreater(
            os.path.getsize(thumbnail_path), 0, "Thumbnail should not be empty"
        )

        print(f"✅ Fallback thumbnail created successfully: {thumbnail_path}")
        print(f"   Size: {os.path.getsize(thumbnail_path)} bytes")

        # Clean up
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            print(f"✓ Cleaned up thumbnail: {thumbnail_path}")

    def test_real_video_thumbnail(self):
        """
        Test thumbnail extraction with a real video file.
        This test is skipped if no video path is provided.

        Run with: python -m tests.test_facebook_api /path/to/video.mp4
        """
        print("\nTEST: Real Video Thumbnail Extraction")
        print("------------------------------------")

        # Skip this test if no video path is provided
        if len(sys.argv) <= 1:
            print("ℹ️ Skipping real video test - no video path provided")
            print(
                "   To test with a real video: python -m tests.test_facebook_api /path/to/video.mp4"
            )
            self.skipTest("No video path provided")
            return

        video_path = sys.argv[1]
        if not os.path.exists(video_path):
            print(f"⚠️ Video file not found: {video_path}")
            self.skipTest(f"Video file not found: {video_path}")
            return

        print(f"Testing with real video: {video_path}")
        thumbnail_path = extract_video_thumbnail(video_path)

        # Verify thumbnail was created
        self.assertIsNotNone(thumbnail_path, "Thumbnail should be created")
        self.assertTrue(os.path.exists(thumbnail_path), "Thumbnail file should exist")
        self.assertGreater(
            os.path.getsize(thumbnail_path), 0, "Thumbnail should not be empty"
        )

        print(f"✅ Thumbnail extracted successfully: {thumbnail_path}")
        print(f"   Size: {os.path.getsize(thumbnail_path)} bytes")

        # Clean up
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            print(f"✓ Cleaned up thumbnail: {thumbnail_path}")


# Simplify running from command line
def main():
    """Run the tests."""
    print("\nRunning Facebook API Tests")
    print("=========================")
    unittest.main(argv=[sys.argv[0]])


if __name__ == "__main__":
    main()
