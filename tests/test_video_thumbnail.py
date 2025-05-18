#!/usr/bin/env python
"""
Test for the video_thumbnail.py module
"""

import unittest
import os
import tempfile
import logging

from facebook_ads_uploader.video_thumbnail import extract_video_thumbnail

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVideoThumbnail(unittest.TestCase):
    """Test the video thumbnail extraction functionality"""

    def setUp(self):
        """Create a test video file for thumbnail extraction"""
        # This is a very basic test that will use the placeholder generation
        # For a more thorough test, we'd need a real video file
        self.test_file = tempfile.mktemp(suffix=".mp4")
        with open(self.test_file, "wb") as f:
            f.write(b"This is a fake video file for testing")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_extract_thumbnail_fallback(self):
        """Test thumbnail extraction fallback to placeholder for invalid video"""
        thumbnail_path = extract_video_thumbnail(self.test_file)

        # Verify we got a result
        self.assertIsNotNone(thumbnail_path)

        # Verify the file exists
        self.assertTrue(os.path.exists(thumbnail_path))

        # Verify it has content
        self.assertGreater(os.path.getsize(thumbnail_path), 0)

        # Clean up the thumbnail
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)


if __name__ == "__main__":
    unittest.main()
