#!/usr/bin/env python

import os
import sys
import logging
from facebook_ads_uploader.facebook_api import extract_video_thumbnail

# Setup logging - set to DEBUG for more verbose output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_thumbnail_extraction():
    """
    Test the thumbnail extraction function with various scenarios.
    """
    print("Starting thumbnail extraction test...")

    # Check if a video file path is provided
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        # Validate the path
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return

        print(f"Testing thumbnail extraction with video: {video_path}")

        # Extract thumbnail
        thumbnail_path = extract_video_thumbnail(video_path)

        if thumbnail_path:
            print(f"Thumbnail extracted successfully: {thumbnail_path}")
            # Check if the thumbnail file exists
            if os.path.exists(thumbnail_path):
                size = os.path.getsize(thumbnail_path)
                print(f"Thumbnail file size: {size} bytes")
                print("✅ Test completed successfully!")
            else:
                print("❌ Thumbnail file doesn't exist!")
        else:
            print("❌ Thumbnail extraction failed!")
    else:
        # Test with a non-existent video to test the fallback mechanism
        print("No video path provided, testing fallback with non-existent video")
        video_path = "/tmp/nonexistent_video.mp4"
        print(f"Using test video path: {video_path}")

        try:
            thumbnail_path = extract_video_thumbnail(video_path)

            if thumbnail_path:
                print(f"Thumbnail created with fallback: {thumbnail_path}")
                # Check if the thumbnail file exists
                if os.path.exists(thumbnail_path):
                    size = os.path.getsize(thumbnail_path)
                    print(f"Thumbnail file size: {size} bytes")
                    print("✅ Fallback test completed successfully!")
                else:
                    print("❌ Fallback thumbnail file doesn't exist!")
            else:
                print("❌ Fallback thumbnail creation failed!")
        except Exception as e:
            print(f"Error during test: {e}")


if __name__ == "__main__":
    test_thumbnail_extraction()
    print("Test completed.")
