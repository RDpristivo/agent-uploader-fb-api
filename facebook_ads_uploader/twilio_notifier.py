from twilio.rest import Client


def send_sms(
    account_sid: str, auth_token: str, from_number: str, to_number: str, message: str
):
    """
    Send an SMS using Twilio with the given message.
    """
    client = Client(account_sid, auth_token)
    client.messages.create(body=message, from_=from_number, to=to_number)
