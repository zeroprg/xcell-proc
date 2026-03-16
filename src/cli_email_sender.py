import argparse
import json
import os
import sys
import pathlib
from pathlib import Path
from typing import List

# Ensure project root is on sys.path so `from src.email_sender import EmailSender`
# works when running this file as a script: `python src/cli_email_sender.py ...`.
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from dotenv import load_dotenv

# load .env from project root if present (do not override existing env vars)
load_dotenv(dotenv_path=root.joinpath('.env'), override=False)

from src.email_sender import EmailSender


def parse_list(s: str) -> List[str]:
    if not s:
        return []
    return [p.strip() for p in s.split(',') if p.strip()]


def main():
    p = argparse.ArgumentParser(description='CLI email sender for tests and previews')
    p.add_argument('--config', '-c', default='config/config.example.json', help='Path to config JSON')
    p.add_argument('--to', '-t', help='Comma-separated recipient emails')
    p.add_argument('--cc', help='Comma-separated CC emails')
    p.add_argument('--subject', '-s', help='Email subject')
    p.add_argument('--template', help='Template filename (in templates folder)')
    p.add_argument('--body', help='Raw text body (used if no template)')
    p.add_argument('--attachments', help='Comma-separated attachment paths')
    p.add_argument('--preview-dir', default='logs/email_previews', help='Directory to write .eml previews')
    p.add_argument('--send', action='store_true', help='Actually send emails (default: dry-run)')
    p.add_argument('--from-name', help='Override From name')
    p.add_argument('--from-email', help='Override From email')
    p.add_argument('--test-recipient', help='Use this single address as recipient for testing')
    args = p.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise SystemExit(f'Config not found: {cfg_path}')

    cfg = json.load(cfg_path.open(encoding='utf-8'))
    smtp_cfg = cfg.get('smtp', {})
    paths = cfg.get('paths', {})
    templates_dir = paths.get('templates_folder', 'templates')

    # allow overrides from env (safe way to provide creds in CI)
    smtp_cfg['username'] = os.environ.get('SMTP_USERNAME', smtp_cfg.get('username'))
    smtp_cfg['password'] = os.environ.get('SMTP_PASSWORD', smtp_cfg.get('password'))
    if args.from_name:
        smtp_cfg['from_name'] = args.from_name
    if args.from_email:
        smtp_cfg['from_email'] = args.from_email

    sender = EmailSender(smtp_cfg, templates_path=templates_dir)

    # determine recipients
    to = parse_list(args.to or '')
    cc = parse_list(args.cc or '')
    if args.test_recipient:
        to = [args.test_recipient]
    # fallback to smtp.from_email if no recipient provided
    if not to:
        fallback = smtp_cfg.get('from_email')
        if fallback:
            print('No recipient provided, using default from_email as test recipient:', fallback)
            to = [fallback]
        else:
            raise SystemExit('No recipients specified and no fallback available')

    # subject/body/template
    subject = args.subject or cfg.get('email_settings', {}).get('subject', 'Test email')
    body = ''
    attachments = parse_list(args.attachments or '')

    if args.template:
        context = {
            'subject': subject,
            'to': to,
            'cc': cc,
        }
        body = sender.render_template(args.template, context)
    elif args.body:
        body = args.body
    else:
        # try to use plain template from config
        tpl = cfg.get('email_settings', {}).get('template_file')
        if tpl:
            body = sender.render_template(tpl, {'subject': subject, 'to': to, 'cc': cc})
        else:
            body = 'Тестовое письмо. Это тело по умолчанию.'

    dry_run = not args.send
    preview_dir = args.preview_dir

    ok = sender.send(subject=subject, to=to, cc=cc, body=body, attachments=attachments, dry_run=dry_run, preview_dir=preview_dir)
    if ok:
        print('Done (dry_run=%s)' % dry_run)
        raise SystemExit(0)
    else:
        print('Failed to send')
        raise SystemExit(2)


if __name__ == '__main__':
    main()
