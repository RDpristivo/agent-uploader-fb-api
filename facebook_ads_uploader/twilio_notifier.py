from twilio.rest import Client
import logging

# Configure logging
logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Failed to send Twilio SMS: {str(e)}")
        raise RuntimeError(f"Twilio SMS sending failed: {str(e)}")


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
