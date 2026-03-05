import os
import smtplib
from email.message import EmailMessage

SMTP_SERVER     = os.getenv("SMTP_SERVER", "")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME   = os.getenv("SMTP_USERNAME") or os.getenv("EMAIL_ACCOUNT", "")
SMTP_PASSWORD   = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD", "")
FROM_ADDRESS    = os.getenv("FROM_ADDRESS") or os.getenv("EMAIL_ACCOUNT", "")
CONFIRM_SUBJECT = os.getenv("CONFIRM_SUBJECT", "Your Print Job Confirmation")


def _send(to_email: str, subject: str, body: str, logger):
    """Low-level send helper."""
    if not SMTP_SERVER:
        logger.warning("SMTP_SERVER not set — skipping email.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = FROM_ADDRESS
    msg["To"]      = to_email

    if body.lstrip().startswith("<"):
        msg.set_content("Please view this email in an HTML-capable client.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email} | subject: {subject}")
    except Exception as exc:
        logger.error(f"Failed to send email to {to_email}: {exc}")


def send_confirmation(
    to_email: str,
    body: str,
    filename: str,
    logger,
    subject_override: str = "",
):
    """Send a confirmation (or error notice) to the original sender."""
    subject = subject_override or f"{CONFIRM_SUBJECT}: {filename}"
    _send(to_email, subject, body, logger)


def send_admin_alert(
    admin_email: str,
    sender: str,
    filename: str,
    job_id: str,
    error_detail: str,
    logger,
):
    """Send a detailed error report to the configured admin address."""
    body = (
        f"email2Print — Print Job Error Report\n"
        f"{'=' * 44}\n"
        f"Job ID   : {job_id}\n"
        f"Sender   : {sender}\n"
        f"File     : {filename}\n"
        f"Error    : {error_detail}\n\n"
        f"Hint: Verify that the PRINTER_NAME env var matches the exact CUPS queue\n"
        f"name. Run 'lpstat -p' inside the container to list all available queues.\n"
    )
    _send(admin_email, f"[email2Print] Print Error — Job {job_id}", body, logger)
