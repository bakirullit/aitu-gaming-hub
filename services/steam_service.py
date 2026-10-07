import re
import logging
import httpx
from fastapi import HTTPException, status
from common.config import settings, Settings

logger = logging.getLogger("services.steam_service")


class SteamService:
    """Service to parse, validate, and resolve Steam community profiles and SteamID64."""

    STEAM_RESOLVE_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"

    def __init__(self, settings_obj: Settings = settings) -> None:
        self.steam_api_key = settings_obj.STEAM_API_KEY

    async def validate_and_extract_steam_id(self, steam_payload: str) -> str:
        """
        Parses and extracts a valid SteamID64 or resolves a vanity profile URL.
        1. Pure SteamID64 (17 digits, starts with 7656119...)
        2. Profiles URL: steamcommunity.com/profiles/<steamid64> or /profiles/<steamid64>
        3. Vanity URL: steamcommunity.com/id/<custom_url> or /id/<custom_url>
        Raises 400 Bad Request on invalid format or unresolvable vanity URL.
        """
        cleaned = steam_payload.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Steam payload cannot be empty.",
            )

        # 1. Direct SteamID64 check (17 digits starting with 7656119...)
        if re.fullmatch(r"7656119\d{10}", cleaned):
            return cleaned

        # 2. Profiles URL pattern
        profile_match = re.search(
            r"(?:https?://)?(?:www\.)?steamcommunity\.com/profiles/(7656119\d{10})(?:[/?#].*)?$",
            cleaned,
            re.IGNORECASE,
        )
        if not profile_match:
            # Also support relative path: /profiles/<id>
            profile_match = re.search(
                r"^/profiles/(7656119\d{10})(?:[/?#].*)?$",
                cleaned,
                re.IGNORECASE,
            )

        if profile_match:
            return profile_match.group(1)

        # 3. Vanity URL pattern
        vanity_match = re.search(
            r"(?:https?://)?(?:www\.)?steamcommunity\.com/id/([a-zA-Z0-9_\-]+)(?:[/?#].*)?$",
            cleaned,
            re.IGNORECASE,
        )
        if not vanity_match:
            # Also support relative path: /id/<custom_url>
            vanity_match = re.search(
                r"^/id/([a-zA-Z0-9_\-]+)(?:[/?#].*)?$",
                cleaned,
                re.IGNORECASE,
            )

        if vanity_match:
            vanity_url = vanity_match.group(1)

            # If vanity_url happens to be 17-digit steamid64 itself
            if re.fullmatch(r"7656119\d{10}", vanity_url):
                return vanity_url

            # If STEAM_API_KEY is configured, resolve via Steam Web API
            if self.steam_api_key:
                return await self._resolve_vanity_url(vanity_url)
            else:
                logger.info(f"STEAM_API_KEY not configured. Returning normalized vanity identifier '{vanity_url}'.")
                return vanity_url

        # 4. If none of the recognized patterns matched
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Steam identifier. Provide a raw SteamID64 (7656119...), /profiles/<id>, or /id/<custom_url> link.",
        )

    async def _resolve_vanity_url(self, vanity_url: str) -> str:
        """Call Steam Web API to resolve custom URL to SteamID64."""
        params = {
            "key": self.steam_api_key,
            "vanityurl": vanity_url,
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(self.STEAM_RESOLVE_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"Steam Web API error: status {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to communicate with Steam Web API.",
                    )
                data = response.json().get("response", {})
                if data.get("success") == 1 and data.get("steamid"):
                    return str(data["steamid"])
                else:
                    message = data.get("message", "Steam profile not found")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Steam vanity URL '{vanity_url}' could not be resolved: {message}",
                    )
        except httpx.RequestError as exc:
            logger.error(f"Network error querying Steam Web API: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to reach Steam Web API for vanity URL resolution.",
            )
