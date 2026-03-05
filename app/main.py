import imapclient
import email
import os
import logging
import time
import json
import uuid
from datetime import datetime
from email.header import decode_header

from app.printer import print_attachment
from app.mailer import send_confirmation, send_admin_alert
from app.templates_engine import render_template

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("/app/logs", exist_ok=True)
os.makedirs("/app/data", exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("email2print")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("/app/logs/email2print.log")
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# ── Config ────────────────────────────────────────────────────────────────────
def _env(name, required=False, default=None):
    val = os.getenv(name)
    if not val:
        if required:
            raise ValueError(f"Missing required env var: {name}")
        return default
    return val

IMAP_SERVER              = _env("IMAP_SERVER", required=True)
IMAP_PORT                = int(_env("IMAP_PORT", default=993))
EMAIL_ACCOUNT            = _env("EMAIL_ACCOUNT", required=True)
EMAIL_PASSWORD           = _env("EMAIL_PASSWORD", required=True)
PRINTER_NAME             = _env("PRINTER_NAME", required=True)
SLEEP_TIME               = int(_env("SLEEP_TIME", default=60))
ALLOWED_TYPES_RAW        = _env("ALLOWED_ATTACHMENT_TYPES", default="pdf,png,jpg,jpeg,docx")
ALLOWED_ATTACHMENT_TYPES = [x.strip().lower() for x in ALLOWED_TYPES_RAW.split(",") if x.strip()]
ALLOWED_RECIPIENTS       = [x.strip().lower() for x in (_env("ALLOWED_RECIPIENTS", default="") or "").split(",") if x.strip()]
CONFIRM_TEMPLATE         = _env("CONFIRM_TEMPLATE", default="default.html")
# Admin email receives detailed error reports; optional
ADMIN_EMAIL              = _env("ADMIN_EMAIL", default="")

JOBS_FILE = "/app/data/jobs.json"

# ── Job persistence ───────────────────────────────────────────────────────────
def load_jobs():
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_job(job: dict):
    jobs = load_jobs()
    jobs.append(job)
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

# ── MIME helpers ──────────────────────────────────────────────────────────────
def decode_mime_words(s):
    if not s:
        return ""
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in decode_header(s)
    )

# ── Email processing ──────────────────────────────────────────────────────────
def process_email(msg):
    from_addr = email.utils.parseaddr(msg.get("From"))[1].lower()
    subject   = decode_mime_words(msg.get("Subject", "(No Subject)"))

    logger.info(f"Processing email | from={from_addr} | subject={subject}")

    if ALLOWED_RECIPIENTS and from_addr not in ALLOWED_RECIPIENTS:
        logger.warning(f"Sender {from_addr} not in ALLOWED_RECIPIENTS — skipping.")
        return

    attachments_found = False
    active_template = CONFIRM_TEMPLATE

    # Runtime override set by the WebUI
    override_file = "/app/data/active_template.txt"
    if os.path.exists(override_file):
        with open(override_file) as f:
            override = f.read().strip()
            if override:
                active_template = override

    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue  # Attachment-only mode: skip all body parts

        attachments_found = True
        filename = decode_mime_words(filename)
        suffix   = os.path.splitext(filename)[1].lower().lstrip(".")
        payload  = part.get_payload(decode=True)

        if not payload:
            logger.warning(f"Attachment '{filename}' has no payload — skipping.")
            continue

        if ALLOWED_ATTACHMENT_TYPES and suffix not in ALLOWED_ATTACHMENT_TYPES:
            logger.warning(f"Attachment '{filename}' type .{suffix} not allowed — skipping.")
            continue

        job_id    = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        success, error_detail = print_attachment(payload, filename, suffix, PRINTER_NAME, logger)
        status = "success" if success else "failed"

        job = {
            "id":            job_id,
            "timestamp":     timestamp,
            "sender":        from_addr,
            "filename":      filename,
            "printer":       PRINTER_NAME,
            "status":        status,
            "template_used": active_template,
            "error":         error_detail or "",
        }
        save_job(job)
        logger.info(f"Job {job_id} | {filename} | {status}")

        if success:
            # Send the normal styled confirmation to the original sender
            body = render_template(active_template, {
                "sender":    from_addr,
                "filename":  filename,
                "printer":   PRINTER_NAME,
                "timestamp": timestamp,
                "job_id":    job_id,
                "status":    status,
            })
            send_confirmation(from_addr, body, filename, logger)
        else:
            # Send a simple error notice to the original sender
            send_confirmation(
                from_addr,
                _error_body_for_sender(filename),
                filename,
                logger,
                subject_override="Print Job Failed",
            )
            # Optionally send a detailed alert to the admin
            if ADMIN_EMAIL:
                send_admin_alert(
                    ADMIN_EMAIL,
                    from_addr,
                    filename,
                    job_id,
                    error_detail or "Unknown error",
                    logger,
                )

    if not attachments_found:
        logger.info(f"Email from {from_addr} has no attachments — nothing to print.")


def _error_body_for_sender(filename: str) -> str:
    """Plain, non-technical error notice sent to the original sender."""
    return (
        f"Hello,\n\n"
        f"Unfortunately an error occurred while processing your print job "
        f"for the file '{filename}'.\n\n"
        f"Please check that you sent the correct file type and try again. "
        f"If the problem persists, contact your administrator.\n\n"
        f"— email2Print"
    )


# ── Main loop ─────────────────────────────────────────────────────────────────
def main_loop():
    while True:
        logger.info("email2print: checking inbox...")
        try:
            with imapclient.IMAPClient(IMAP_SERVER, ssl=True, port=IMAP_PORT) as client:
                client.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
                client.select_folder("INBOX")
                messages = client.search(["UNSEEN"])
                logger.info(f"Found {len(messages)} unseen message(s)")
                for uid, msg_data in client.fetch(messages, "RFC822").items():
                    msg = email.message_from_bytes(msg_data[b"RFC822"])
                    process_email(msg)
                    client.add_flags(uid, [b"\\Seen"])
        except Exception as exc:
            logger.error(f"IMAP error: {exc}")

        logger.info(f"Sleeping {SLEEP_TIME}s...")
        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main_loop()
