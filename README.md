# email2Print

Send an email with an attachment → it gets printed automatically. That's it.

email2Print monitors an IMAP mailbox, prints every **file attachment** it finds, and sends a confirmation email back to the sender. An optional web dashboard lets you manage everything through a browser.

---

## Features

- 📧 Monitors an IMAP inbox and prints new attachments automatically
- 🖨️ Prints **attachments only** — the email body is never sent to the printer
- ✅ Sends a styled **confirmation email** to the sender after each job
- ❌ On failure, the sender gets a simple error notice; the admin gets a detailed report
- 📊 Every print job is logged to `data/jobs.json`
- 🌐 Optional **Admin WebUI** on port `635`:
  - Dashboard with live statistics
  - Full job history with filtering
  - Template manager (switch templates without restarting)
  - Real-time log viewer
  - Settings & printer status page
- 🌙 Dark / Light mode
- 🐳 Runs as a single Docker container alongside CUPS

---

## Requirements

- Docker & Docker Compose
- A running **CUPS** server (the included `docker-compose.yml` sets one up for you)
- A dedicated email address for the print service (e.g. a Gmail account with an App Password)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/TillitschScHocK/email2Print.git
cd email2Print
```

### 2. Prepare the CUPS config directory

The CUPS container needs its config files to already exist on the host before it starts.
Run this **once** to generate the default config:

```bash
mkdir -p /your/path/cups-config

# Start a temporary CUPS container without any volume mounts
docker run -d --name cups-init \
  --privileged --network host \
  drpsychick/airprint-bridge:latest

sleep 5

# Copy the generated config files to your host directory
docker cp cups-init:/etc/cups/. /your/path/cups-config/

# Remove the temporary container
docker rm -f cups-init
```

Then set the correct permissions:

```bash
chmod 644 /your/path/cups-config/*.conf
chmod 755 /your/path/cups-config
chown -R root:root /your/path/cups-config
```

### 3. Configure `docker-compose.yml`

Edit `docker-compose.yml` and replace the placeholder values:

| Placeholder | Replace with |
|---|---|
| `/your/path/cups-config` | Absolute path to your CUPS config directory |
| `/your/path/avahi` | Absolute path to your Avahi services directory |
| `Your-Printer-Queue-Name` | Your CUPS printer queue name (see step 5) |
| `imap.example.com` | Your IMAP server |
| `print@example.com` | Your mailbox address |
| `smtp.example.com` | Your SMTP server |

### 4. Start the stack

```bash
docker-compose up -d --build
```

### 5. Find your printer queue name

```bash
docker exec email2print lpstat -p
```

Example output:
```
printer Epson-ET2820-USB is idle.  enabled since ...
```

Copy the name (`Epson-ET2820-USB`) and set it as `PRINTER_NAME` in `docker-compose.yml`, then restart:

```bash
docker-compose up -d
```

### 6. Open the Admin WebUI

```
http://<your-server-ip>:635
```

---

## How CUPS networking works

Both containers use `network_mode: host`. This means they share the host's network stack and `lp`/`lpstat` inside the email2print container connect directly to `localhost:631` where CUPS is listening. This avoids IPP version negotiation errors that occur with bridge networking.

> **Troubleshooting `lpstat: Error - add '/version=1.1' to server name`**
> This error means the container is using bridge networking instead of host networking.
> Make sure both services have `network_mode: host` in `docker-compose.yml`.

> **Troubleshooting `lp: Error - The printer or class does not exist.`**
> The `PRINTER_NAME` value does not match the CUPS queue name.
> Run `docker exec email2print lpstat -p` to see the exact name.

> **Troubleshooting `sed: can't read /etc/cups/cups-files.conf`**
> The CUPS config directory is empty or has wrong permissions.
> Follow step 2 above to initialise it correctly.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `IMAP_SERVER` | ✅ | — | IMAP server hostname |
| `IMAP_PORT` | | `993` | IMAP SSL port |
| `EMAIL_ACCOUNT` | ✅ | — | Email address to monitor |
| `EMAIL_PASSWORD` | ✅ | — | Password or App Password |
| `SMTP_SERVER` | ✅ | — | SMTP server for confirmation emails |
| `SMTP_PORT` | | `587` | SMTP port (STARTTLS) |
| `SMTP_USERNAME` | | `EMAIL_ACCOUNT` | SMTP login username |
| `SMTP_PASSWORD` | | `EMAIL_PASSWORD` | SMTP password |
| `FROM_ADDRESS` | | `EMAIL_ACCOUNT` | Sender address for outgoing emails |
| `PRINTER_NAME` | ✅ | — | CUPS queue name — must match `lpstat -p` exactly |
| `SLEEP_TIME` | | `60` | How often to check for new emails (seconds) |
| `ALLOWED_ATTACHMENT_TYPES` | | `pdf,png,jpg,jpeg,docx` | Allowed file extensions (comma-separated) |
| `ALLOWED_RECIPIENTS` | | *(all)* | Only process emails from these addresses (comma-separated); leave empty to allow everyone |
| `CONFIRM_TEMPLATE` | | `default.html` | Template file from `templates/` for confirmation emails |
| `CONFIRM_SUBJECT` | | `Your Print Job Confirmation` | Subject line prefix for confirmation emails |
| `ADMIN_EMAIL` | | — | Receives a detailed error report on every failed print job |
| `WEBUI_ENABLED` | | `true` | Set to `false` to disable the web interface |

---

## Confirmation Email Templates

Templates are located in the `templates/` folder and use [Jinja2](https://jinja.palletsprojects.com/) syntax.
You can switch the active template at any time from the **Templates** page in the WebUI — no restart needed.

### Available variables

| Variable | Description |
|---|---|
| `{{ sender }}` | Email address of the person who sent the file |
| `{{ filename }}` | Name of the printed file |
| `{{ printer }}` | CUPS queue name |
| `{{ timestamp }}` | Date and time of the job |
| `{{ job_id }}` | Short unique job ID |
| `{{ status }}` | `success` or `failed` |

### Included templates

| Template | Description |
|---|---|
| `default.html` | Clean white card layout |
| `fancy.html` | Gradient design with large status icon |

---

## Volumes

| Host path | Container path | Purpose |
|---|---|---|
| `./email2Print/templates` | `/app/templates` | Confirmation email templates |
| `./email2Print/data` | `/app/data` | Print job log (`jobs.json`) |
| `./email2Print/logs` | `/app/logs` | Application log (`email2print.log`) |
| `/your/path/cups-config` | `/etc/cups` | CUPS configuration (read/write) |
| `/your/path/avahi` | `/etc/avahi/services` | Avahi AirPrint service files (read-only) |

---

## Project Structure

```
email2Print/
├── app/
│   ├── main.py               # IMAP polling loop
│   ├── printer.py            # CUPS printing via lp
│   ├── mailer.py             # SMTP confirmation + admin alert
│   ├── templates_engine.py   # Jinja2 template renderer
│   └── webui/
│       ├── server.py         # FastAPI web server
│       └── templates/        # WebUI HTML pages
├── templates/                # Confirmation email templates
├── data/                     # Auto-created: jobs.json
├── logs/                     # Auto-created: email2print.log
├── entrypoint.sh             # Container startup script
├── supervisord.conf          # Manages IMAP poller + WebUI processes
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

The IMAP poller and the WebUI run in the **same container**, managed by **supervisord**.
