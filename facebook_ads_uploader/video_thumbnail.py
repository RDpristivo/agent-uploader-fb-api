#!/usr/bin/env python

import os
import tempfile
import subprocess
import logging
import hashlib

# Configure logging
logger = logging.getLogger(__name__)


def extract_video_thumbnail(video_path):
    """
    Extract the first frame of a video to use as a thumbnail.
    Uses multiple methods:
    1. OpenCV (if available)
    2. ffmpeg (if available)
    3. PIL fallback (generates a placeholder)

    Args:
        video_path: Path to the video file

    Returns:
        Path to the generated thumbnail image or None if extraction failed
    """
    # Create a temporary file for the thumbnail
    fd, thumbnail_path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)  # Close the file descriptor as we'll use the path

    logger.info(f"🖼️ Extracting thumbnail from video: {video_path}")

    # Method 1: Try using OpenCV if available - best for first frame extraction
    try:
        import cv2

        # Open the video file
        vidcap = cv2.VideoCapture(video_path)

        # Check if video opened successfully
        if not vidcap.isOpened():
            logger.error(f"❌ OpenCV couldn't open the video file: {video_path}")
            # Will fall through to next method
        else:
            # Read the first frame
            success, image = vidcap.read()

            if success:
                # Save the first frame as a JPEG
                cv2.imwrite(thumbnail_path, image, [cv2.IMWRITE_JPEG_QUALITY, 95])
                vidcap.release()

                # Check if the thumbnail was created and has contents
                if (
                    os.path.exists(thumbnail_path)
                    and os.path.getsize(thumbnail_path) > 0
                ):
                    logger.info(
                        f"✅ Successfully extracted first frame with OpenCV: {thumbnail_path}"
                    )
                    return thumbnail_path
            else:
                logger.error("❌ Failed to read the first frame from video")
                vidcap.release()
                # Will fall through to the next method
    except ImportError:
        logger.warning("⚠️ OpenCV (cv2) not available, trying ffmpeg instead")
        # Will fall through to the next method
    except Exception as e:
        logger.error(f"❌ Error extracting thumbnail with OpenCV: {e}")
        # Will fall through to the next method

    # Method 2: Try using ffmpeg if available
    try:
        # Use ffmpeg to extract the first frame
        # -y: Overwrite output file without asking
        # -i: Input file
        # -ss: Seek to position (0 seconds)
        # -vframes: Number of frames to extract (1)
        # -q:v: Quality of output image (2 is high quality, 31 is low)
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output without asking
            "-i",
            video_path,  # Input file
            "-ss",
            "00:00:00",  # Position at start
            "-vframes",
            "1",  # Extract 1 frame
            "-q:v",
            "2",  # High quality
            thumbnail_path,
        ]

        # Run the command
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        # Check if the thumbnail was created and has contents
        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            logger.info(
                f"✅ Successfully extracted thumbnail with ffmpeg: {thumbnail_path}"
            )
            return thumbnail_path
        else:
            logger.error("❌ Thumbnail was not created or is empty")
            # Will fall through to fallback method
    except FileNotFoundError:
        # ffmpeg is not installed, log this clearly
        logger.warning(
            "⚠️ ffmpeg not found on system, falling back to placeholder thumbnail"
        )
        # Will fall through to fallback method
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error running ffmpeg: {e}")
        if hasattr(e, "stderr") and e.stderr:
            logger.error(f"ffmpeg stderr: {e.stderr.decode('utf-8')}")
        # Will fall through to fallback method
    except Exception as e:
        logger.error(f"❌ Error extracting thumbnail with ffmpeg: {e}")
        # Will fall through to fallback method

    # Fallback method: Create a placeholder thumbnail using PIL
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Generate RGB values from hash for a consistent color
        video_hash = hashlib.md5(video_path.encode()).hexdigest()
        r = int(video_hash[0:2], 16)
        g = int(video_hash[2:4], 16)
        b = int(video_hash[4:6], 16)

        # Create a 1280x720 image (16:9 aspect ratio, standard for videos)
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(r, g, b))
        draw = ImageDraw.Draw(img)

        # Draw a frame
        draw.rectangle(
            [(10, 10), (width - 10, height - 10)], outline=(255, 255, 255), width=5
        )

        # Get filename without path for display
        video_filename = os.path.basename(video_path)

        # Add video filename as text
        text_color = (255, 255, 255)  # White text for contrast

        # Create a simpler text-based thumbnail since we don't know what fonts are available
        try:
            # Try to load a font if available (but don't fail if not)
            font = None
            try:
                # Try system fonts that are likely to be available
                system_fonts = [
                    "/System/Library/Fonts/Helvetica.ttc",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                    # Add more common font paths if needed
                ]

                for font_path in system_fonts:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, 36)
                        break
            except Exception:
                # If loading specific fonts fails, use default
                pass

            # Draw the text in the center
            draw.text(
                (width / 2, height / 2),
                f"Video: {video_filename[:30]}...",
                fill=text_color,
                font=font,
                anchor=(
                    "mm" if hasattr(ImageDraw.ImageDraw, "textbbox") else None
                ),  # Only use anchor if supported
            )

            # Draw additional text explaining this is a placeholder
            draw.text(
                (width / 2, height / 2 + 50),
                "Auto-generated thumbnail",
                fill=text_color,
                font=font,
                anchor=(
                    "mm" if hasattr(ImageDraw.ImageDraw, "textbbox") else None
                ),  # Only use anchor if supported
            )
        except Exception as text_error:
            # If advanced text rendering fails, fall back to even simpler approach
            logger.warning(
                f"Error in text rendering, using simpler approach: {text_error}"
            )

            # Draw simple text centered approximately
            draw.text(
                (width // 2 - 150, height // 2 - 20),
                f"Video Thumbnail",
                fill=text_color,
            )
            draw.text(
                (width // 2 - 150, height // 2 + 20), "Auto-generated", fill=text_color
            )

        # Save the image
        img.save(thumbnail_path, "JPEG", quality=95)

        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            logger.info(
                f"✅ Successfully created placeholder thumbnail: {thumbnail_path}"
            )
            return thumbnail_path
        else:
            logger.error("❌ Placeholder thumbnail was not created or is empty")
            return None
    except Exception as e:
        logger.error(f"❌ Error creating placeholder thumbnail: {e}")
        return None
