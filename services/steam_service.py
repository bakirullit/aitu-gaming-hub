from __future__ import annotations

import json
import logging
import re
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.config import Settings, settings

logger = logging.getLogger("services.steam_service")


class SteamService:
    """
    Comprehensive service for Steam OpenID 2.0 authentication,
    Steam Web API integrations (profile summaries & bans),
    and legacy vanity URL / SteamID64 parsing.
    """

    OPENID_GATEWAY_URL = "https://steamcommunity.com/openid/login"
    STEAM_RESOLVE_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
    STEAM_SUMMARIES_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    STEAM_BANS_URL = "https://api.steampowered.com/ISteamUser/GetPlayerBans/v1/"

    STATE_PREFIX = "steam:state:"
    STATUS_PREFIX = "steam:status:"
    DEFAULT_STATE_TTL_SECONDS = 900  # 15 minutes

    def __init__(self, settings_obj: Settings = settings) -> None:
        self.settings = settings_obj
        self.steam_api_key = settings_obj.STEAM_API_KEY

    # =========================================================================
    # 1. State Management (Session tokens in Redis)
    # =========================================================================

    async def create_login_state(
        self,
        telegram_id: int,
        redis: Redis,
        extra_data: dict[str, Any] | None = None,
        ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
    ) -> str:
        """
        Generates a cryptographically secure one-time session token (state)
        and stores the associated telegram_id and optional payload in Redis.
        Also initializes state status for Telegram Mini App polling.
        """
        state = secrets.token_urlsafe(32)
        payload = {
            "telegram_id": telegram_id,
            "extra_data": extra_data or {},
        }
        key = f"{self.STATE_PREFIX}{state}"
        status_key = f"{self.STATUS_PREFIX}{state}"
        await redis.set(key, json.dumps(payload), ex=ttl_seconds)
        await redis.set(
            status_key,
            json.dumps({"status": "pending", "telegram_id": telegram_id}),
            ex=ttl_seconds,
        )
        logger.info(f"Created Steam login state for telegram_id={telegram_id} (TTL={ttl_seconds}s)")
        return state

    async def verify_and_consume_state(
        self,
        state: str,
        redis: Redis,
    ) -> dict[str, Any] | None:
        """
        Verifies the state token against Redis.
        If valid, atomically removes the state (protecting against replay attacks)
        and returns the stored state dictionary.
        Returns None if missing or expired.
        """
        if not state or not state.strip():
            return None

        key = f"{self.STATE_PREFIX}{state.strip()}"
        raw_val = await redis.get(key)
        if not raw_val:
            return None

        await redis.delete(key)
        try:
            data = json.loads(raw_val)
            if isinstance(data, dict):
                return data
            # Fallback for plain telegram_id string
            return {"telegram_id": int(raw_val), "extra_data": {}}
        except Exception:
            return {"telegram_id": int(raw_val), "extra_data": {}}

    async def set_login_status(
        self,
        state: str,
        redis: Redis,
        status_val: str,
        data: dict[str, Any] | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        """
        Sets the completion/failure status of a Steam login session for TMA polling.
        """
        if not state or not state.strip():
            return
        key = f"{self.STATUS_PREFIX}{state.strip()}"
        payload = {"status": status_val, **(data or {})}
        await redis.set(key, json.dumps(payload), ex=ttl_seconds)

    async def get_login_status(
        self,
        state: str,
        redis: Redis,
    ) -> dict[str, Any] | None:
        """
        Retrieves current session status for Telegram Mini App polling.
        """
        if not state or not state.strip():
            return None
        key = f"{self.STATUS_PREFIX}{state.strip()}"
        raw = await redis.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return {"status": "unknown"}

    # =========================================================================
    # 2. OpenID 2.0 Flow Construction & Validation
    # =========================================================================

    def build_bridge_url(self, state: str, base_url: str = "") -> str:
        """
        Constructs the Telegram Mini App bridge URL.
        """
        clean_base = (base_url or self.settings.WEBAPP_URL).rstrip("/")
        return f"{clean_base}/auth/steam/bridge?state={state}"

    def build_login_url(self, state: str, base_url: str = "") -> str:
        """
        Constructs the bot auth entry URL pointing to FastAPI /api/v1/auth/steam/login?state={state}.
        """
        clean_base = (base_url or self.settings.WEBAPP_URL).rstrip("/")
        return f"{clean_base}/api/v1/auth/steam/login?state={state}"

    def build_openid_login_url(self, state: str, base_url: str) -> str:
        """
        Constructs the official Steam OpenID 2.0 authorization redirect URL.
        """
        clean_base = base_url.rstrip("/")
        realm = f"{clean_base}/"
        return_to = f"{clean_base}/api/v1/auth/steam/callback?state={state}"

        params = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": return_to,
            "openid.realm": realm,
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
        return f"{self.OPENID_GATEWAY_URL}?{urlencode(params)}"

    async def validate_openid_response(
        self,
        query_params: dict[str, str],
    ) -> tuple[bool, str | None]:
        """
        Validates the incoming OpenID 2.0 signature by sending a check_authentication
        POST request back to Steam Community gateway.
        Returns (is_valid: bool, steam_id: str | None).
        """
        mode = query_params.get("openid.mode")
        if mode == "cancel":
            logger.info("Steam login cancelled by user.")
            return False, None

        claimed_id = query_params.get("openid.claimed_id", "")
        match = re.search(r"^https://steamcommunity\.com/openid/id/(\d+)$", claimed_id)
        if not match:
            logger.warning(f"Invalid or missing openid.claimed_id: {claimed_id}")
            return False, None

        steam_id = match.group(1)

        # Prepare check_authentication payload: copy openid.* parameters
        post_data: dict[str, str] = {}
        for k, v in query_params.items():
            if k.startswith("openid."):
                post_data[k] = v

        post_data["openid.mode"] = "check_authentication"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    self.OPENID_GATEWAY_URL,
                    data=post_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if res.status_code != 200:
                    logger.warning(f"Steam OpenID verification responded with status {res.status_code}")
                    return False, None

                # Steam responds with key-value pairs in plaintext
                # e.g. "ns:http://specs.openid.net/auth/2.0\nis_valid:true\n"
                response_text = res.text
                is_valid = any(
                    line.strip() == "is_valid:true"
                    for line in response_text.splitlines()
                )

                if is_valid:
                    logger.info(f"Successfully verified Steam OpenID signature for steam_id={steam_id}")
                    return True, steam_id
                else:
                    logger.warning(f"Steam OpenID signature check rejected: {response_text.strip()}")
                    return False, None
        except Exception as exc:
            logger.error(f"Error communicating with Steam OpenID verification endpoint: {exc}")
            return False, None

    # =========================================================================
    # 3. Steam Web API Integrations (Summaries & Bans)
    # =========================================================================

    async def get_player_summaries(self, steam_id: str) -> dict[str, Any] | None:
        """
        Fetches player profile summaries (personaname, avatar, profileurl) via Steam Web API.
        Returns player dict or None if API key unset or request failed.
        """
        if not self.steam_api_key:
            logger.debug("STEAM_API_KEY is not configured; skipping player summaries.")
            return None

        params = {
            "key": self.steam_api_key,
            "steamids": steam_id,
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(self.STEAM_SUMMARIES_URL, params=params)
                if res.status_code == 200:
                    players = res.json().get("response", {}).get("players", [])
                    if players:
                        return players[0]
        except Exception as exc:
            logger.warning(f"Failed to fetch player summaries for steam_id={steam_id}: {exc}")
        return None

    async def get_player_bans(self, steam_id: str) -> dict[str, Any] | None:
        """
        Fetches player VAC / Community bans via Steam Web API.
        Returns bans dict or None if API key unset or request failed.
        """
        if not self.steam_api_key:
            logger.debug("STEAM_API_KEY is not configured; skipping player bans.")
            return None

        params = {
            "key": self.steam_api_key,
            "steamids": steam_id,
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(self.STEAM_BANS_URL, params=params)
                if res.status_code == 200:
                    players = res.json().get("players", [])
                    if players:
                        return players[0]
        except Exception as exc:
            logger.warning(f"Failed to fetch player bans for steam_id={steam_id}: {exc}")
        return None

    # =========================================================================
    # 4. Legacy Validation & Vanity URL Resolution (for backwards compatibility)
    # =========================================================================

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


def render_steam_success_html(
    persona_name: str,
    steam_id: str,
    avatar_url: str | None = None,
    is_vac: bool = False,
    is_community: bool = False,
    bot_username: str = "aitu_gaming_bot",
) -> str:
    """Renders a sleek, dark-themed responsive HTML page confirming Steam linking."""
    tg_url = f"https://t.me/{bot_username}"
    tg_app_url = f"tg://resolve?domain={bot_username}"

    avatar_markup = (
        f'<img src="{avatar_url}" alt="{persona_name}" class="avatar" />'
        if avatar_url
        else '<div class="avatar-placeholder"><svg viewBox="0 0 24 24" width="28" height="28" fill="#818cf8"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1V12h3v3h-3v6.95C18.05 21.45 22 17.19 22 12c0-5.52-4.48-10-10-10z"/></svg></div>'
    )

    ban_badge = (
        '<span class="ban-status ban-warn">⚠️ Обнаружены ограничения</span>'
        if (is_vac or is_community)
        else '<span class="ban-status ban-clean">✅ Чистый аккаунт (без банов)</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AITU Gaming Hub — Steam верифицирован</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: radial-gradient(circle at 50% 20%, #1e1b4b 0%, #0b0f19 70%, #05070d 100%);
      color: #f1f5f9;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .card {{
      background: rgba(22, 30, 46, 0.9);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(99, 102, 241, 0.35);
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7), 0 0 50px rgba(99, 102, 241, 0.2);
      border-radius: 24px;
      max-width: 440px;
      width: 100%;
      padding: 40px 28px;
      text-align: center;
      animation: fadeIn 0.4s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .badge-icon {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 35px rgba(16, 185, 129, 0.45);
      margin-bottom: 24px;
    }}
    .badge-icon svg {{ width: 44px; height: 44px; fill: white; }}
    h1 {{
      font-size: 24px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }}
    .sub {{
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 26px;
    }}
    .profile-box {{
      background: rgba(31, 41, 61, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 16px;
      text-align: left;
      margin-bottom: 28px;
    }}
    .avatar {{
      width: 58px;
      height: 58px;
      border-radius: 14px;
      border: 2px solid #6366f1;
      object-fit: cover;
      flex-shrink: 0;
    }}
    .avatar-placeholder {{
      width: 58px;
      height: 58px;
      border-radius: 14px;
      background: #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid #6366f1;
      flex-shrink: 0;
    }}
    .profile-info {{ flex: 1; min-width: 0; }}
    .persona {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .steamid {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #818cf8;
      margin-top: 3px;
    }}
    .ban-status {{
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      margin-top: 4px;
    }}
    .ban-clean {{ color: #34d399; }}
    .ban-warn {{ color: #f87171; }}
    .btn-tg {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
      color: #ffffff;
      text-decoration: none;
      font-weight: 700;
      font-size: 15px;
      padding: 14px 20px;
      border-radius: 14px;
      box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
      transition: all 0.2s ease;
    }}
    .btn-tg:hover {{
      transform: translateY(-2px);
      box-shadow: 0 12px 30px rgba(99, 102, 241, 0.5);
    }}
    .footer-note {{
      font-size: 12px;
      color: #64748b;
      margin-top: 20px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge-icon">
      <svg viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
    </div>
    <h1>Steam успешно привязан!</h1>
    <p class="sub">Ваш профиль верифицирован для участия в открытых киберспортивных турнирах AITU Gaming Hub.</p>
    
    <div class="profile-box">
      {avatar_markup}
      <div class="profile-info">
        <div class="persona">{persona_name}</div>
        <div class="steamid">SteamID: {steam_id}</div>
        {ban_badge}
      </div>
    </div>

    <a href="{tg_url}" class="btn-tg">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
      <span>Вернуться в Telegram</span>
    </a>
    <div class="footer-note">Вы можете закрыть эту вкладку и продолжить в боте.</div>
  </div>
</body>
</html>"""


def render_steam_error_html(
    title: str,
    message: str,
    bot_username: str = "aitu_gaming_bot",
) -> str:
    """Renders a sleek dark error page for Steam OpenID failures or cancellations."""
    tg_url = f"https://t.me/{bot_username}"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AITU Gaming Hub — {title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: radial-gradient(circle at 50% 20%, #2a1215 0%, #0b0f19 70%, #05070d 100%);
      color: #f1f5f9;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .card {{
      background: rgba(22, 30, 46, 0.9);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(239, 68, 68, 0.35);
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7), 0 0 50px rgba(239, 68, 68, 0.15);
      border-radius: 24px;
      max-width: 440px;
      width: 100%;
      padding: 40px 28px;
      text-align: center;
    }}
    .badge-icon {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 35px rgba(239, 68, 68, 0.45);
      margin-bottom: 24px;
    }}
    .badge-icon svg {{ width: 44px; height: 44px; fill: white; }}
    h1 {{
      font-size: 22px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 12px;
    }}
    .sub {{
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.6;
      margin-bottom: 28px;
    }}
    .btn-tg {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      background: #334155;
      color: #ffffff;
      text-decoration: none;
      font-weight: 700;
      font-size: 15px;
      padding: 14px 20px;
      border-radius: 14px;
      transition: all 0.2s ease;
    }}
    .btn-tg:hover {{
      background: #475569;
      transform: translateY(-2px);
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge-icon">
      <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
    </div>
    <h1>{title}</h1>
    <p class="sub">{message}</p>
    <a href="{tg_url}" class="btn-tg">
      <span>Вернуться в Telegram</span>
    </a>
  </div>
</body>
</html>"""


def render_steam_bridge_html(
    state: str,
    login_url: str,
    status_url: str,
    bot_username: str = "",
) -> str:
    """
    Renders the official Telegram Mini App (Web App) pre-flight bridge screen.
    Includes security certifications, SSL warning plaque, and native openLink transition.
    """
    bot_name = bot_username.lstrip("@") if bot_username else "aitu_gaming_bot"
    tg_url = f"https://t.me/{bot_name}"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>AITU Gaming Hub — Steam Authorization</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-color: #070a12;
      --card-bg: rgba(15, 23, 42, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --primary-glow: rgba(99, 102, 241, 0.35);
      --steam-color: #171a21;
      --steam-accent: #66c0f4;
      --success: #10b981;
      --success-glow: rgba(16, 185, 129, 0.4);
      --warning-border: rgba(245, 158, 11, 0.3);
      --warning-bg: rgba(245, 158, 11, 0.08);
      --warning-text: #fbbf24;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #070a12 65%);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 16px;
      overflow-x: hidden;
    }}

    .container {{
      max-width: 440px;
      width: 100%;
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--border-color);
      border-radius: 28px;
      padding: 32px 24px;
      box-shadow: 0 25px 70px rgba(0, 0, 0, 0.8), 0 0 50px rgba(99, 102, 241, 0.1);
      position: relative;
      overflow: hidden;
      animation: fadeIn 0.4s ease-out;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(16px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .header {{
      text-align: center;
      margin-bottom: 24px;
    }}

    .badges-row {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin-bottom: 20px;
    }}

    .brand-icon {{
      width: 56px;
      height: 56px;
      border-radius: 16px;
      background: linear-gradient(135deg, #4f46e5 0%, #312e81 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 25px var(--primary-glow);
      border: 1px solid rgba(255, 255, 255, 0.15);
    }}
    .brand-icon svg {{ width: 30px; height: 30px; fill: #ffffff; }}

    .connect-arrow {{
      color: #64748b;
      display: flex;
      align-items: center;
      font-size: 16px;
    }}

    .steam-icon {{
      width: 56px;
      height: 56px;
      border-radius: 16px;
      background: linear-gradient(135deg, #1b2838 0%, #171a21 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 25px rgba(102, 192, 244, 0.25);
      border: 1px solid rgba(102, 192, 244, 0.25);
    }}
    .steam-icon svg {{ width: 30px; height: 30px; fill: #66c0f4; }}

    .protocol-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.25);
      color: #34d399;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 5px 12px;
      border-radius: 20px;
      margin-bottom: 12px;
    }}
    .dot-live {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 1.8s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #ffffff;
      margin-bottom: 6px;
    }}

    .subtitle {{
      font-size: 13.5px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    /* The Requested Security Notice Plaque */
    .security-notice {{
      background: var(--warning-bg);
      border: 1px solid var(--warning-border);
      border-radius: 18px;
      padding: 16px;
      margin: 22px 0;
      display: flex;
      gap: 14px;
      align-items: flex-start;
      text-align: left;
    }}

    .security-icon {{
      width: 32px;
      height: 32px;
      border-radius: 10px;
      background: rgba(245, 158, 11, 0.18);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
    }}
    .security-icon svg {{
      width: 18px;
      height: 18px;
      fill: #fbbf24;
    }}

    .security-text {{
      flex: 1;
    }}
    .security-title {{
      font-size: 13px;
      font-weight: 700;
      color: #fbbf24;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .security-body {{
      font-size: 12.5px;
      color: #e2e8f0;
      line-height: 1.55;
    }}
    .security-body code {{
      font-family: 'JetBrains Mono', monospace;
      background: rgba(0, 0, 0, 0.35);
      padding: 2px 6px;
      border-radius: 6px;
      color: #fde68a;
      font-size: 11.5px;
    }}
    .security-body b {{
      color: #ffffff;
    }}

    .features-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 26px;
      text-align: left;
    }}

    .feature-item {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 14px;
      font-size: 13px;
      color: #cbd5e1;
    }}
    .feature-check {{
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 800;
      flex-shrink: 0;
    }}

    .btn-main {{
      width: 100%;
      background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
      color: #ffffff;
      border: none;
      border-radius: 16px;
      padding: 16px 20px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      box-shadow: 0 8px 30px var(--primary-glow);
      transition: all 0.25s ease;
      font-family: inherit;
    }}
    .btn-main:hover {{
      background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%);
      transform: translateY(-2px);
      box-shadow: 0 12px 35px var(--primary-glow);
    }}
    .btn-main:active {{
      transform: translateY(0);
    }}

    /* Waiting / Polling overlay */
    .waiting-box {{
      display: none;
      margin-top: 18px;
      padding: 16px;
      background: rgba(30, 41, 59, 0.6);
      border: 1px dashed rgba(99, 102, 241, 0.4);
      border-radius: 16px;
      text-align: center;
    }}
    .spinner {{
      width: 26px;
      height: 26px;
      border: 3px solid rgba(99, 102, 241, 0.25);
      border-top-color: #818cf8;
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      margin: 0 auto 10px;
    }}
    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
    .waiting-text {{
      font-size: 13px;
      color: #cbd5e1;
      font-weight: 500;
    }}
    .waiting-sub {{
      font-size: 11.5px;
      color: #94a3b8;
      margin-top: 4px;
    }}

    /* Success Card State */
    .success-card {{
      display: none;
      text-align: center;
      animation: fadeIn 0.4s ease-out;
    }}
    .success-badge {{
      width: 76px;
      height: 76px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 35px var(--success-glow);
      margin-bottom: 20px;
    }}
    .success-badge svg {{ width: 40px; height: 40px; fill: white; }}

    .profile-card {{
      background: rgba(31, 41, 61, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 14px;
      display: flex;
      align-items: center;
      gap: 14px;
      text-align: left;
      margin: 20px 0;
    }}
    .profile-avatar {{
      width: 52px;
      height: 52px;
      border-radius: 12px;
      border: 2px solid #6366f1;
      object-fit: cover;
    }}
    .profile-name {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
    }}
    .profile-id {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11.5px;
      color: #818cf8;
      margin-top: 2px;
    }}
  </style>
</head>
<body>
  <div class="container" id="app-container">

    <!-- INITIAL FLOW VIEW -->
    <div id="initial-view">
      <div class="header">
        <div class="badges-row">
          <div class="brand-icon">
            <svg viewBox="0 0 24 24"><path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-10 7H8v3H6v-3H3v-2h3V8h2v3h3v2zm4.5 2c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm4-3c-.83 0-1.5-.67-1.5-1.5S18.67 9 19.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
          </div>
          <div class="connect-arrow">⇄</div>
          <div class="steam-icon">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15.5c-.71-.34-1.29-.91-1.66-1.63l-4.14 1.71c-.08-.52-.13-1.04-.13-1.58 0-.41.04-.81.09-1.21l4.13-1.71c.21-.99.85-1.84 1.74-2.28 1.48-.73 3.29-.12 4.02 1.36.46.93.39 2-.09 2.82l3.41 1.41c.42-.39.99-.64 1.63-.64 1.38 0 2.5 1.12 2.5 2.5s-1.12 2.5-2.5 2.5c-1.35 0-2.45-1.07-2.49-2.41L12.5 16.5c-.15.42-.4.79-.73 1.07v4.23c4.56-.93 8-4.96 8-9.8 0-5.52-4.48-10-10-10z"/></svg>
          </div>
        </div>

        <div class="protocol-tag">
          <span class="dot-live"></span>
          <span>Официальный шлюз Valve OpenID 2.0</span>
        </div>

        <h1>Привязка Steam</h1>
        <p class="subtitle">Интеграция игрового профиля с AITU Gaming Hub для допуска к турнирам</p>
      </div>

      <!-- Specific User Security Plaque -->
      <div class="security-notice">
        <div class="security-icon">
          <svg viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>
        </div>
        <div class="security-text">
          <div class="security-title">Безопасность Valve Corporation</div>
          <div class="security-body">
            Вы будете перенаправлены на официальный шлюз <code>steamcommunity.com</code>. 
            Обратите внимание на <b>SSL-сертификат</b> (🔒) и адресную строку в браузере. Клуб не запрашивает и не сохраняет ваши учетные данные Steam.
          </div>
        </div>
      </div>

      <div class="features-list">
        <div class="feature-item">
          <div class="feature-check">✓</div>
          <div>Вход в 1 клик через вашу активную сессию браузера</div>
        </div>
        <div class="feature-item">
          <div class="feature-check">✓</div>
          <div>Мгновенное присвоение статуса <b>Verified Guest</b></div>
        </div>
        <div class="feature-item">
          <div class="feature-check">✓</div>
          <div>Синхронизация игрового никнейма, аватара и VAC-статуса</div>
        </div>
      </div>

      <button id="btn-login" class="btn-main" onclick="startSteamAuth()">
        <span>🎮 Войти через Steam</span>
      </button>

      <div id="waiting-box" class="waiting-box">
        <div class="spinner"></div>
        <div class="waiting-text">Ожидание подтверждения входа...</div>
        <div class="waiting-sub">Подтвердите вход в открывшемся окне браузера Steam</div>
      </div>
    </div>

    <!-- SUCCESS VIEW (Hidden until polling signals completion) -->
    <div id="success-view" class="success-card">
      <div class="success-badge">
        <svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
      </div>
      <h1>Steam успешно привязан!</h1>
      <p class="subtitle">Ваш профиль верифицирован. Окно закроется автоматически...</p>

      <div class="profile-card">
        <img id="res-avatar" class="profile-avatar" src="" alt="Avatar" style="display:none;">
        <div class="profile-info">
          <div id="res-name" class="profile-name">Игрок</div>
          <div id="res-steamid" class="profile-id">SteamID: -</div>
        </div>
      </div>
    </div>

  </div>

  <script>
    const tg = window.Telegram?.WebApp;
    if (tg) {{
      tg.ready();
      tg.expand();
      try {{
        tg.setHeaderColor('#070a12');
        tg.setBackgroundColor('#070a12');
      }} catch (e) {{}}
    }}

    const loginUrl = "{login_url}";
    const statusUrl = "{status_url}";
    let pollInterval = null;

    function startSteamAuth() {{
      const btn = document.getElementById("btn-login");
      const waiting = document.getElementById("waiting-box");
      btn.style.display = "none";
      waiting.style.display = "block";

      if (tg && typeof tg.openLink === "function") {{
        tg.openLink(loginUrl);
      }} else {{
        window.open(loginUrl, "_blank");
      }}

      // Start real-time status polling
      pollInterval = setInterval(checkAuthStatus, 1400);
    }}

    async function checkAuthStatus() {{
      try {{
        const resp = await fetch(statusUrl, {{ cache: "no-store" }});
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.status === "completed") {{
          clearInterval(pollInterval);
          showSuccess(data);
        }} else if (data.status === "failed") {{
          clearInterval(pollInterval);
          if (tg && tg.HapticFeedback) {{
            tg.HapticFeedback.notificationOccurred("error");
          }}
          alert("Ошибка привязки: " + (data.reason || "Попробуйте снова"));
          location.reload();
        }}
      }} catch (err) {{
        console.error("Status poll error:", err);
      }}
    }}

    function showSuccess(data) {{
      if (tg && tg.HapticFeedback) {{
        tg.HapticFeedback.notificationOccurred("success");
      }}

      document.getElementById("initial-view").style.display = "none";
      const successView = document.getElementById("success-view");
      successView.style.display = "block";

      if (data.avatar) {{
        const img = document.getElementById("res-avatar");
        img.src = data.avatar;
        img.style.display = "block";
      }}
      if (data.personaname) {{
        document.getElementById("res-name").textContent = data.personaname;
      }}
      if (data.steam_id) {{
        document.getElementById("res-steamid").textContent = "SteamID: " + data.steam_id;
      }}

      // Close Mini App automatically after 1.8 seconds
      setTimeout(() => {{
        if (tg && typeof tg.close === "function") {{
          tg.close();
        }}
      }}, 1800);
    }}
  </script>
</body>
</html>"""

