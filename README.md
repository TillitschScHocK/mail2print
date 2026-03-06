# Mail2Print

Mail2Print watches an email inbox, prints supported attachments automatically through CUPS, and sends a confirmation email back to the sender.

It ships with a ready-to-run Docker Compose stack that includes CUPS, Avahi for AirPrint service publishing, and the Mail2Print app with an optional web interface.

## Features

- Monitor an IMAP inbox for new emails.
- Print supported file attachments automatically.
- Send a confirmation email after each processed print job.
- Store job history and logs in persistent local folders.
- Manage the app through the built-in web UI.
- Run the full stack with Docker Compose.

## Included services

The included `docker-compose.yml` starts these services:

- `cups-init`: Creates the initial CUPS configuration in `./cups` on first start.
- `cups`: Runs the CUPS print server with the web interface enabled.
- `avahi`: Publishes printer services on the local network for discovery.
- `mail2print`: Connects to your mailbox, processes attachments, and starts the web UI.

## Requirements

Before you start, make sure you have:

- Docker
- Docker Compose plugin (`docker compose`)
- A Linux host that can use `network_mode: host`
- A printer that can be added to CUPS
- A dedicated email inbox for Mail2Print

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/TillitschScHocK/mail2print.git
cd mail2print
```

### 2. Create your environment file

Copy the example file and edit it:

```bash
cp .env.example .env
```

At minimum, set these values in `.env`:

- `PRINTER_NAME`
- `IMAP_SERVER`
- `EMAIL_ACCOUNT`
- `EMAIL_PASSWORD`
- `SMTP_SERVER`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

You can keep the other values as they are for the first start.

### 3. Start the stack

```bash
docker compose up -d --build
```

On the first start, the `cups-init` service prepares the CUPS configuration automatically. After that, the regular services continue running in the background.

### 4. Open CUPS and add your printer

Open the CUPS web interface in your browser:

```text
http://<your-server-ip>:631
```

Log in with the values from:

- `CUPS_ADMIN_USER`
- `CUPS_ADMIN_PASSWORD`

Add your printer in CUPS, note the exact queue name, and set that value as `PRINTER_NAME` in `.env`.

If you changed `.env`, restart the app:

```bash
docker compose up -d
```

### 5. Open the Mail2Print web UI

After the stack is running, open:

```text
http://<your-server-ip>:635
```

The web UI provides job history, logs, templates, and status information.

## Folder structure

These folders are used automatically and are created locally next to the Compose file:

- `./cups` for persistent CUPS configuration
- `./avahi` for Avahi service definitions
- `./mail2print/templates` for custom confirmation templates
- `./mail2print/data` for job history and runtime data
- `./mail2print/logs` for application and web UI logs

## Environment variables

Copy `.env.example` to `.env` and adjust the values for your environment.

| Variable | Default | Description |
|---|---|---|
| `CUPS_ADMIN_USER` | `admin` | CUPS administrator username |
| `CUPS_ADMIN_PASSWORD` | `changeme` | CUPS administrator password |
| `PRINTER_NAME` | `Your-Printer-Queue-Name` | Exact CUPS printer queue name |
| `IMAP_SERVER` | `imap.example.com` | IMAP server hostname |
| `IMAP_PORT` | `993` | IMAP port |
| `EMAIL_ACCOUNT` | `print@example.com` | Mailbox address to monitor |
| `EMAIL_PASSWORD` | `your-imap-password` | IMAP password or app password |
| `SMTP_SERVER` | `smtp.example.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | `print@example.com` | SMTP username |
| `SMTP_PASSWORD` | `your-smtp-password` | SMTP password |
| `FROM_ADDRESS` | `print@example.com` | Sender address for confirmation emails |
| `CONFIRM_SUBJECT` | `Your print job was processed` | Subject line for confirmation emails |
| `SLEEP_TIME` | `60` | Poll interval in seconds |
| `ALLOWED_ATTACHMENT_TYPES` | `pdf,docx,png,jpg` | Allowed attachment extensions |
| `ALLOWED_RECIPIENTS` | empty | Optional comma-separated sender allowlist |
| `CONFIRM_TEMPLATE` | `default_en.j2` | Confirmation template filename |
| `ADMIN_EMAIL` | empty | Optional email address for detailed failure notifications |
| `WEBUI_ENABLED` | `true` | Enable or disable the web UI |

## Templates

Mail2Print uses confirmation templates stored in `./mail2print/templates`.

- Template files use the `.j2` extension for HTML templates.
- Plain text templates with `.txt` can also be included.
- On first start, default templates are copied into the templates folder automatically if they do not already exist.

If you want to customize the confirmation email, edit the template files in `./mail2print/templates`.

## Updating

To update the project:

```bash
git pull
docker compose up -d --build
```

## Troubleshooting

### The printer does not print

Check whether the printer exists in CUPS and whether `PRINTER_NAME` matches the queue name exactly.

Open CUPS in the browser or inspect the printer list inside the running environment:

```bash
docker exec cups lpstat -p
```

### The web UI does not open

Make sure port `635` is reachable on your host and that the `mail2print` container is running.

```bash
docker compose ps
```

### Mail login fails

Re-check your IMAP and SMTP credentials in `.env`. For providers such as Gmail, an app password may be required.

### I changed templates or settings

Most environment changes require recreating the container:

```bash
docker compose up -d --build
```

Templates stored in `./mail2print/templates` stay persistent across restarts.
