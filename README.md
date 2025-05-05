# 🚀 Facebook Ads Automation System

An automated system for uploading Facebook ad campaigns directly from Google Sheets using the Facebook Marketing API.

## ✨ Features

- 📊 **Spreadsheet Integration**: Read campaign data directly from Google Sheets
- 📱 **Multiple Device Targeting**: Target Android devices, iOS devices, or both
- 🖼️ **Multi-Image Campaigns**: Automatically create multiple ad layers from multiple media URLs
- 🔄 **Channel Tracking**: Automatically increments channel parameters for each ad layer
- 📋 **Special Ad Categories**: Support for Facebook's special ad categories
- ✅ **Status Tracking**: Updates Google Sheets with upload status and error messages
- 📲 **SMS Notifications**: Receive SMS alerts about upload status via Twilio
- 🤖 **AI Integration**: Connects to Claude AI via Model Context Protocol (MCP)

## 📋 Prerequisites

- Python 3.8+ installed on your system
- A Facebook developer account and app with Marketing API access
- A Google Cloud account with Google Sheets API enabled
- A Twilio account (optional, for SMS notifications)
- An Anthropic API key (optional, for Claude AI integration)

## 🔧 Configuration

### Environment Setup

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

| Column Name         | Description                                    | Required |
| ------------------- | ---------------------------------------------- | -------- |
| Upload              | Set to "yes" to upload this campaign           | Yes      |
| Platform            | Set to "fb api" for Facebook API campaigns     | Yes      |
| Topic               | Campaign topic/name                            | Yes      |
| Country             | Target country (name or 2-letter code)         | Yes      |
| Device Targeting    | "all", "android_only", or "ios_only"           | No       |
| Title               | Ad headline                                    | Yes      |
| Body                | Ad primary text                                | Yes      |
| Query               | Search query for landing page URL              | Yes      |
| Media Path          | Image URL(s) separated by spaces               | Yes      |
| Special Ad Category | Facebook special ad category (e.g., "HOUSING") | No       |
| Hash ID             | Unique identifier for the campaign             | No       |

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
