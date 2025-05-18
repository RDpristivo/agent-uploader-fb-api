# In facebook_ads_uploader/image_downloader.py
import tempfile
import os
import requests
import logging
import re
import hashlib
import time
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)


def download_image_from_url(url: str, media_type: str = "image") -> str:
    """
    Download an image or video from a URL and save it to a temporary file.
    Handles complex URLs including Facebook CDN and Google Drive links.

    Args:
        url: The URL of the media to download
        media_type: The type of media (image or video)

    Returns:
        The path to the temporary file containing the downloaded media

    Raises:
        RuntimeError: If the media cannot be downloaded
    """
    logger.info(f"🔽 Downloading {media_type} from URL: {url}")

    # Clean the URL if it contains query parameters with special characters
    cleaned_url = url

    # Generate a filename based on the URL
    parsed_url = urlparse(url)

    # For Facebook CDN URLs with complex parameters, create a filename from hash of URL
    if "fbcdn.net" in url or len(url) > 200:
        # Extract any identifiable number from the URL
        id_match = re.search(r"\/(\d+)_", url)
        id_part = (
            f"fb_{id_match.group(1)}"
            if id_match
            else f"fb_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        )

        # Set appropriate extension
        if media_type.lower() == "video":
            filename = f"{id_part}.mp4"
        else:
            filename = f"{id_part}.jpg"
    else:
        # For normal URLs, get filename from path
        filename = os.path.basename(parsed_url.path)
        # Handle empty filenames or missing extensions
        if not filename or "." not in filename:
            # Default to appropriate extension based on media_type
            if media_type.lower() == "video":
                filename = "temp_video.mp4"
            else:
                filename = "temp_image.jpg"

    # Create a temporary file with appropriate extension
    suffix = os.path.splitext(filename)[1]
    if not suffix:
        suffix = ".mp4" if media_type.lower() == "video" else ".jpg"

    fd, temp_path = tempfile.mkstemp(suffix=suffix)

    # Setting up improved timeouts and retry handling
    max_retries = 3
    retry_count = 0
    download_success = False
    last_error = None

    # Try multiple times with increasing timeout
    while retry_count < max_retries and not download_success:
        try:
            timeout = 30 + (retry_count * 15)  # Increase timeout with each retry
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }
            logger.info(
                f"Download attempt {retry_count + 1}/{max_retries} (timeout: {timeout}s)"
            )

            # Download the image with proper headers for Facebook CDN
            response = requests.get(url, stream=True, timeout=timeout, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Write the image to the temp file
            total_size = 0
            with os.fdopen(fd, "wb") as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        total_size += len(chunk)

            # Verify we got actual content
            if total_size == 0:
                raise RuntimeError("Downloaded file is empty")

            logger.info(
                f"✅ Media downloaded successfully ({total_size} bytes) to: {temp_path}"
            )
            download_success = True
            return temp_path

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Download attempt {retry_count + 1} failed: {last_error}")
            retry_count += 1

            # Wait before retrying
            if retry_count < max_retries:
                time.sleep(2)

    # If we got here, all attempts failed
    logger.error(
        f"❌ Failed to download media from URL {url} after {max_retries} attempts: {last_error}"
    )
    raise RuntimeError(
        f"Failed to download media after {max_retries} attempts: {last_error}"
    )
