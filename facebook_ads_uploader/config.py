import yaml
import os
import re
from dotenv import load_dotenv


def replace_env_vars(value):
    """
    Replace environment variable placeholders ${VAR_NAME} with their values.
    """
    if isinstance(value, str):
        pattern = r"\${([^}]+)}"
        matches = re.findall(pattern, value)
        for match in matches:
            env_var = os.getenv(match)
            if env_var is not None:
                value = value.replace(f"${{{match}}}", env_var)
    return value


def process_dict_env_vars(config_dict):
    """
    Recursively process a dictionary and replace environment variable placeholders.
    """
    for key, value in config_dict.items():
        if isinstance(value, dict):
            process_dict_env_vars(value)
        else:
            config_dict[key] = replace_env_vars(value)
    return config_dict


def load_config(path: str = "defaults.yaml") -> dict:
    """
    Load YAML configuration from the given path and overlay with environment variables.
    Environment variables take precedence over YAML config.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load base configuration from YAML
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if not config:
        config = {}

    # Initialize sections if they don't exist
    config.setdefault("facebook", {})
    config.setdefault("google_sheets", {})

    # Override with environment variables
    # Facebook credentials
    if os.getenv("FB_APP_ID"):
        config["facebook"]["app_id"] = os.getenv("FB_APP_ID")
    if os.getenv("FB_APP_SECRET"):
        config["facebook"]["app_secret"] = os.getenv("FB_APP_SECRET")
    if os.getenv("FB_ACCESS_TOKEN"):
        config["facebook"]["access_token"] = os.getenv("FB_ACCESS_TOKEN")
    if os.getenv("FB_AD_ACCOUNT_ID"):
        config["facebook"]["ad_account_id"] = os.getenv("FB_AD_ACCOUNT_ID")
    if os.getenv("FB_PAGE_ID"):
        config["facebook"]["page_id"] = os.getenv("FB_PAGE_ID")
    if os.getenv("FB_PIXEL_ID"):
        config["facebook"]["pixel_id"] = os.getenv("FB_PIXEL_ID")
    if os.getenv("FB_API_VERSION"):
        config["facebook"]["api_version"] = os.getenv("FB_API_VERSION")

    # Google Sheets credentials
    if os.getenv("GOOGLE_CREDENTIALS_FILE"):
        config["google_sheets"]["credentials_file"] = os.getenv(
            "GOOGLE_CREDENTIALS_FILE"
        )
    if os.getenv("GOOGLE_SPREADSHEET_ID"):
        config["google_sheets"]["spreadsheet_id"] = os.getenv("GOOGLE_SPREADSHEET_ID")

    # Twilio credentials
    if os.getenv("TWILIO_ACCOUNT_SID"):
        config.setdefault("twilio", {})["account_sid"] = os.getenv("TWILIO_ACCOUNT_SID")
    if os.getenv("TWILIO_AUTH_TOKEN"):
        config.setdefault("twilio", {})["auth_token"] = os.getenv("TWILIO_AUTH_TOKEN")
    if os.getenv("TWILIO_FROM_NUMBER"):
        config.setdefault("twilio", {})["from_number"] = os.getenv("TWILIO_FROM_NUMBER")
    if os.getenv("TWILIO_TO_NUMBER"):
        config.setdefault("twilio", {})["to_number"] = os.getenv("TWILIO_TO_NUMBER")

    return config


def load_platforms_config(path: str = "platforms.yaml") -> dict:
    """
    Load platform mappings from YAML file with environment variable substitution.
    """
    try:
        with open(path, "r") as f:
            platforms_config = yaml.safe_load(f)

        # Replace environment variables in the configuration
        if "platforms" in platforms_config:
            process_dict_env_vars(platforms_config["platforms"])

        return platforms_config.get("platforms", {})
    except FileNotFoundError:
        return {"fb api": {}}  # Default mapping for backward compatibility
