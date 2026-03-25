"""Integration-level tests for cli_notify entry point."""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli_notify import main


def _create_test_env(tmp_path):
    """Create minimal config + xlsx for integration test."""
    tpl_dir = tmp_path / 'templates'
    tpl_dir.mkdir()
    (tpl_dir / 'preapproval.html').write_text(
        '<p>Отпуск: {{ employee }}, дата: {{ first_date }}</p>', encoding='utf-8'
    )
    (tpl_dir / 'deadline.html').write_text(
        '<p>Дедлайн: {{ employee }}, к {{ deadline_date }}</p>', encoding='utf-8'
    )

    row0 = ['ФИО сотрудника', 'email работника', 'Январь'] + [None] * 5
    row1 = [None, None, 1, 2, 3, 4, 5, 6]
    row2 = ['Тестов Тест', 'test@example.com', '+', None, None, None, None, None]
    df = pd.DataFrame([row0, row1, row2])
    xlsx = tmp_path / 'Отпуска.xlsx'
    df.to_excel(xlsx, index=False, header=False)

    config = {
        'smtp': {
            'server': 'smtp.example.com', 'port': 587,
            'use_tls': True, 'username': 'u', 'password': 'p',
            'from_email': 'hr@example.com', 'from_name': 'HR',
        },
        'paths': {
            'templates_folder': str(tpl_dir),
            'attachments_folder': str(tmp_path / 'attachments'),
        },
        'vacation_settings': {
            'file': str(xlsx), 'sheet_name': None,
            'employee_column': 'ФИО сотрудника',
            'email_column': 'email работника',
            'months': ['Январь'], 'year': 2026,
        },
        'notifications': {
            'preapproval_offset_days': 21,
            'deadline_offset_days': 8,
            'approval_deadline_days': 7,
            'preapproval_template': 'preapproval.html',
            'deadline_template': 'deadline.html',
            'send_only_due': True,
        },
        'logging': {'level': 'WARNING', 'console': False},
    }

    import json
    cfg_path = tmp_path / 'config.json'
    cfg_path.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
    return cfg_path


class TestCliNotifyIntegration:
    def test_dry_run_all(self, tmp_path):
        cfg_path = _create_test_env(tmp_path)
        preview = tmp_path / 'previews'

        with patch('sys.argv', ['cli_notify.py', '-c', str(cfg_path), '--all',
                                '--preview-dir', str(preview)]):
            main()

        eml_files = list(preview.glob('*.eml'))
        assert len(eml_files) >= 1
