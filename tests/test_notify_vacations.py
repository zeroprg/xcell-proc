import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.notify_vacations import notify_due


def _make_vacation_sheet(tmp_path, vacations_data, manager_col=None, fm_col=None):
    """
    Build a minimal vacation xlsx and return the path.
    vacations_data: list of (name, email, {month_name: [day_numbers]}, manager_email, fm_email)
    """
    months = ['Январь', 'Февраль']
    row0 = ['ФИО сотрудника', 'email работника']
    row1 = [None, None]

    if manager_col:
        row0.append(manager_col)
        row1.append(None)
    if fm_col:
        row0.append(fm_col)
        row1.append(None)

    day_cols = []
    for m in months:
        row0.append(m)
        row1.append(1)
        day_cols.append((m, 1))
        for d in range(2, 4):
            row0.append(None)
            row1.append(d)
            day_cols.append((m, d))

    rows = [row0, row1]
    for name, email, vac_dict, mgr, fm in vacations_data:
        data_row = [name, email]
        if manager_col:
            data_row.append(mgr)
        if fm_col:
            data_row.append(fm)
        for m, d in day_cols:
            if d in vac_dict.get(m, []):
                data_row.append('+')
            else:
                data_row.append(None)
        rows.append(data_row)

    df = pd.DataFrame(rows)
    file = tmp_path / 'Отпуска.xlsx'
    df.to_excel(file, index=False, header=False)
    return file


def _base_config(file_path, manager_col=None, fm_col=None):
    cfg = {
        'smtp': {
            'server': 'smtp.example.com',
            'port': 587,
            'use_tls': True,
            'username': 'test@example.com',
            'password': 'pwd',
            'from_email': 'test@example.com',
            'from_name': 'HR Bot',
        },
        'paths': {
            'templates_folder': 'templates',
            'attachments_folder': 'attachments',
        },
        'vacation_settings': {
            'file': str(file_path),
            'sheet_name': None,
            'employee_column': 'ФИО сотрудника',
            'email_column': 'email работника',
            'months': ['Январь', 'Февраль'],
            'year': 2026,
        },
        'notifications': {
            'preapproval_offset_days': 21,
            'deadline_offset_days': 8,
            'approval_deadline_days': 7,
            'preapproval_template': 'preapproval.html',
            'deadline_template': 'deadline.html',
            'send_only_due': True,
        },
    }
    if manager_col:
        cfg['notifications']['manager_email_column'] = manager_col
    if fm_col:
        cfg['notifications']['fm_email_column'] = fm_col
    return cfg


class TestNotifyDue:
    def test_include_future_generates_notifications(self, tmp_path):
        file = _make_vacation_sheet(tmp_path, [
            ('Иванов', 'ivan@test.com', {'Январь': [2, 3]}, None, None),
        ])
        cfg = _base_config(file)

        results = notify_due(cfg, dry_run=True, include_future=True)
        assert len(results) == 2
        types = {r['type'] for r in results}
        assert types == {'preapproval', 'deadline'}

    def test_no_notifications_when_not_due(self, tmp_path):
        file = _make_vacation_sheet(tmp_path, [
            ('Иванов', 'ivan@test.com', {'Февраль': [1]}, None, None),
        ])
        cfg = _base_config(file)

        far_future = datetime(2025, 1, 1)
        with patch('src.notify_vacations.datetime') as mock_dt:
            mock_dt.today.return_value = far_future
            mock_dt.strptime = datetime.strptime
            results = notify_due(cfg, dry_run=True)

        assert len(results) == 0

    def test_employee_without_email_skipped(self, tmp_path):
        file = _make_vacation_sheet(tmp_path, [
            ('Безымейловый', '', {'Январь': [1]}, None, None),
        ])
        cfg = _base_config(file)
        results = notify_due(cfg, dry_run=True, include_future=True)
        assert len(results) == 0

    def test_manager_cc_included(self, tmp_path):
        mgr_col = 'email руководителя'
        file = _make_vacation_sheet(
            tmp_path,
            [('Петров', 'petr@test.com', {'Январь': [1]}, 'boss@test.com', None)],
            manager_col=mgr_col,
        )
        cfg = _base_config(file, manager_col=mgr_col)
        results = notify_due(cfg, dry_run=True, include_future=True)

        assert len(results) >= 1
        for r in results:
            assert 'boss@test.com' in r['cc']
