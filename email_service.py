"""
Transactional email via Resend (https://resend.com).

Set in the environment (never commit real values):
    RESEND_API_KEY   your `re_...` key
    RESEND_FROM      e.g. "Akagera Inc <noreply@akagerainc.store>"
                     (the domain must be verified in Resend; until then use
                     "onboarding@resend.dev", which only delivers to the
                     Resend account owner's address)
"""
import os
import requests

RESEND_API_URL = "https://api.resend.com/emails"


def _cfg():
    return {
        "key": os.getenv("RESEND_API_KEY", "").strip(),
        "from": os.getenv("RESEND_FROM", "Akagera Inc <onboarding@resend.dev>").strip(),
    }


def is_configured() -> bool:
    return bool(_cfg()["key"])


def send_email(to: str, subject: str, html: str, text: str | None = None) -> tuple[bool, str]:
    cfg = _cfg()
    if not cfg["key"]:
        print(f"[email] RESEND_API_KEY not set — would send to {to}: {subject}")
        return False, "email not configured"
    payload = {"from": cfg["from"], "to": [to], "subject": subject, "html": html}
    if text:
        payload["text"] = text
    try:
        r = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True, r.json().get("id", "sent")
        return False, f"resend {r.status_code}: {r.text[:200]}"
    except requests.RequestException as exc:
        return False, str(exc)


# --------------------------------------------------------------------------
_OTP_COPY = {
    "login": ("Your Akagera Inc sign-in code", "sign in to your Akagera Inc account"),
    "verify": ("Verify your Akagera Inc email", "verify your email address"),
    "reset": ("Reset your Akagera Inc password", "reset your password"),
}


def send_otp(to: str, code: str, purpose: str = "login", ttl_minutes: int = 10) -> tuple[bool, str]:
    subject, action = _OTP_COPY.get(purpose, _OTP_COPY["login"])
    html = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <div style="font-size:20px;font-weight:800;color:#141414">Akagera<span style="color:#BD4A39">Inc</span></div>
  <p style="color:#3a3a3a;font-size:15px;margin-top:20px">
    Use this code to {action}. It expires in {ttl_minutes} minutes.
  </p>
  <div style="font-size:34px;font-weight:800;letter-spacing:10px;color:#BD4A39;
              background:#F7E8E5;border-radius:10px;text-align:center;padding:18px 0;margin:18px 0">
    {code}
  </div>
  <p style="color:#7a7a7a;font-size:13px">
    If you didn't request this, you can safely ignore this email.
  </p>
  <p style="color:#a8a8a8;font-size:12px;margin-top:24px">© Akagera Inc</p>
</div>"""
    text = f"Your Akagera Inc code is {code}. It expires in {ttl_minutes} minutes."
    return send_email(to, subject, html, text)
