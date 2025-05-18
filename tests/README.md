# Facebook Ads Uploader Tests

This directory contains tests for the Facebook Ads Uploader application.

## Running Tests

### Running All Tests

To run all tests, execute the following command from the project root:

```sh
python -m unittest discover tests
```

### Testing Thumbnail Extraction

The thumbnail extraction module can be tested using two methods:

1. **Via Unit Tests**:

   ```sh
   python -m tests.test_facebook_api
   ```

   To test with a real video file:

   ```sh
   python -m tests.test_facebook_api /path/to/your/video.mp4
   ```

2. **Via CLI Utility**:

   ```sh
   python -m facebook_ads_uploader.test_utils thumbnail
   ```

   To test with a real video file:

   ```sh
   python -m facebook_ads_uploader.test_utils thumbnail /path/to/your/video.mp4
   ```

## Test Coverage

The test suite covers the following components:

1. **facebook_api.py**: Tests the Facebook API functionality including:
   - Video thumbnail extraction (with both ffmpeg and fallback methods)
   - Fallback mechanisms for when ffmpeg is not available
   - PBIA (Page-Backed Instagram Account) integration for both image and video creatives

## Testing PBIA Integration

The PBIA (Page-Backed Instagram Account) integration test verifies that ads can properly use your Facebook Page's identity when displayed on Instagram. This is a critical feature for brand consistency across platforms.

To run the PBIA integration test:

```sh
# Test both image and video PBIA integration with default test URLs
python -m facebook_ads_uploader.test_pbia

# Test with specific custom URLs
python -m facebook_ads_uploader.test_pbia --image-url "https://example.com/image.jpg" --video-url "https://example.com/video.mp4"

# Test only image PBIA integration
python -m facebook_ads_uploader.test_pbia --image-only

# Test only video PBIA integration
python -m facebook_ads_uploader.test_pbia --video-only

# Test with real-world URLs from production logs
python -m facebook_ads_uploader.test_pbia --real-world
```

The test verifies:

1. **Correct API parameters**: Confirms that both `use_page_actor_override` and `instagram_user_id` parameters are correctly set
2. **Image creative handling**: Verifies that image creatives properly integrate with PBIA
3. **Video creative handling**: Verifies that video creatives properly integrate with PBIA

### Prerequisites for PBIA Testing

Before running the PBIA test, ensure:

1. Environment variables are properly configured in `.env`:

   - `FB_APP_ID`
   - `FB_APP_SECRET`
   - `FB_ACCESS_TOKEN`
   - `FB_AD_ACCOUNT_ID`
   - `FB_PAGE_ID`
   - `FB_PBIA` (your Instagram account ID)

2. Your Facebook Page is linked to the Instagram account specified in `FB_PBIA`

## Adding New Tests

To add new tests, create a new test file in the `tests` directory following the naming convention:
`test_<module_name>.py`

For example, to test the `image_downloader.py` module, create a file named `test_image_downloader.py`.
