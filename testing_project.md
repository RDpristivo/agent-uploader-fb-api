# Testing Guide for Facebook Ads Automation System

This guide provides step-by-step instructions to test the Facebook Ads Automation System, ensuring all components work correctly before deploying to production.

## Prerequisites

Before testing, ensure you have:

1. Python 3.8+ installed on your system
2. A Facebook developer account with Marketing API access
3. A Google Cloud account with Google Sheets API access
4. A properly set up Google Sheet with test campaign data
5. A Twilio account (optional, for SMS notification testing)

## Setup for Testing

### 1. Environment Setup

1. Clone the repository or ensure all updated files are in place
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Configuration Files

1. Create a `.env` file with your test credentials:

   ```
   # Facebook API Credentials (Primary Platform)
   FB_APP_ID="your_test_app_id"
   FB_APP_SECRET="your_test_app_secret"
   FB_ACCESS_TOKEN="your_test_access_token"
   FB_AD_ACCOUNT_ID="act_your_test_ad_account_id"
   FB_PAGE_ID="your_test_page_id"
   FB_PIXEL_ID="your_test_pixel_id"
   FB_API_VERSION="v22.0"

   # Facebook API Credentials (Secondary Platform, if testing multiple platforms)
   FB_APP_ID_2="your_second_test_app_id"
   FB_APP_SECRET_2="your_second_test_app_secret"
   FB_ACCESS_TOKEN_2="your_second_test_access_token"
   FB_AD_ACCOUNT_ID_2="act_your_second_test_ad_account_id"
   FB_PAGE_ID_2="your_second_test_page_id"
   FB_PIXEL_ID_2="your_second_test_pixel_id"
   FB_API_VERSION_2="v22.0"

   # Google Sheets Credentials
   GOOGLE_CREDENTIALS_FILE="service_account_credentials.json"
   GOOGLE_SPREADSHEET_ID="your_test_spreadsheet_id"

   # Twilio Credentials (Optional)
   TWILIO_ACCOUNT_SID="your_test_twilio_sid"
   TWILIO_AUTH_TOKEN="your_test_twilio_auth_token"
   TWILIO_FROM_NUMBER="+1234567890"
   TWILIO_TO_NUMBER="+1234567890"
   ```

2. Verify your `platforms.yaml` is correctly configured:

   ```yaml
   platforms:
     "fb api":
       ad_account_id: "${FB_AD_ACCOUNT_ID}"
       page_id: "${FB_PAGE_ID}"
       pixel_id: "${FB_PIXEL_ID}"
       app_id: "${FB_APP_ID}"
       app_secret: "${FB_APP_SECRET}"
       access_token: "${FB_ACCESS_TOKEN}"
       api_version: "${FB_API_VERSION}"

     "fb api 2":
       ad_account_id: "${FB_AD_ACCOUNT_ID_2}"
       page_id: "${FB_PAGE_ID_2}"
       pixel_id: "${FB_PIXEL_ID_2}"
       app_id: "${FB_APP_ID_2}"
       app_secret: "${FB_APP_SECRET_2}"
       access_token: "${FB_ACCESS_TOKEN_2}"
       api_version: "${FB_API_VERSION_2}"
   ```

3. Ensure your Google service account credentials JSON file is in place and has access to your test spreadsheet

### 3. Prepare Test Data

1. Create a test tab in your Google Sheet with today's date (format: DD/MM)
2. Add at least 2-3 test campaign rows with different configurations:
   - One row with a single media URL
   - One row with multiple media URLs separated by " | "
   - One row with a different platform (e.g., "fb api 2") if testing multiple platforms
   - Set "Upload" column to "yes" for rows you want to test
   - Set "Platform" column to match your configured platforms (e.g., "fb api")

## Test Execution

### Test 1: Basic Functionality

1. Run the uploader with debug mode enabled:

   ```bash
   python -m facebook_ads_uploader --debug
   ```

2. Verify the following in console output:

   - Configuration loaded successfully
   - Connection to Google Sheet established
   - Campaigns detected and processed
   - Facebook API initialized for each platform
   - Campaigns created with expected naming conventions

3. Check the Google Sheet:
   - Status column should show "SUCCESS" for processed rows
   - Error column should contain Campaign ID or error details

### Test 2: Multiple Media URLs

1. Find a row with multiple media URLs in your test data
2. Verify in the console output:

   - Multiple media URLs detected
   - Multiple creatives created for each URL
   - Channel parameter incremented for each URL

3. Log into Facebook Ads Manager:
   - Locate the created campaign
   - Verify multiple ads exist with the correct images
   - Check landing page URLs have incremented channel parameters

### Test 3: Cross-Platform Support

1. If testing multiple platforms, run with explicit tab name:

   ```bash
   python -m facebook_ads_uploader --tab "DD/MM" --debug
   ```

2. Verify in console output:
   - Detection of different platforms for different rows
   - Correct initialization of Facebook API for each platform
   - Successful campaign creation in different ad accounts

### Test 4: Error Handling

1. Create a test row with intentional errors:

   - Invalid media URL
   - Missing required field (e.g., empty "Title")
   - Non-existent platform name

2. Run the uploader with debug mode:

   ```bash
   python -m facebook_ads_uploader --debug
   ```

3. Verify:
   - Appropriate error messages in console
   - "FAILED" status in Google Sheet status column
   - Error details in Google Sheet error column
   - Other valid rows still processed successfully

### Test 5: MCP Server Integration

1. Start the MCP server:

   ```bash
   python -m facebook_ads_uploader.mcp_server
   ```

2. Test the health endpoint using curl or a web browser:

   ```bash
   curl http://localhost:5000/health
   ```

3. Test the ping tool using curl:

   ```bash
   curl -X POST http://localhost:5000/v1/tools \
     -H "Content-Type: application/json" \
     -d '{"name": "ping"}'
   ```

4. Test campaign creation through the MCP interface:

   ```bash
   curl -X POST http://localhost:5000/v1/tools \
     -H "Content-Type: application/json" \
     -d '{
       "name": "create_maximizer_campaign",
       "parameters": {
         "topic": "Test Campaign",
         "country": "US",
         "title": "Test Ad Title",
         "body": "Test ad body text with compelling message",
         "query": "test query",
         "media_path": "https://example.com/test-image.jpg",
         "extra_prompt": "platform: fb api, device: all"
       }
     }'
   ```

5. Verify:
   - Server responds with success status
   - Campaign is created in Facebook Ads Manager
   - Correct platform and device targeting applied

## Test Validation

After running all tests, verify the following:

1. **Facebook Ads Manager**:

   - All test campaigns are created with correct naming
   - Ad sets have proper targeting settings (device, country)
   - Multiple ads created for each media URL
   - Ads have correct headline (Title) and primary text (Body)
   - Landing page URLs have correct query parameters and incremented channels

2. **Google Sheet**:

   - Status column updated for all rows
   - Error column populated with appropriate messages for failed rows
   - Success rows have campaign IDs in the error column

3. **SMS Notifications** (if Twilio configured):
   - Test phone number received notification message
   - Message contains correct success/failure counts

## Clean Up

After testing:

1. Delete test campaigns from Facebook Ads Manager to avoid spending ad budget
2. Clear or archive test data in Google Sheets
3. Stop the MCP server if it's still running

## Troubleshooting Common Issues

### Google Sheets Access Issues

- Verify service account has edit access to the spreadsheet
- Check spreadsheet ID is correct in .env file
- Ensure tab name format matches what's in the spreadsheet

### Facebook API Errors

- Verify access token hasn't expired
- Check ad account has sufficient permissions
- Ensure media URLs are accessible and in supported formats

### MCP Server Problems

- Check port 5000 is not already in use
- Verify environment variables are loaded correctly
- Check all required files are in the expected locations
