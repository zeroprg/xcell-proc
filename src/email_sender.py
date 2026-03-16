import smtplib
from email.message import EmailMessage
from typing import List, Optional
import logging
from pathlib import Path
import jinja2
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, smtp_config: dict, templates_path: str = 'templates'):
        self.smtp = smtp_config
        self.templates_path = templates_path
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.templates_path))

    def render_template(self, template_name: str, context: dict) -> str:
        tmpl = self.env.get_template(template_name)
        return tmpl.render(**context)

    def compose_message(self, subject: str, to: List[str], cc: List[str], body: str, attachments: Optional[List[str]] = None) -> EmailMessage:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f"{self.smtp.get('from_name')} <{self.smtp.get('from_email')}>"
        msg['To'] = ', '.join(to)
        if cc:
            msg['Cc'] = ', '.join(cc)
        msg.set_content(body)

        for a in attachments or []:
            p = Path(a)
            if not p.exists():
                logger.warning(f'Attachment not found: {a}')
                continue
            with p.open('rb') as fh:
                data = fh.read()
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=p.name)

        return msg

    def send(self, subject: str, to: List[str], cc: List[str], body: str, attachments: Optional[List[str]] = None, dry_run: bool = True, preview_dir: Optional[str] = None):
        msg = self.compose_message(subject, to, cc, body, attachments)

        # Attach files
        for a in attachments or []:
            p = Path(a)
            if not p.exists():
                logger.warning(f'Attachment not found: {a}')
                continue
            with p.open('rb') as fh:
                data = fh.read()
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=p.name)

        # if preview requested, write .eml to preview_dir for debugging
        if preview_dir:
            pdir = Path(preview_dir)
            pdir.mkdir(parents=True, exist_ok=True)
            # filename safe employee/subject
            fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{subject[:40].replace(' ','_')}.eml"
            out = pdir / fname
            with out.open('wb') as fh:
                fh.write(msg.as_bytes())
            logger.info(f'Wrote preview email to {out}')

        if dry_run:
            logger.info('Dry run: would send email')
            logger.info(f'To: {to} CC: {cc} Subject: {subject}')
            return True

        # real send
        server = self.smtp.get('server')
        port = int(self.smtp.get('port', 25))
        use_tls = bool(self.smtp.get('use_tls', True))
        use_ssl = bool(self.smtp.get('use_ssl', False))
        timeout = float(self.smtp.get('timeout', 60))
        username = self.smtp.get('username')
        password = self.smtp.get('password')

        # ensure server is a string
        if server is None:
            raise ValueError('SMTP server is not configured')
        server = str(server)

        try:
            if use_ssl:
                s = smtplib.SMTP_SSL(server, port, timeout=timeout)
            else:
                s = smtplib.SMTP(server, port, timeout=timeout)
                if use_tls:
                    s.starttls()

            if username and password:
                s.login(username, password)

            s.send_message(msg)
            s.quit()
            logger.info('Email sent')
            return True
        except Exception as e:
            logger.error(f'Failed to send email: {e}')
            return False
