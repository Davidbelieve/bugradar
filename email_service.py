"""
email_service.py — Welcome email via Resend for BugOracle.
"""

import os
import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_URL     = "https://api.resend.com/emails"
FROM_EMAIL     = "BugOracle <onboarding@resend.dev>"


def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Sends a welcome email to a new Pro subscriber.
    Returns True on success, False on failure.
    """
    if not RESEND_API_KEY:
        print("[email] RESEND_API_KEY not set — skipping welcome email")
        return False

    if not to_email:
        print(f"[email] No email address for {username} — skipping")
        return False

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ margin: 0; padding: 0; background: #08080a; font-family: 'DM Sans', -apple-system, sans-serif; }}
  .wrap {{ max-width: 580px; margin: 0 auto; padding: 48px 24px; }}
  .logo {{ font-family: monospace; font-size: 18px; font-weight: 700; color: #c8ff00; margin-bottom: 32px; }}
  .logo b {{ color: #eeeef0; }}
  .card {{ background: #0f0f12; border: 1px solid #1c1c22; border-radius: 12px; padding: 40px; }}
  h1 {{ font-size: 24px; color: #eeeef0; margin: 0 0 12px; font-weight: 600; line-height: 1.3; }}
  p {{ font-size: 15px; color: #9898a8; line-height: 1.7; margin: 0 0 16px; }}
  .highlight {{ color: #eeeef0; }}
  .badge {{ display: inline-block; background: #c8ff00; color: #08080a; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; font-family: monospace; margin-bottom: 24px; }}
  .btn {{ display: inline-block; background: #c8ff00; color: #08080a; font-weight: 700; font-size: 14px; padding: 12px 28px; border-radius: 8px; text-decoration: none; margin: 8px 0 24px; }}
  .divider {{ height: 1px; background: #1c1c22; margin: 24px 0; }}
  .feat {{ display: flex; gap: 12px; margin-bottom: 14px; align-items: flex-start; }}
  .feat-icon {{ font-size: 16px; margin-top: 2px; flex-shrink: 0; }}
  .feat-text {{ font-size: 14px; color: #9898a8; line-height: 1.5; }}
  .feat-text strong {{ color: #eeeef0; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #55556a; text-align: center; font-family: monospace; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">Bug<b>Oracle</b></div>
  <div class="card">
    <div class="badge">PRO</div>
    <h1>You're in, {username}. 🎉</h1>
    <p>Your BugOracle Pro subscription is active. Every repo you register now gets <span class="highlight">unlimited scans</span> and <span class="highlight">automatic merge blocking</span> on every pull request.</p>

    <a href="https://bugradar.onrender.com/auth/github" class="btn">Open your dashboard →</a>

    <div class="divider"></div>

    <div class="feat">
      <div class="feat-icon">♾️</div>
      <div class="feat-text"><strong>Unlimited repos</strong> — register as many as you need, no caps.</div>
    </div>
    <div class="feat">
      <div class="feat-icon">⚡</div>
      <div class="feat-text"><strong>Unlimited scans</strong> — every PR, every push, no monthly limits.</div>
    </div>
    <div class="feat">
      <div class="feat-icon">🛡️</div>
      <div class="feat-text"><strong>Merge blocking</strong> — high-risk functions automatically block merges until fixed.</div>
    </div>
    <div class="feat">
      <div class="feat-icon">📊</div>
      <div class="feat-text"><strong>Full scan history</strong> — risk trends, high-risk function frequency, all in your dashboard.</div>
    </div>

    <div class="divider"></div>

    <p style="margin:0;font-size:13px;">Questions? Reply to this email — it goes straight to the founder. We read everything.</p>
  </div>
  <div class="footer">BugOracle &middot; Powered by NASA KC1 &amp; PC1 datasets &middot; &copy; 2026</div>
</div>
</body>
</html>
"""

    text = f"""
Welcome to BugOracle Pro, {username}!

Your subscription is active. Here's what you now have:

- Unlimited repos
- Unlimited scans
- Automatic merge blocking on high-risk PRs
- Full scan history dashboard

Open your dashboard: https://bugradar.onrender.com/auth/github

Questions? Just reply to this email.

— The BugOracle team
"""

    try:
        response = requests.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [to_email],
                "subject": "You're now on BugOracle Pro ⚡",
                "html": html,
                "text": text,
            },
            timeout=10,
        )
        if response.status_code == 200:
            print(f"[email] Welcome email sent to {to_email}")
            return True
        else:
            print(f"[email] Failed to send: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"[email] Exception sending email: {e}")
        return False
