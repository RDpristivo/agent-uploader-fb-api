#!/usr/bin/env python
"""
Command-line utility for testing Facebook API functionality.
This script provides a convenient way to test thumbnail extraction
and other Facebook API features from the command line.

Usage:
  python -m facebook_ads_uploader.test_utils thumbnail [path/to/video.mp4]
"""

import os
import sys
import argparse
import logging
from facebook_ads_uploader.facebook_api import extract_video_thumbnail

# Setup logging with stdout handler for more visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def test_thumbnail_extraction(video_path=None):
    """
    Test the thumbnail extraction functionality.

    Args:
        video_path: Optional path to a video file. If not provided,
                   tests the fallback mechanism with a non-existent video.
    """
    print("\n==== Testing Thumbnail Extraction ====")

    if video_path and os.path.exists(video_path):
        print(f"Using provided video: {video_path}")
        thumbnail_path = extract_video_thumbnail(video_path)
    else:
        if video_path:
            print(f"Video file not found: {video_path}")

        print("Testing fallback with non-existent video")
        test_video_path = "/tmp/nonexistent_video.mp4"
        print(f"Using test path: {test_video_path}")
        thumbnail_path = extract_video_thumbnail(test_video_path)

    if thumbnail_path:
        print(f"\n✅ SUCCESS: Thumbnail created at: {thumbnail_path}")
        # Check if the thumbnail file exists
        if os.path.exists(thumbnail_path):
            size = os.path.getsize(thumbnail_path)
            print(f"Thumbnail file size: {size} bytes")

            # Show the thumbnail path
            print("\nTo view the thumbnail:")
            if sys.platform == "darwin":  # macOS
                print(f"open {thumbnail_path}")
            elif sys.platform == "win32":  # Windows
                print(f"start {thumbnail_path}")
            else:  # Linux and others
                print(f"xdg-open {thumbnail_path}")

            return True
        else:
            print("\n❌ ERROR: Thumbnail file doesn't exist!")
    else:
        print("\n❌ ERROR: Thumbnail creation failed!")

    return False


def main():
    """CLI entry point for Facebook API utilities."""
    parser = argparse.ArgumentParser(description="Facebook API testing utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Thumbnail command
    thumbnail_parser = subparsers.add_parser(
        "thumbnail", help="Test video thumbnail extraction"
    )
    thumbnail_parser.add_argument(
        "video_path", nargs="?", help="Path to a video file (optional)"
    )

    # Parse arguments
    args = parser.parse_args()

    if args.command == "thumbnail":
        print(f"\nFacebook API Test Utility - Testing Thumbnail Extraction")
        print(f"====================================================")
        success = test_thumbnail_extraction(
            args.video_path if hasattr(args, "video_path") else None
        )
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
