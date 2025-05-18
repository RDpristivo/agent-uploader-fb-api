# In facebook_ads_uploader/video_downloader.py
import tempfile
import os
import requests
import logging
import re
import hashlib
import time
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def download_video_from_url(url: str) -> str:
    """
    Download a video from a URL and save it to a temporary file.
    Handles complex URLs including Facebook CDN and Google Drive links.

    Args:
        url: The URL of the video to download

    Returns:
        The path to the temporary file containing the downloaded video

    Raises:
        RuntimeError: If the video cannot be downloaded
    """
    logger.info(f"🔽 Downloading video from URL: {url}")

    # Extract file extension if present in URL for better temp file naming
    parsed_url = urlparse(url)
    url_path = parsed_url.path.lower()
    url_extension = None

    # Special handling for Facebook CDN URLs (fbcdn.net)
    if "fbcdn.net" in url.lower():
        logger.info("📱 Detected Facebook CDN URL (fbcdn.net)")
        # For Facebook CDN URLs, look for .mp4, .mov, etc. in the path or query params
        if ".mp4" in url.lower():
            url_extension = ".mp4"
        elif ".mov" in url.lower():
            url_extension = ".mov"
        else:
            # Default to .mp4 for Facebook videos if extension not found
            url_extension = ".mp4"
        logger.info(f"📄 Using file extension for Facebook CDN video: {url_extension}")
    else:
        # Try to guess the file type from the URL for non-FB CDN URLs
        video_extensions = [
            ".mp4",
            ".mov",
            ".avi",
            ".wmv",
            ".flv",
            ".webm",
            ".mkv",
            ".m4v",
        ]
        for ext in video_extensions:
            if url_path.endswith(ext):
                url_extension = ext
                logger.info(f"📄 Detected video file extension from URL: {ext}")
            break

    # If extension not found in path, look in query parameters too (common for some hosts)
    if not url_extension and parsed_url.query:
        query_params = parse_qs(parsed_url.query)
        # Check for file parameter that might contain the extension
        for param_name in ["file", "filename", "name", "video"]:
            if param_name in query_params:
                param_value = query_params[param_name][0].lower()
                for ext in video_extensions:
                    if param_value.endswith(ext):
                        url_extension = ext
                        logger.info(
                            f"📄 Detected video file extension from query parameter: {ext}"
                        )
                        break
                if url_extension:
                    break

    # Special handling for Google Drive links
    if "drive.google.com" in url or "docs.google.com" in url:
        logger.info(f"🔄 Using specialized Google Drive video download handler")
        return download_google_drive_video(url)

    # Special handling for cloud storage services
    if "storage.googleapis.com" in url:
        logger.info(f"📦 Detected Google Cloud Storage URL: {url}")
    elif "cloudfront.net" in url:
        logger.info(f"📦 Detected Amazon CloudFront URL: {url}")
    elif "amazonaws.com" in url and "s3" in url:
        logger.info(f"📦 Detected Amazon S3 URL: {url}")
    elif "blob.core.windows.net" in url:
        logger.info(f"📦 Detected Azure Blob Storage URL: {url}")

    if any(
        host in url
        for host in [
            "storage.googleapis.com",
            "cloudfront.net",
            "amazonaws.com",
            "blob.core.windows.net",
        ]
    ):
        logger.info(f"☁️ Using direct download for cloud storage URL")

    # Generate a filename based on the URL
    parsed_url = urlparse(url)

    # For Facebook CDN URLs with complex parameters, create a filename from hash of URL
    if "fbcdn.net" in url or len(url) > 200:
        # Extract any identifiable number from the URL for Facebook videos
        id_match = re.search(r"\/(\d+)_", url)
        id_part = (
            f"fb_{id_match.group(1)}"
            if id_match
            else f"fb_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        )
        # Always use .mp4 for Facebook videos as it's their default format
        filename = f"{id_part}.mp4"
        logger.info(f"🎬 Created filename for Facebook CDN video: {filename}")
    else:
        # For normal URLs, get filename from path
        filename = os.path.basename(parsed_url.path)
        # Handle empty filenames or missing extensions
        if not filename or "." not in filename:
            filename = f"temp_video{url_extension or '.mp4'}"

    # Create a temporary file with appropriate extension
    suffix = url_extension or os.path.splitext(filename)[1]
    if not suffix:
        suffix = ".mp4"

    fd, temp_path = tempfile.mkstemp(suffix=suffix)

    # Setting up improved timeouts and retry handling
    max_retries = 3
    retry_count = 0
    download_success = False
    # Try multiple times with increasing timeout
    while retry_count < max_retries and not download_success:
        try:
            timeout = 60 + (
                retry_count * 30
            )  # Increase timeout with each retry, start with longer timeout for videos

            # Enhanced headers for Facebook CDN URLs
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Accept": "*/*",  # Accept anything for videos
                "Accept-Encoding": "identity;q=1, *;q=0",  # Prefer uncompressed responses
                "Accept-Language": "en-US,en;q=0.9",
                "Range": "bytes=0-",  # Support for partial content
                "Referer": "https://www.facebook.com/",  # Adding a referer helps with some Facebook URLs
            }

            logger.info(
                f"Download attempt {retry_count + 1}/{max_retries} (timeout: {timeout}s)"
            )

            # Special handling for Facebook CDN URLs
            if "fbcdn.net" in url:
                logger.info(f"🔍 Using specialized handling for Facebook CDN URL")
                # For Facebook CDN URLs, we may need to try multiple variants
                fetch_url = url
            else:
                fetch_url = url

            # Download the video with proper headers
            try:
                response = requests.get(
                    fetch_url, stream=True, timeout=timeout, headers=headers
                )
                response.raise_for_status()  # Raise an exception for HTTP errors
            except Exception as e:
                if "fbcdn.net" in url and "/v/" in url:
                    # If the original URL fails, try with the modified URL
                    logger.info(
                        f"⚠️ Original fbcdn.net URL failed, trying simplified version"
                    )
                    parts = url.split("/v/")
                    modified_url = parts[0] + "/" + parts[1].split("/", 1)[1]
                    response = requests.get(
                        modified_url, stream=True, timeout=timeout, headers=headers
                    )
                    response.raise_for_status()
                else:
                    # Re-raise the exception if it's not a Facebook CDN URL
                    raise e

            # Write the video to the temp file
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
                f"✅ Video downloaded successfully ({total_size} bytes) to: {temp_path}"
            )
            download_success = True
            return temp_path

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Download attempt {retry_count + 1} failed: {last_error}")
            retry_count += 1

            # Wait before retrying
            if retry_count < max_retries:
                time.sleep(3)  # Slightly longer wait for videos

    # If we got here, all attempts failed
    logger.error(
        f"❌ Failed to download video from URL {url} after {max_retries} attempts: {last_error}"
    )
    raise RuntimeError(
        f"Failed to download video after {max_retries} attempts: {last_error}"
    )


def extract_google_drive_video_id(url: str) -> Optional[str]:
    """
    Extract the file ID from a Google Drive URL specifically for videos.
    Supports various Google Drive URL formats.

    Args:
        url: The Google Drive URL

    Returns:
        The file ID or None if it couldn't be extracted
    """
    if not url:
        return None

    # Check for Google Drive domains
    if not any(
        domain in url.lower() for domain in ["drive.google.com", "docs.google.com"]
    ):
        return None

    # Format: https://drive.google.com/file/d/FILE_ID/view
    if "/file/d/" in url:
        try:
            file_id = url.split("/file/d/")[1].split("/")[0]
            logger.info(
                f"📋 Extracted Google Drive file ID from file/d/ format: {file_id}"
            )
            return file_id
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract ID from file/d/ format: {str(e)}")
            pass

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Format: https://drive.google.com/open?id=FILE_ID
    if "id" in query_params:
        file_id = query_params["id"][0]
        logger.info(
            f"📋 Extracted Google Drive file ID from query parameter id: {file_id}"
        )
        return file_id

    # Format: https://drive.google.com/uc?export=view&id=FILE_ID
    if parsed_url.path == "/uc" and "id" in query_params:
        file_id = query_params["id"][0]
        logger.info(
            f"📋 Extracted Google Drive file ID from uc path with id: {file_id}"
        )
        return file_id

    # Format: https://docs.google.com/document/d/FILE_ID/edit
    # Format: https://docs.google.com/spreadsheets/d/FILE_ID/edit
    # Format: https://docs.google.com/presentation/d/FILE_ID/edit
    docs_pattern = r"/(?:document|spreadsheets|presentation)/d/([a-zA-Z0-9_-]+)"
    docs_match = re.search(docs_pattern, url)
    if docs_match:
        file_id = docs_match.group(1)
        logger.info(f"📋 Extracted Google Drive file ID from docs format: {file_id}")
        return file_id

    # Format: Using a direct sharing link with a key parameter
    if "sharing" in url and "key" in query_params:
        file_id = query_params["key"][0]
        logger.info(f"📋 Extracted Google Drive file ID from sharing key: {file_id}")
        return file_id

    logger.warning(f"❌ Could not extract file ID from Google Drive URL: {url}")
    return None


def download_google_drive_video(url: str) -> str:
    """
    Download a video from Google Drive with special handling for the authentication flow.

    Args:
        url: The Google Drive URL

    Returns:
        Path to the downloaded video file
    """
    logger.info(f"🎬 Downloading video from Google Drive: {url}")

    # Extract the file ID
    file_id = extract_google_drive_video_id(url)
    if not file_id:
        raise RuntimeError(f"Could not extract file ID from Google Drive URL: {url}")

    # Create a direct download URL
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    logger.info(f"🔄 Using direct download URL: {direct_url}")

    # Try to determine the file type/extension from the original URL
    file_extension = ".mp4"  # Default extension

    # Extract filename and extension if available in the URL
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # First try: Check if the name/filename is in query params (might have extension)
    if "name" in query_params:
        name = query_params["name"][0]
        if "." in name:
            potential_ext = os.path.splitext(name)[1].lower()
            video_exts = [
                ".mp4",
                ".mov",
                ".avi",
                ".wmv",
                ".flv",
                ".webm",
                ".mkv",
                ".m4v",
            ]
            if potential_ext in video_exts:
                file_extension = potential_ext
                logger.info(
                    f"📄 Found video extension in query parameter: {file_extension}"
                )

    # Create a temporary file with the appropriate extension
    fd, temp_path = tempfile.mkstemp(suffix=file_extension)

    # Set up session for handling redirects and cookies
    session = requests.Session()

    try:
        # Initial request to get confirmation token if needed
        logger.info(f"🌐 Making initial request to Google Drive")
        response = session.get(direct_url, stream=True, timeout=60)

        # Check if we got an error response
        if response.status_code != 200:
            logger.error(
                f"❌ Google Drive returned status code: {response.status_code}"
            )
            raise RuntimeError(
                f"Failed to access Google Drive file. Status code: {response.status_code}"
            )

        # Check if we need to bypass the "large file" warning
        if "confirm=" in response.text:
            logger.info(f"🔍 Found Google Drive confirmation prompt (large file)")
            try:
                confirmation_token = re.search(
                    r"confirm=([0-9a-zA-Z_-]+)", response.text
                ).group(1)
                direct_url = f"{direct_url}&confirm={confirmation_token}"
                logger.info(f"📝 Using confirmation token, updated URL")
                response = session.get(direct_url, stream=True, timeout=120)
            except Exception as e:
                logger.warning(f"⚠️ Error extracting confirmation token: {str(e)}")
                logger.info(f"🔄 Proceeding with download anyway")

        # Check content type to verify it's a video
        content_type = response.headers.get("Content-Type", "")
        if content_type and "video/" in content_type:
            logger.info(f"✅ Confirmed video content type: {content_type}")
        elif content_type:
            logger.warning(f"⚠️ Content-Type is not video: {content_type}")
            # Try to proceed anyway, might be application/octet-stream

        # Download the file
        total_size = 0
        content_length = response.headers.get("Content-Length")
        expected_size = int(content_length) if content_length else None

        if expected_size:
            logger.info(f"📊 Expected file size: {expected_size / 1024 / 1024:.2f} MB")

        with os.fdopen(fd, "wb") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    total_size += len(chunk)

                    # Log progress for large files
                    if (
                        expected_size
                        and expected_size > 10 * 1024 * 1024
                        and total_size % (5 * 1024 * 1024) < 8192
                    ):
                        progress = (total_size / expected_size) * 100
                        logger.info(
                            f"📈 Download progress: {progress:.1f}% ({total_size / 1024 / 1024:.2f} MB)"
                        )

        # Verify we got actual content
        if total_size == 0:
            raise RuntimeError("Downloaded video file is empty")

        # If file is very small, it might be an error page rather than the actual video
        if total_size < 10000:  # Less than 10 KB is suspicious for a video
            logger.warning(
                f"⚠️ Downloaded file is suspiciously small: {total_size} bytes"
            )
            # Read start of file to check if it's HTML error page
            with open(temp_path, "rb") as f:
                start_bytes = f.read(100)
                if b"<!DOCTYPE html>" in start_bytes or b"<html" in start_bytes:
                    logger.error(
                        f"❌ Downloaded file appears to be HTML, not video data"
                    )
                    raise RuntimeError(
                        "Google Drive returned HTML instead of video data"
                    )

        logger.info(
            f"✅ Google Drive video downloaded successfully ({total_size / 1024 / 1024:.2f} MB) to: {temp_path}"
        )
        return temp_path

    except Exception as e:
        # Clean up temp file if something went wrong
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"🧹 Removed incomplete download file: {temp_path}")
            except:
                pass
        logger.error(f"❌ Error downloading Google Drive video: {str(e)}")
        raise RuntimeError(f"Error downloading Google Drive video: {str(e)}")


def get_video_info(file_path: str) -> Tuple[int, int, int]:
    """
    Get basic information about a video file.

    Args:
        file_path: Path to the video file

    Returns:
        Tuple containing (file_size_bytes, duration_seconds, width_pixels, height_pixels)
    """
    try:
        file_size = os.path.getsize(file_path)

        # Check if file is actually a video by examining headers
        with open(file_path, "rb") as f:
            header = f.read(12)  # Read first 12 bytes to check file signature

        # Check common video file signatures
        is_video = (
            header.startswith(b"\x00\x00\x00\x18ftypmp42")  # MP4
            or header.startswith(b"\x00\x00\x00\x1cftypisom")  # MP4 ISO format
            or header.startswith(b"\x00\x00\x00\x20ftyp")  # Common MP4 format
            or header.startswith(b"\x52\x49\x46\x46")  # AVI
            or header.startswith(b"\x1a\x45\xdf\xa3")  # WebM/MKV
        )

        if not is_video:
            logger.warning(
                f"⚠️ File doesn't appear to be a standard video format: {file_path}"
            )

        # Log file size in MB for clarity
        size_mb = file_size / (1024 * 1024)
        logger.info(f"📊 Video file size: {size_mb:.2f} MB")

        # Duration and dimensions would require a video processing library like ffmpeg
        # In a production environment, consider adding actual video metadata extraction
        # For example using python-ffmpeg or moviepy

        return file_size, 0, 0
    except Exception as e:
        logger.error(f"❌ Error getting video info: {e}")
        return 0, 0, 0
