import os
import tempfile
import subprocess
from typing import Tuple

# Build the CUPS server string once at import time.
# The env var CUPS_SERVER_ADDRESS is set by the entrypoint script
# (which appends /version=1.1 to whatever CUPS_SERVER contains).
# Fallback: use CUPS_SERVER directly if the entrypoint was not used.
_CUPS_SERVER = os.getenv("CUPS_SERVER_ADDRESS") or os.getenv("CUPS_SERVER", "")


def _build_lp_cmd(printer_name: str, file_path: str) -> list:
    """Build the lp command, injecting -h <server>/version=1.1 when a
    CUPS server address is configured. This avoids the
    'add /version=1.1 to server name' error thrown by newer CUPS servers
    when the client does not negotiate the IPP version explicitly."""
    cmd = ["lp"]
    if _CUPS_SERVER:
        # Ensure the /version=1.1 suffix is present exactly once
        server = _CUPS_SERVER.rstrip("/")
        if "/version=" not in server:
            server = f"{server}/version=1.1"
        cmd += ["-h", server]
    cmd += ["-d", printer_name, file_path]
    return cmd


def print_attachment(
    payload: bytes, filename: str, suffix: str, printer_name: str, logger
) -> Tuple[bool, str]:
    """
    Write payload to a temp file and send it to the CUPS printer.

    Returns (success: bool, error_detail: str).

    Troubleshooting:
      - Run 'docker exec email2print lpstat -h host.docker.internal/version=1.1 -p'
        to list available queues from inside the container.
      - PRINTER_NAME must match the queue name exactly (case-sensitive).
      - CUPS_SERVER must point to the host running cupsd (e.g. host.docker.internal).
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            tmp.write(payload)
            tmp_path = tmp.name

        cmd = _build_lp_cmd(printer_name, tmp_path)
        logger.info(f"Print command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "lp returned non-zero").strip()
            logger.error(f"Printing failed for '{filename}': {detail}")
            return False, detail

        logger.info(f"Sent to printer '{printer_name}': {filename}")
        return True, ""

    except Exception as exc:
        logger.error(f"Unexpected printing error for '{filename}': {exc}")
        return False, str(exc)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
