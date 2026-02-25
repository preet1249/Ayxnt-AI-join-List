import os
import json
import base64
import traceback
import requests
import gspread
import sib_api_v3_sdk
from datetime import datetime
from sib_api_v3_sdk.rest import ApiException

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load .env first, fall back to .env.example (used during local dev)
load_dotenv() or load_dotenv(".env.example")

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL     = "arcee-ai/trinity-large-preview:free"

BREVO_API_KEY        = os.getenv("BREVO_API_KEY")        # Brevo API key (v3)
SENDER_EMAIL         = os.getenv("SENDER_EMAIL")          # Verified sender email
SENDER_NAME          = os.getenv("SENDER_NAME", "Ayxnt")

GOOGLE_SHEET_ID      = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDS_FILE    = os.getenv("GOOGLE_CREDS_FILE", "credentials.json")

APP_NAME             = os.getenv("APP_NAME", "Ayxnt")
APP_SITE_URL         = os.getenv("APP_SITE_URL", "https://ayxnt.com")
UNSUBSCRIBE_URL      = os.getenv("UNSUBSCRIBE_URL", "https://ayxnt.com/unsubscribe")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title=f"{APP_NAME} Waitlist API")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173"   # default for local dev
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schema ─────────────────────────────────────────────────────────────
class SubscribeRequest(BaseModel):
    email: EmailStr


# ── Google Sheets helpers ──────────────────────────────────────────────────────
SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _get_sheet():
    """Return the first worksheet of the configured Google Sheet."""
    creds_json_b64 = os.getenv("GOOGLE_CREDS_JSON")
    if creds_json_b64:
        # On Render: credentials stored as a base64-encoded env var
        creds_data = json.loads(base64.b64decode(creds_json_b64).decode())
        creds = Credentials.from_service_account_info(creds_data, scopes=SHEET_SCOPES)
    else:
        # Local: read from credentials.json file
        creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=SHEET_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def _ensure_header(sheet):
    """Make sure the header row exists."""
    first_row = sheet.row_values(1)
    if not first_row or first_row[0] != "Email":
        sheet.insert_row(["Email", "Timestamp (UTC)", "Sent"], index=1)


def save_email_to_sheet(email: str) -> int:
    """
    Append a new row with the subscriber email.
    Returns the 1-based row index of the newly added row.
    """
    sheet = _get_sheet()
    _ensure_header(sheet)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([email, timestamp, ""])
    return len(sheet.get_all_values())


def mark_row_sent(row_index: int):
    """Put a tick (✓) in the Sent column for the given row."""
    sheet = _get_sheet()
    sheet.update_cell(row_index, 3, "✓")


# ── OpenRouter LLM helper ──────────────────────────────────────────────────────
def generate_email_content(recipient_email: str) -> dict:
    """
    Ask the LLM to produce the welcome email content.
    Returns a dict with keys: subject, heading, body, unsubscribe_note.
    """
    prompt = f"""Write a concise, warm welcome email for someone who just joined the "{APP_NAME}" waitlist.

Rules:
- subject: one short subject line
- heading: short H2-style heading (plain text)
- body: exactly 2-3 sentences, friendly and professional
- End the body with: "Please do not reply to this email."
- unsubscribe_note: short sentence pointing to {UNSUBSCRIBE_URL}

Return ONLY valid JSON — no markdown, no code fences, no extra keys:
{{
  "subject": "...",
  "heading": "...",
  "body": "...",
  "unsubscribe_note": "..."
}}"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": APP_SITE_URL,
            "X-Title": APP_NAME,
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
        },
        timeout=40,
    )
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if the LLM adds them
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


# ── Brevo API helper ───────────────────────────────────────────────────────────
def send_welcome_email(recipient_email: str, content: dict):
    """Send the HTML welcome email via Brevo Transactional Email API."""
    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;padding:40px;max-width:600px;">
        <tr>
          <td>
            <h2 style="font-size:22px;font-weight:600;color:#111;margin:0 0 16px 0;">
              {content['heading']}
            </h2>
            <p style="font-size:15px;line-height:1.7;color:#444;margin:0 0 28px 0;">
              {content['body']}
            </p>
            <hr style="border:none;border-top:1px solid #eee;margin:0 0 20px 0;">
            <p style="font-size:12px;color:#999;margin:0 0 8px 0;">
              {content['unsubscribe_note']}
            </p>
            <p style="font-size:12px;color:#bbb;margin:0;">
              &copy; {datetime.utcnow().year} {APP_NAME}. All rights reserved.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": recipient_email}],
        sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
        subject=content["subject"],
        html_content=html,
    )

    api_instance.send_transac_email(send_smtp_email)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/subscribe")
def subscribe(req: SubscribeRequest):
    email = req.email

    # 1. Save to Google Sheet
    try:
        row_index = save_email_to_sheet(email)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sheet error: {exc}")

    # 2. Generate email content via OpenRouter LLM
    try:
        content = generate_email_content(email)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")

    # 3. Send welcome email via Brevo API
    try:
        send_welcome_email(email, content)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Email send error: {exc}")

    # 4. Mark row as sent (✓)
    try:
        mark_row_sent(row_index)
    except Exception as exc:
        print(f"[WARN] Could not mark row {row_index} as sent: {exc}")

    return {"status": "success", "message": "Subscribed successfully!"}
