from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

# Configure logging
logger = logging.getLogger(__name__)


def validate_twilio_credentials(account_sid: str, auth_token: str) -> bool:
    """
    Validate Twilio credentials by attempting to fetch account details.

    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token

    Returns:
        True if credentials are valid, False otherwise
    """
    if not account_sid or not auth_token:
        logger.warning("Twilio account_sid or auth_token is missing")
        return False

    try:
        client = Client(account_sid, auth_token)
        # Try to fetch account details to validate credentials
        account = client.api.accounts(account_sid).fetch()
        logger.info(
            f"Twilio credentials validated successfully (Account: {account.friendly_name})"
        )
        return True
    except TwilioRestException as e:
        if e.code == 20003:  # Authentication Error
            logger.error("Invalid Twilio credentials")
        else:
            logger.error(f"Twilio API error: {e.msg}")
        return False
    except Exception as e:
        logger.error("Error validating Twilio credentials")
        return False


def send_sms(
    account_sid: str, auth_token: str, from_number: str, to_number: str, message: str
):
    """
    Send an SMS using Twilio with the given message.

    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token
        from_number: Sender phone number (must be registered with Twilio)
        to_number: Recipient phone number
        message: SMS message content

    Returns:
        The Twilio message SID if successful

    Raises:
        ValueError: If required parameters are missing
        RuntimeError: If Twilio API call fails
    """
    # Validate required parameters
    if not all([account_sid, auth_token, from_number, to_number]):
        logger.error("Missing required Twilio credentials")
        raise ValueError(
            "All Twilio parameters (account_sid, auth_token, from_number, to_number) are required"
        )

    if not message:
        logger.warning("Empty message provided to Twilio notifier")
        message = "No message content provided"

    # Validate credentials before attempting to send
    if not validate_twilio_credentials(account_sid, auth_token):
        raise RuntimeError(
            "Invalid Twilio credentials. Please check your account_sid and auth_token."
        )

    # Ensure message length is within SMS limits (160 chars for single SMS)
    # For longer messages, Twilio will automatically split into multiple SMS
    if len(message) > 1600:  # Limiting to 10 SMS worth of content (160 * 10)
        logger.warning(
            f"Message too long ({len(message)} chars), truncating to 1600 chars"
        )
        message = message[:1597] + "..."

    try:
        client = Client(account_sid, auth_token)
        twilio_message = client.messages.create(
            body=message, from_=from_number, to=to_number
        )
        logger.info(f"SMS sent successfully with SID: {twilio_message.sid}")
        return twilio_message.sid
    except TwilioRestException as e:
        error_message = "Twilio SMS sending failed"
        if e.code == 21211:
            error_message = f"Invalid 'to' phone number: {to_number}"
        elif e.code == 21606:
            error_message = f"Invalid 'from' phone number: {from_number}"

        logger.error(error_message)
        raise RuntimeError(f"Twilio SMS sending failed")
    except Exception as e:
        logger.error(f"Failed to send Twilio SMS")
        raise RuntimeError(f"Twilio SMS sending failed")


def send_batch_sms(
    account_sid: str, auth_token: str, from_number: str, to_numbers: list, message: str
):
    """
    Send the same SMS to multiple recipients.

    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token
        from_number: Sender phone number
        to_numbers: List of recipient phone numbers
        message: SMS message content

    Returns:
        Dictionary mapping recipient numbers to message SIDs or error messages
    """
    if not to_numbers:
        logger.warning("No recipients provided for batch SMS")
        return {}

    # First validate credentials to avoid multiple failed attempts
    if not validate_twilio_credentials(account_sid, auth_token):
        logger.error("Invalid Twilio credentials. Batch SMS not sent.")
        return {
            num: {"status": "failed", "error": "Invalid Twilio credentials"}
            for num in to_numbers
        }

    results = {}
    for to_number in to_numbers:
        try:
            message_sid = send_sms(
                account_sid, auth_token, from_number, to_number, message
            )
            results[to_number] = {"status": "success", "message_sid": message_sid}
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {str(e)}")
            results[to_number] = {"status": "failed", "error": str(e)}

    return results
