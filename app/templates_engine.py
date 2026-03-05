import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

TEMPLATES_DIR = "/app/templates"

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def render_template(template_name: str, context: dict) -> str:
    try:
        tpl = _env.get_template(template_name)
        return tpl.render(**context)
    except TemplateNotFound:
        # Fallback: plain text
        return (
            f"Your print job has been processed.\n\n"
            f"File    : {context.get('filename')}\n"
            f"Printer : {context.get('printer')}\n"
            f"Status  : {context.get('status')}\n"
            f"Time    : {context.get('timestamp')}\n"
            f"Job ID  : {context.get('job_id')}\n"
        )
