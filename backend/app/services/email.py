"""
KueryCore AI — Email Service (Brevo HTTPS API, SMTP & Resend)
=============================================================
Multi-provider transactional email service with detailed diagnostic reporting.
"""

import asyncio
import email.utils
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Tuple

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Brevo HTTPS REST API (Port 443 — Cloud-Friendly)
# ---------------------------------------------------------------------------

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def _send_via_brevo_api(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> Tuple[bool, Dict[str, Any]]:
    """Send transactional email via Brevo's HTTPS v3 REST API."""
    raw_api_key = getattr(settings, "BREVO_API_KEY", None) or settings.SMTP_PASSWORD
    api_key = raw_api_key.strip() if raw_api_key else None

    from_name = getattr(settings, "SMTP_FROM_NAME", None) or "KueryCore AI"
    from_email = getattr(settings, "SMTP_FROM_EMAIL", None) or settings.SMTP_USERNAME or "noreply@kuerycore.ai"

    _, parsed_addr = email.utils.parseaddr(from_email)
    sender_addr = (parsed_addr if parsed_addr else from_email).strip()

    if not api_key or not sender_addr:
        return False, {"error": "Missing BREVO_API_KEY or sender address", "sender": sender_addr}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                _BREVO_API_URL,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "sender": {"name": from_name, "email": sender_addr},
                    "to": [{"email": to.strip()}],
                    "subject": subject,
                    "htmlContent": html,
                    "textContent": text,
                },
            )

        if response.status_code in (200, 201, 202):
            data = response.json()
            msg_id = data.get("messageId", "unknown")
            logger.info("Password reset email sent via Brevo HTTPS API to %s (messageId=%s)", to, msg_id)
            return True, {"provider": "brevo_https", "status": response.status_code, "data": data}

        logger.error(
            "Brevo HTTPS API returned status %s for email to %s: %s (sender=%s)",
            response.status_code, to, response.text[:300], sender_addr,
        )
        return False, {
            "provider": "brevo_https",
            "status": response.status_code,
            "response": response.text[:300],
            "sender_used": sender_addr,
        }

    except Exception as exc:
        logger.error("Failed to send email via Brevo HTTPS API to %s: %s", to, exc)
        return False, {"provider": "brevo_https", "error": str(exc), "type": type(exc).__name__}


# ---------------------------------------------------------------------------
# 2. Gmail / Generic SMTP Relay
# ---------------------------------------------------------------------------

def _send_smtp_sync(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> Tuple[bool, Dict[str, Any]]:
    """Synchronous SMTP worker executed inside an async worker thread."""
    username = settings.SMTP_USERNAME.strip() if settings.SMTP_USERNAME else None
    password = settings.SMTP_PASSWORD.strip() if settings.SMTP_PASSWORD else None
    server_host = settings.SMTP_SERVER.strip() if settings.SMTP_SERVER else "smtp.gmail.com"
    server_port = int(settings.SMTP_PORT or 587)

    raw_from = getattr(settings, "SMTP_FROM_EMAIL", None) or username or "noreply@kuerycore.ai"
    parsed_name, parsed_addr = email.utils.parseaddr(raw_from)
    sender_addr = (parsed_addr if parsed_addr else raw_from).strip()
    sender_name = parsed_name or getattr(settings, "SMTP_FROM_NAME", None) or "KueryCore AI"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email.utils.formataddr((sender_name, sender_addr))
    msg["To"] = to

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    server = None
    try:
        if server_port == 465:
            server = smtplib.SMTP_SSL(server_host, server_port, timeout=12.0)
        else:
            server = smtplib.SMTP(server_host, server_port, timeout=12.0)
            server.ehlo()
            server.starttls()
            server.ehlo()

        if username and password:
            server.login(username, password)

        server.sendmail(sender_addr, [to], msg.as_string())
        logger.info("Password reset email successfully sent via SMTP (%s) to %s", server_host, to)
        return True, {"provider": "smtp", "host": server_host, "port": server_port, "sender": sender_addr}
    except Exception as exc:
        logger.error("Failed to send email via SMTP (%s) to %s: %s (type: %s)", server_host, to, exc, type(exc).__name__)
        return False, {"provider": "smtp", "host": server_host, "port": server_port, "error": str(exc), "type": type(exc).__name__}
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


async def _send_via_smtp(*, to: str, subject: str, html: str, text: str) -> Tuple[bool, Dict[str, Any]]:
    """Non-blocking async wrapper around SMTP."""
    return await asyncio.to_thread(_send_smtp_sync, to=to, subject=subject, html=html, text=text)


# ---------------------------------------------------------------------------
# 3. Resend REST API
# ---------------------------------------------------------------------------

_RESEND_API_URL = "https://api.resend.com/emails"


async def _send_via_resend(*, to: str, subject: str, html: str, text: str) -> Tuple[bool, Dict[str, Any]]:
    raw_api_key = settings.RESEND_API_KEY
    api_key = raw_api_key.strip() if raw_api_key else None
    from_addr = getattr(settings, "RESEND_FROM_EMAIL", "KueryCore <noreply@kuerycore.ai>").strip()

    if not api_key:
        return False, {"error": "Missing RESEND_API_KEY"}

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
                    "to": [to.strip()],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )

        if response.status_code in (200, 201):
            data = response.json()
            msg_id = data.get("id", "unknown")
            logger.info("Password reset email sent via Resend to %s (id=%s)", to, msg_id)
            return True, {"provider": "resend", "status": response.status_code, "data": data}

        logger.error("Resend API returned %s for email to %s: %s", response.status_code, to, response.text[:200])
        return False, {"provider": "resend", "status": response.status_code, "response": response.text[:200]}

    except Exception as exc:
        logger.error("Failed to send email via Resend to %s: %s", to, exc)
        return False, {"provider": "resend", "error": str(exc), "type": type(exc).__name__}


# ---------------------------------------------------------------------------
# Public: Password-Reset Email
# ---------------------------------------------------------------------------

async def send_password_reset_email(*, to: str, raw_token: str) -> Dict[str, Any]:
    """
    Send a password-reset email containing a one-time link.
    Returns diagnostic dict indicating provider used and outcome.
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
        <h1 style="margin:0 0 4px;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">KueryCore</h1>
        <p style="margin:0 0 28px;font-size:12px;color:#4ade80;font-family:monospace;letter-spacing:1px;">AI Document Intelligence</p>
        <p style="font-size:15px;line-height:1.6;margin:0 0 16px;color:#cbd5e1;">
          We received a request to reset the password for your account.
          Click the button below to choose a new password.
        </p>
        <p style="font-size:13px;color:#94a3b8;margin:0 0 28px;">
          This link expires in <strong style="color:#e2e8f0;">30 minutes</strong>.
          If you didn't request this, you can safely ignore this email — your password will not change.
        </p>
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

    diagnostics = {}

    # 1. Brevo HTTPS REST API
    is_brevo = getattr(settings, "BREVO_API_KEY", None) or (
        settings.SMTP_SERVER and "brevo" in settings.SMTP_SERVER.lower() and settings.SMTP_PASSWORD
    )
    if is_brevo:
        sent, info = await _send_via_brevo_api(to=to, subject=subject, html=html_body, text=text_body)
        if sent:
            return {"success": True, "provider": "brevo_https", "details": info}
        diagnostics["brevo_https"] = info

        # Fallback to SMTP
        sent_smtp, info_smtp = await _send_via_smtp(to=to, subject=subject, html=html_body, text=text_body)
        if sent_smtp:
            return {"success": True, "provider": "brevo_smtp", "details": info_smtp}
        diagnostics["brevo_smtp"] = info_smtp

    # 2. Generic / Gmail SMTP Relay
    elif settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        sent_smtp, info_smtp = await _send_via_smtp(to=to, subject=subject, html=html_body, text=text_body)
        if sent_smtp:
            return {"success": True, "provider": "smtp", "details": info_smtp}
        diagnostics["smtp"] = info_smtp

    # 3. Resend REST API
    elif settings.RESEND_API_KEY:
        sent_resend, info_resend = await _send_via_resend(to=to, subject=subject, html=html_body, text=text_body)
        if sent_resend:
            return {"success": True, "provider": "resend", "details": info_resend}
        diagnostics["resend"] = info_resend

    # 4. Dev Fallback
    else:
        logger.warning(
            "[EMAIL DEV FALLBACK — no email provider credentials configured]\n"
            "To: %s\nSubject: %s\nReset URL: %s",
            to, subject, reset_url,
        )
        return {"success": True, "provider": "dev_fallback", "reset_url": reset_url}

    return {"success": False, "error": "All email providers failed", "diagnostics": diagnostics}
