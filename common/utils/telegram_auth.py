import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
import logging

logger = logging.getLogger("common.utils.telegram_auth")


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400 * 7,  # Default 7 days expiry tolerance
) -> dict:
    """
    Validates Telegram WebApp initData string using HMAC-SHA256 according to Telegram specifications:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    1. Parses query string into key-value pairs.
    2. Extracts and strips 'hash'.
    3. Sorts remaining key-value pairs alphabetically as key=value separated by '\n'.
    4. Computes secret_key = HMAC_SHA256(b"WebAppData", bot_token).
    5. Computes hash = HMAC_SHA256(secret_key, data_check_string).hexdigest().
    6. Validates hash match and auth_date freshness.
    7. Returns parsed user dict and auth metadata.
    """
    if not init_data or not isinstance(init_data, str):
        raise ValueError("Empty or invalid initData string")

    try:
        parsed_items = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception as e:
        raise ValueError(f"Could not parse initData query string: {e}")

    if "hash" not in parsed_items:
        raise ValueError("Missing 'hash' parameter in initData")

    received_hash = parsed_items.pop("hash")

    # Data check string: alphabetically sorted key=value separated by '\n'
    data_check_list = [f"{k}={v}" for k, v in sorted(parsed_items.items())]
    data_check_string = "\n".join(data_check_list)

    # Calculate HMAC secret key using b"WebAppData"
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Calculate HMAC of data_check_string
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid initData cryptographic signature (hash mismatch)")

    # Validate auth_date freshness if present
    auth_date_raw = parsed_items.get("auth_date")
    if auth_date_raw:
        auth_date: int | None = None
        try:
            auth_date = int(auth_date_raw)
        except (ValueError, TypeError):
            auth_date = None

        if auth_date is not None and max_age_seconds:
            if time.time() - auth_date > max_age_seconds:
                raise ValueError("initData authentication timestamp has expired")


    # Extract user dictionary
    user_data = {}
    if "user" in parsed_items:
        try:
            user_data = json.loads(parsed_items["user"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in 'user' parameter: {e}")

    return {
        "user": user_data,
        "auth_date": auth_date_raw,
        "query_id": parsed_items.get("query_id"),
        "raw": parsed_items,
    }
