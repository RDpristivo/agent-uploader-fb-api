# In facebook_ads_uploader/image_downloader.py
import tempfile
import os
import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_image_from_url(url: str) -> str:
    """
    Download an image from a URL and save it to a temporary file.

    Args:
        url: The URL of the image to download

    Returns:
        The path to the temporary file containing the downloaded image

    Raises:
        RuntimeError: If the image cannot be downloaded
    """
    logger.info(f"Downloading image from URL: {url}")

    try:
        # Create a proper temp file with the correct extension
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        # Ensure the filename has an extension
        if not filename or "." not in filename:
            # Default to .jpg if we can't determine
            filename = "temp_image.jpg"

        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])

        # Download the image
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Write the image to the temp file
        with os.fdopen(fd, "wb") as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    temp_file.write(chunk)

        logger.info(f"Image downloaded successfully to: {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Failed to download image from URL {url}: {str(e)}")
        raise RuntimeError(f"Failed to download image: {str(e)}")
