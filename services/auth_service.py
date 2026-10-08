from __future__ import annotations

import secrets
import logging
from redis.asyncio import Redis
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import resend

from common.config import settings, Settings
from common.models.user import User

logger = logging.getLogger("services.auth_service")


class AuthService:
    """
    Service responsible for OTP generation, rate limiting, student email dispatch via Resend,
    and OTP verification with attempt tracking.
    """

    OTP_TTL_SECONDS = 300  # 5 minutes
    RATE_LIMIT_TTL_SECONDS = 60  # 1 minute
    MAX_VERIFY_ATTEMPTS = 3

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        settings_obj: Settings = settings,
    ) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings_obj
        self.resend_api_key = settings_obj.RESEND_API_KEY
        self.sender_email = settings_obj.SENDER_EMAIL

    async def send_student_otp(
        self,
        telegram_id: int,
        barcode: str,
        target_email: str | None = None,
    ) -> str:
        """
        Sends verification OTP to student email:
        1. Checks rate limit in Redis (rate:otp:{telegram_id}).
        2. Checks whether barcode is already registered by another user in DB.
        3. Generates 6-digit cryptographic OTP and caches in Redis (otp:{barcode}, TTL=300).
        4. Selects destination address:
           - During testing/development (ENVIRONMENT != "production"): sends to the Gmail
             address entered by the user during registration (target_email or user.email in DB).
           - In production (ENVIRONMENT == "production"): sends strictly to corporate
             email {barcode}@astanait.edu.kz.
        5. Sends HTML email via Resend SDK with sender aitu-gaming@y-not-devs.com.
        """
        rate_key = f"rate:otp:{telegram_id}"

        # 1. Check rate limit
        if await self.redis.exists(rate_key):
            ttl = await self.redis.ttl(rate_key)
            retry_after = str(max(ttl, 1))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please wait before requesting a new code.",
                headers={"Retry-After": retry_after},
            )

        # 2. Check if student_barcode is already taken by another active user in DB
        stmt = select(User).where(
            or_(User.barcode == barcode, User.student_barcode == barcode)
        )
        existing_user = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing_user and existing_user.telegram_id != telegram_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student barcode '{barcode}' is already linked to another active user.",
            )

        # Apply rate limiting key
        await self.redis.set(rate_key, "1", ex=self.RATE_LIMIT_TTL_SECONDS)

        # 3. Generate cryptographically secure 6-digit OTP code
        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        otp_key = f"otp:{barcode}"
        attempts_key = f"attempts:otp:{barcode}"

        await self.redis.set(otp_key, otp_code, ex=self.OTP_TTL_SECONDS)
        await self.redis.delete(attempts_key)

        # 4. Format destination address
        corporate_email = f"{barcode}@astanait.edu.kz"
        if self.settings.is_production:
            recipient = corporate_email
        else:
            if target_email and target_email.strip():
                recipient = target_email.strip()
            else:
                stmt_user = select(User).where(User.telegram_id == telegram_id)
                db_user = (await self.session.execute(stmt_user)).scalar_one_or_none()
                if db_user and db_user.email and db_user.email.strip():
                    recipient = db_user.email.strip()
                else:
                    recipient = corporate_email

        # 5. Dispatch HTML email via Resend SDK
        sender = (self.sender_email or "AITU Gaming Hub <aitu-gaming@y-not-devs.com>").strip()
        if "@" in sender and "<" not in sender:
            sender = f"AITU Gaming Hub <{sender}>"

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AITU Gaming Hub — Код подтверждения</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; padding: 40px 16px; text-align: center;">
  <div style="max-width: 460px; margin: 0 auto; background-color: #161e2e; border: 1px solid #283548; border-radius: 12px; padding: 32px 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <h1 style="color: #6366f1; font-size: 22px; margin-bottom: 6px;">AITU Gaming Hub</h1>
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 24px;">Верификация студенческого аккаунта</p>
    <div style="background-color: #1f293d; border: 2px dashed #6366f1; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
      <span style="font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #ffffff;">{otp_code}</span>
    </div>
    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0;">
      Код действителен в течение <strong>5 минут</strong>.<br>
      Никому не передавайте этот код. Если вы не отправляли запрос, просто проигнорируйте это письмо.
    </p>
  </div>
</body>
</html>"""

        if self.resend_api_key:
            try:
                resend.api_key = self.resend_api_key
                params = {
                    "from": sender,
                    "to": [recipient],
                    "subject": f"AITU Gaming Hub: Код верификации {otp_code}",
                    "html": html_body,
                }
                await resend.Emails.send_async(params)
                logger.info(f"Dispatched student OTP email to {recipient} from {sender}")
            except Exception as exc:
                logger.error(f"Resend SDK dispatch error to {recipient}: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to send email verification: {str(exc)}",
                )
        else:
            logger.warning(
                f"RESEND_API_KEY not configured. Mocking OTP dispatch of '{otp_code}' to '{recipient}'."
            )

        return recipient

    async def verify_student_otp(self, telegram_id: int, barcode: str, otp_code: str) -> bool:
        """
        Verifies student OTP against Redis:
        1. Checks attempt limit (attempts:otp:{barcode}).
        2. Compares provided code with cached code (otp:{barcode}).
        3. On success, deletes OTP and attempts keys and returns True.
        """
        otp_key = f"otp:{barcode}"
        attempts_key = f"attempts:otp:{barcode}"

        # 1. Check current attempts count
        raw_attempts = await self.redis.get(attempts_key)
        attempts_count = int(raw_attempts) if raw_attempts else 0

        if attempts_count >= self.MAX_VERIFY_ATTEMPTS:
            await self.redis.delete(otp_key)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Maximum OTP verification attempts exceeded. Code has been invalidated.",
            )

        # 2. Check if OTP is still active in Redis
        saved_otp = await self.redis.get(otp_key)
        if not saved_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP code expired or not found. Please request a new verification code.",
            )

        # 3. Compare OTP
        if otp_code != saved_otp:
            new_attempts = await self.redis.incr(attempts_key)
            if new_attempts == 1:
                ttl = await self.redis.ttl(otp_key)
                await self.redis.expire(attempts_key, max(ttl, 60))

            if new_attempts >= self.MAX_VERIFY_ATTEMPTS:
                await self.redis.delete(otp_key)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Maximum OTP verification attempts exceeded. Code has been invalidated.",
                )

            remaining = self.MAX_VERIFY_ATTEMPTS - new_attempts
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP code. {remaining} attempt(s) remaining.",
            )

        # 4. Success: clear temporary state
        await self.redis.delete(otp_key, attempts_key)
        logger.info(f"Successfully verified OTP for student barcode {barcode} (telegram_id={telegram_id})")
        return True
