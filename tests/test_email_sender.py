import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.email_sender import EmailSender


@pytest.fixture
def smtp_config():
    return {
        'server': 'smtp.example.com',
        'port': 587,
        'use_tls': True,
        'use_ssl': False,
        'username': 'test@example.com',
        'password': 'secret',
        'from_email': 'test@example.com',
        'from_name': 'Test Sender',
    }


@pytest.fixture
def sender(smtp_config, tmp_path):
    tpl_dir = tmp_path / 'templates'
    tpl_dir.mkdir()
    (tpl_dir / 'test.html').write_text('<p>Hello, {{ name }}!</p>', encoding='utf-8')
    return EmailSender(smtp_config, templates_path=str(tpl_dir))


class TestEmailSender:
    def test_render_template(self, sender):
        result = sender.render_template('test.html', {'name': 'Alice'})
        assert '<p>Hello, Alice!</p>' in result

    def test_compose_message_basic(self, sender):
        msg = sender.compose_message('Test', ['a@b.com'], [], 'Hello')
        assert msg['Subject'] == 'Test'
        assert 'a@b.com' in msg['To']
        assert msg['Cc'] is None

    def test_compose_message_with_cc(self, sender):
        msg = sender.compose_message('Test', ['a@b.com'], ['c@d.com'], 'Hello')
        assert 'c@d.com' in msg['Cc']

    def test_compose_message_with_attachment(self, sender, tmp_path):
        att = tmp_path / 'file.txt'
        att.write_text('attachment content')
        msg = sender.compose_message('Test', ['a@b.com'], [], 'Hello', attachments=[str(att)])
        payloads = msg.get_payload()
        assert len(payloads) == 2  # body + 1 attachment

    def test_no_duplicate_attachments(self, sender, tmp_path):
        """Regression: send() should NOT double-attach files."""
        att = tmp_path / 'file.txt'
        att.write_text('data')
        with patch('smtplib.SMTP') as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value = instance
            sender.send('Test', ['a@b.com'], [], 'Hello',
                        attachments=[str(att)], dry_run=False)
            sent_msg = instance.send_message.call_args[0][0]
            attachment_count = sum(
                1 for part in sent_msg.walk()
                if part.get_content_disposition() == 'attachment'
            )
            assert attachment_count == 1

    def test_dry_run_does_not_send(self, sender):
        with patch('smtplib.SMTP') as mock_smtp:
            result = sender.send('Test', ['a@b.com'], [], 'Body', dry_run=True)
            assert result is True
            mock_smtp.assert_not_called()

    def test_preview_eml(self, sender, tmp_path):
        preview = tmp_path / 'previews'
        sender.send('Test', ['a@b.com'], [], 'Body', dry_run=True, preview_dir=str(preview))
        eml_files = list(preview.glob('*.eml'))
        assert len(eml_files) == 1

    def test_html_body_sent_as_html(self, sender):
        """HTML bodies should be sent with content-type text/html, not text/plain."""
        html = '<html><body><p>Hello</p></body></html>'
        msg = sender.compose_message('Test', ['a@b.com'], [], html)
        assert msg.get_content_type() == 'text/html'

    def test_plain_text_body_sent_as_text(self, sender):
        msg = sender.compose_message('Test', ['a@b.com'], [], 'Plain text body')
        assert msg.get_content_type() == 'text/plain'
