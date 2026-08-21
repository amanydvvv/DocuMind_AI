"""
KueryCore AI — Email Service (Resend)
=====================================
Thin wrapper around the Resend REST API for transactional emails.

Provider choice: Resend (https://resend.com)
  - Simple POST-only REST API, no heavy SDK dependency tree
  - Generous free tier (3 000 emails/month, 100/day)
  - HTTP 200 + JSON { "id": "<message-id>" } on success
  - RESEND_API_KEY must be set as an env var; without it emails are logged
    to stdout in development (so local flows still work end-to-end without
    a real API key, and the reset-password endpoints behave identically).

To swap providers (SES, SendGrid, Postmark, SMTP) replace only _send_via_resend();
the public interface (send_password_reset_email) stays the same.

Required env vars:
  RESEND_API_KEY   — your Resend API key (from https://resend.com/api-keys)
  RESEND_FROM_EMAIL — optional, defaults to "KueryCore <noreply@kuerycore.ai>"
  FRONTEND_URL     — base URL of the deployed frontend
                     (e.g. https://docu-mind-ai-iota.vercel.app)
                     used to build the reset link
"""

import logging
import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal: Resend REST call
# ---------------------------------------------------------------------------

_RESEND_API_URL = "https://api.resend.com/emails"


async def _send_via_resend(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> bool:
    """
    Send a single transactional email via Resend.

    Returns True on success, False on failure.
    Logs errors but never raises — callers must NOT change their HTTP response
    based on email-delivery success/failure (avoids account-enumeration leaks).
    """
    api_key = settings.RESEND_API_KEY
    from_addr = getattr(settings, "RESEND_FROM_EMAIL", "KueryCore <noreply@kuerycore.ai>")

    if not api_key:
        # Development fallback: log the email body instead of sending.
        logger.warning(
            "[EMAIL DEV FALLBACK — no RESEND_API_KEY set]\n"
            "To: %s\nSubject: %s\n\n%s",
            to, subject, text,
        )
        return True  # Treat as success so the endpoint still returns 200

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_addr,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )

        if response.status_code in (200, 201):
            msg_id = response.json().get("id", "unknown")
            logger.info("Password reset email sent via Resend to %s (id=%s)", to, msg_id)
            return True

        logger.error(
            "Resend API returned %s for email to %s: %s",
            response.status_code, to, response.text[:200],
        )
        return False

    except Exception as exc:
        logger.error("Failed to send email via Resend to %s: %s", to, exc)
        return False


# ---------------------------------------------------------------------------
# Public: password-reset email
# ---------------------------------------------------------------------------

async def send_password_reset_email(*, to: str, raw_token: str) -> None:
    """
    Send a password-reset email containing a one-time link.

    The link is:  {FRONTEND_URL}/reset-password?token={raw_token}

    Never raises. Returns None regardless of delivery outcome so callers
    cannot distinguish success/failure (prevents timing/enumeration attacks).
    """
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"

    subject = "Reset your KueryCore password"

    html_body = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#050d08;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e2e8f0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;margin:40px auto;background:linear-gradient(180deg,rgba(13,29,21,0.95) 0%,rgba(9,20,16,0.98) 100%);border:1px solid rgba(0,255,170,0.18);border-radius:16px;overflow:hidden;">
    <tr>
      <td style="padding:40px 36px;">
        <!-- Brand heading -->
        <h1 style="margin:0 0 4px;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">KueryCore</h1>
        <p style="margin:0 0 28px;font-size:12px;color:#4ade80;font-family:monospace;letter-spacing:1px;">AI Document Intelligence</p>

        <!-- Body -->
        <p style="font-size:15px;line-height:1.6;margin:0 0 16px;color:#cbd5e1;">
          We received a request to reset the password for your account.
          Click the button below to choose a new password.
        </p>
        <p style="font-size:13px;color:#94a3b8;margin:0 0 28px;">
          This link expires in <strong style="color:#e2e8f0;">30 minutes</strong>.
          If you didn't request this, you can safely ignore this email — your password will not change.
        </p>

        <!-- CTA button -->
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td align="center">
              <a href="{reset_url}"
                 style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#00d68f 0%,#00ffaa 100%);color:#020804;font-weight:700;font-size:14px;text-decoration:none;border-radius:10px;letter-spacing:0.5px;box-shadow:0 0 30px rgba(0,214,143,0.45);">
                Reset Password →
              </a>
            </td>
          </tr>
        </table>

        <!-- Fallback link -->
        <p style="margin:24px 0 0;font-size:11px;color:#64748b;word-break:break-all;">
          Or copy this link into your browser:<br>
          <a href="{reset_url}" style="color:#4ade80;">{reset_url}</a>
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding:16px 36px;border-top:1px solid rgba(255,255,255,0.07);font-size:11px;color:#475569;">
        KueryCore AI · This is an automated security email · Do not reply
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_body = (
        f"Reset your KueryCore password\n\n"
        f"We received a request to reset the password associated with your account.\n\n"
        f"Click the link below to choose a new password (expires in 30 minutes):\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, please ignore this email. Your password will not change.\n\n"
        f"— KueryCore AI"
    )

    await _send_via_resend(to=to, subject=subject, html=html_body, text=text_body)
