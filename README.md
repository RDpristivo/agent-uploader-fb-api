# 🚀 Facebook Ads Automation System

An easy-to-use system that automatically creates and uploads Facebook ad campaigns directly from your Google Sheets data. No coding required!

> **Recent Updates (May 18, 2025)**: Fixed PBIA integration for image creatives and enhanced video thumbnail extraction. See [UPDATES.md](UPDATES.md) for details.

## 💼 Business Benefits

- **Save Time**: Create multiple ad campaigns in minutes instead of hours
- **Reduce Errors**: Automated uploads eliminate manual entry mistakes
- **Track Performance**: Keep all campaign data organized in one spreadsheet
- **Scale Easily**: Launch dozens of campaigns with different images at once

## ✨ Features

- 📊 **Spreadsheet Integration**: Read campaign data directly from Google Sheets
- 📱 **Multiple Device Targeting**: Target Android devices, iOS devices, or both
- 🖼️ **Multi-Image Campaigns**: Automatically create multiple ad variations from multiple images
- 🔄 **Channel Tracking**: Automatically increments channel parameters for each ad
- 📋 **Special Ad Categories**: Support for Facebook's special ad categories
- ✅ **Status Tracking**: Updates Google Sheets with upload status and error messages
- 📲 **SMS Notifications**: Receive text alerts about upload status
- 🤖 **AI Integration**: Connects to Claude AI to help optimize campaigns

## 🏃‍♀️ Quick Start for Non-Technical Users

1. **Fill in the Google Sheet**: Add your campaign details to our template
2. **Set "Upload" to "yes"**: Only rows with "yes" in the Upload column will be processed
3. **Wait for confirmation**: You'll receive an SMS when your campaigns are live
4. **Check the Status column**: The sheet will update with "Success" or error details

Need help? Contact the marketing tech team on Slack at #marketing-automation-help

## 📋 For the Technical Team

### Prerequisites

- Python 3.8+ installed on your system
- A Facebook developer account and app with Marketing API access
- A Google Cloud account with Google Sheets API enabled
- A Twilio account (optional, for SMS notifications)
- An Anthropic API key (optional, for Claude AI integration)
- Pillow library (for image processing)
- ffmpeg (optional, for video thumbnail extraction)

### 🔧 Configuration

#### Environment Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Set up the `.env` file with your credentials:

   ```
   # Facebook API Credentials
   FB_APP_ID="your_app_id"
   FB_APP_SECRET="your_app_secret"
   FB_ACCESS_TOKEN="your_access_token"
   FB_AD_ACCOUNT_ID="act_your_ad_account_id"
   FB_PAGE_ID="your_page_id"
   FB_PIXEL_ID="your_pixel_id"
   FB_API_VERSION="v22.0"
   FB_PBIA="your_instagram_account_id"  # Page-Backed Instagram Account ID

   # Google Sheets Credentials
   GOOGLE_CREDENTIALS_FILE="service_account_credentials.json"
   GOOGLE_SPREADSHEET_ID="your_spreadsheet_id"

   # Twilio Credentials
   TWILIO_ACCOUNT_SID="your_twilio_sid"
   TWILIO_AUTH_TOKEN="your_twilio_auth_token"
   TWILIO_FROM_NUMBER="+1234567890"
   TWILIO_TO_NUMBER="+1234567890"

   # Claude AI
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   ```

3. Ensure you have the Google service account JSON file (`service_account_credentials.json`) in the root directory.

### 📝 Google Sheet Setup

Your Google Sheet should include the following columns:

| Column Name         | Description                                               | Required    | Example                                                       |
| ------------------- | --------------------------------------------------------- | ----------- | ------------------------------------------------------------- |
| Upload              | Type "yes" when you want to create this campaign          | Yes         | yes                                                           |
| Platform            | Must be set to "fb api" for Facebook campaigns            | Yes         | fb api                                                        |
| Topic               | What your campaign is about (becomes the campaign name)   | Yes         | Summer Sale                                                   |
| Country             | Which country to target ads to                            | Yes         | US or United States                                           |
| Device Targeting    | Which devices to show ads on                              | No          | all (default), android_only, or ios_only                      |
| Title               | The headline that appears in your ad                      | Yes         | 50% Off Summer Collection                                     |
| Body                | The main text of your advertisement                       | Yes         | Shop our summer collection with free shipping!                |
| Query               | Keyword used in the landing page URL                      | Yes         | summer sale                                                   |
| Media Path          | URL(s) to the images you want to use, separated by spaces | Yes         | https://example.com/image1.jpg https://example.com/image2.jpg |
| Special Ad Category | For housing, credit, employment, or politics ads          | No          | HOUSING, CREDIT, EMPLOYMENT, POLITICS                         |
| Hash ID             | Unique identifier for tracking (auto-generated if empty)  | No          | abc123                                                        |
| Status              | Shows if upload succeeded or failed (don't fill this in)  | Auto-filled | Success or Error message                                      |

#### Tips for Filling Out the Sheet:

- Put each campaign on a separate row
- For multiple images, paste all URLs in the Media Path column with spaces between them
- The system will create separate ads for each image and increment the channel number
- Always double-check country codes and image URLs before setting Upload to "yes"

## 🚀 Running the Automation

To run the automation with the current date's tab (formatted as DD/MM):

```
python -m facebook_ads_uploader
```

To specify a specific tab and enable debug mode:

```
python -m facebook_ads_uploader --tab "01/05" --debug
```

## 🔍 How It Works

1. The system connects to your Google Sheet and reads the data from the specified tab
2. It filters rows where "Upload" is "yes" and "Platform" is "fb api"
3. For each row:
   - It creates a Facebook campaign based on your configuration
   - If multiple media URLs are specified, it creates multiple ad layers
   - Each ad layer gets an incremented channel parameter in the URL
   - Device targeting is applied based on the "Device Targeting" column
   - Special ad categories are read from the "Special Ad Category" column
4. After processing, it updates the Status and Error columns in the sheet
5. An SMS notification is sent with the summary of results

## 🤖 MCP Server for Claude AI

The system includes a Model Context Protocol (MCP) server for connecting to Claude AI:

1. Ensure your `.env` file includes the `ANTHROPIC_API_KEY`
2. To start the MCP server:
   ```
   python -m facebook_ads_uploader.mcp_server
   ```
3. The server will run on http://localhost:5000/
4. You can connect external tools that support MCP to use Claude AI

## 📊 Understanding Ad Layers

When providing multiple image URLs in the "Media Path" column, the system will:

1. Create a single campaign and ad set
2. Create multiple ads within that ad set, one for each image URL
3. Automatically increment the "channel" parameter in the landing page URL, keeping the token unchanged
4. Each ad will be named "[Campaign Name] Ad 1", "[Campaign Name] Ad 2", etc.

Example URL transformation:

- First ad: `https://kosearch.com/?token=XXXX&channel=YYY1&oxd=1&q=query`
- Second ad: `https://kosearch.com/?token=XXXX&channel=YYY2&oxd=1&q=query`
- Third ad: `https://kosearch.com/?token=XXXX&channel=YYY3&oxd=1&q=query`

## 📱 Device Targeting

You can target specific devices by setting the "Device Targeting" column:

- "all" - Target both Android and iOS devices (default)
- "android_only" - Target only Android devices
- "ios_only" - Target only iOS devices

## ❓ Troubleshooting

### Common Issues

1. **Authentication Failures**:

   - Ensure your credentials in the `.env` file are correct and up to date
   - For Facebook, check that your access token hasn't expired

2. **Google Sheet Access Issues**:

   - Verify that your service account has edit access to the Google Sheet
   - Check that the tab name exists and is formatted correctly (DD/MM)

3. **Missing Columns**:

   - Ensure your Google Sheet has all the required columns
   - Column names are case-insensitive, but must match expected names

4. **Image Upload Failures**:
   - Verify that image URLs are accessible and are in formats supported by Facebook
   - Check that images meet Facebook's size and content requirements

For more help, run with the `--debug` flag to see detailed error messages.

Run the uploader with debug mode enabled:

```bash
python -m facebook_ads_uploader --debug
```

## 🧪 Testing

The system includes comprehensive testing utilities for validating functionality:

### Automated Tests

Run all automated tests:

```bash
python -m unittest discover tests
```

### Testing Video Thumbnail Generation

The system includes a robust thumbnail generation mechanism for video ads, with multiple fallback options:

1. Extract thumbnail using ffmpeg (if available)
2. Generate a placeholder thumbnail using Pillow
3. Use a reliable image URL as a last resort

To test thumbnail extraction:

```bash
# Test the fallback mechanism with a non-existent video
python -m facebook_ads_uploader.test_utils thumbnail

# Test with a real video file
python -m facebook_ads_uploader.test_utils thumbnail /path/to/your/video.mp4
```

### Testing PBIA Integration

The system supports PBIA (Page-Backed Instagram Account) integration, allowing ads to display your Facebook Page's identity on Instagram. This requires proper configuration of the `use_page_actor_override` parameter and the Instagram user ID.

To test PBIA integration for both image and video creatives:

```bash
# Test PBIA integration with default test URLs
python -m facebook_ads_uploader.test_pbia

# Test with specific URLs
python -m facebook_ads_uploader.test_pbia --image-url "https://example.com/image.jpg" --video-url "https://example.com/video.mp4"

# Test only image PBIA integration
python -m facebook_ads_uploader.test_pbia --image-only

# Test only video PBIA integration
python -m facebook_ads_uploader.test_pbia --video-only

# Test with real-world URLs from production logs
python -m facebook_ads_uploader.test_pbia --real-world
```

This test verifies that:

1. The `use_page_actor_override` parameter is correctly set to `True`
2. The `instagram_user_id` parameter is correctly set with the PBIA ID
3. Both image and video creatives properly handle these PBIA parameters

For more information about testing, see the [tests/README.md](tests/README.md) file.

## 🔒 Instagram Identity Integration (PBIA)

The system supports Facebook's Page-Backed Instagram Account (PBIA) integration, which allows your ads to display your Facebook Page's identity when shown on Instagram.

### How PBIA Works

1. Your Facebook Page must be linked to an Instagram account (done in Facebook Business Settings)
2. The Instagram account ID (PBIA ID) must be provided in the environment variable `FB_PBIA`
3. Two key parameters must be properly set for PBIA to work:
   - `use_page_actor_override`: Must be set to `True`
   - `instagram_user_id` (or `instagram_actor_id` for older API versions): Must be set to your PBIA ID

### PBIA Configuration

1. Set the `FB_PBIA` environment variable with your Instagram account ID:

   ```
   FB_PBIA="your_instagram_account_id"
   ```

2. The system automatically handles the rest, ensuring proper PBIA integration for both image and video ads

### Troubleshooting PBIA Issues

If your ads aren't showing with the correct identity on Instagram:

1. Verify the `FB_PBIA` environment variable is correctly set
2. Run the PBIA test to verify proper integration:
   ```
   python -m facebook_ads_uploader.test_pbia
   ```
3. Check the Facebook Ad Manager UI under the "Identity" section - it should show "Use Facebook Page"
4. Ensure your Facebook Page is properly linked to your Instagram account in Facebook Business Settings

#### Known PBIA Behavior

The Facebook API handling of PBIA parameters may vary between image and video creatives:

1. For **video creatives**:

   - The `use_page_actor_override` and `instagram_user_id` parameters are required and should both be set
   - The Facebook Ad UI reliably shows "Use Facebook Page" option

2. For **image creatives**:

   - The `use_page_actor_override` parameter must be set to `true` in the API call
   - However, the API may not return this parameter in the response, even when it's properly applied
   - The success of PBIA integration can be verified by checking the `instagram_user_id` in the response
   - You can also verify in the Facebook Ad UI if the "Use Facebook Page" option appears

3. Testing with real-world URLs:
   ```
   python -m facebook_ads_uploader.test_pbia --real-world
   ```
   This uses the exact URLs from production logs to verify PBIA integration works consistently
