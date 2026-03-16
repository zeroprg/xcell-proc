import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd

from src.vacation_reader import read_vacation_schedule
from src.email_sender import EmailSender
import logging

logger = logging.getLogger(__name__)


def _iso_to_date(s: str) -> datetime.date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def notify_due(config: Dict, dry_run=True, include_future: bool = False, preview_dir: str = None):
    vs = config['vacation_settings']
    notifications = config.get('notifications', {})

    pre_offset = notifications.get('preapproval_offset_days', 21)
    deadline_offset = notifications.get('deadline_offset_days', 8)
    approval_deadline_days = notifications.get('approval_deadline_days', 7)

    manager_col = notifications.get('manager_email_column')
    fm_col = notifications.get('fm_email_column')

    # read vacation schedule from reader
    schedule = read_vacation_schedule(config)

    sender = EmailSender(config.get('smtp', {}), templates_path=config.get('paths', {}).get('templates_folder', 'templates'))

    today = datetime.today().date()
    sent = []

    for row in schedule:
        if not row['vacations']:
            continue
        first_day = min(row['vacations'])
        first_date = _iso_to_date(first_day)

        # load manager and fm emails from the original sheet: we need to locate them via vacation_reader by reading df again
        # For simplicity, attempt to read manager/fm from the same sheet using pandas by matching employee row
        # fallback to None if not found
        manager_email = None
        fm_email = None
        try:
            # read raw sheet to find the row
            path = Path(vs['file'])
            if not path.exists():
                path = Path('data') / vs['file']
            xls = pd.ExcelFile(path)
            sheet = vs.get('sheet_name') or xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            # find employee cell
            emp_col_idx = None
            # find column index where header matches employee column name
            for c in range(df.shape[1]):
                if not pd.isna(df.iat[0, c]) and str(df.iat[0, c]).strip() == vs['employee_column']:
                    emp_col_idx = c
                    break
            if emp_col_idx is not None:
                # find employee row
                emp_row_idx = None
                for r in range(df.shape[0]):
                    v = df.iat[r, emp_col_idx]
                    if not pd.isna(v) and str(v).strip() == row['employee']:
                        emp_row_idx = r
                        break
                if emp_row_idx is not None:
                    # find manager and fm columns by header
                    man_idx = None
                    fm_idx = None
                    for c in range(df.shape[1]):
                        vh = df.iat[0, c]
                        if not pd.isna(vh):
                            if str(vh).strip() == manager_col:
                                man_idx = c
                            if str(vh).strip() == fm_col:
                                fm_idx = c
                    if man_idx is not None:
                        manager_email = df.iat[emp_row_idx, man_idx]
                    if fm_idx is not None:
                        fm_email = df.iat[emp_row_idx, fm_idx]
        except Exception:
            pass

        # compute preapproval notification date
        pre_date = first_date - timedelta(days=pre_offset)
        deadline_date = first_date - timedelta(days=deadline_offset)

        # determine whether to send/preview preapproval
        if include_future:
            pre_should = True
        else:
            pre_should = (pre_date <= today and (not notifications.get('send_only_due', True) or pre_date == today))

        # determine whether to send/preview deadline
        if include_future:
            deadline_should = True
        else:
            deadline_should = (deadline_date <= today and (not notifications.get('send_only_due', True) or deadline_date == today))

        # send preapproval if due/preview
        if pre_should:
            subj = 'Уведомление: предстоящий отпуск'
            # render template
            try:
                body = sender.render_template(notifications.get('preapproval_template'), {
                    'employee': row['employee'],
                    'first_date': first_date.isoformat(),
                    'approval_deadline_days': approval_deadline_days
                })
            except Exception:
                body = f"Уведомление: отпуск {row['employee']} начинается {first_date.isoformat()}"
            to = [row['email']]
            cc = [e for e in [manager_email, fm_email] if e and not pd.isna(e)]
            attachments = [Path(config.get('paths', {}).get('attachments_folder', 'attachments')) / notifications.get('standard_attachment')]
            attachments = [str(p) for p in attachments if p.exists()]
            sender.send(subj, to, cc, body, attachments=attachments, dry_run=dry_run, preview_dir=preview_dir)
            sent.append({
                'type': 'preapproval',
                'employee': row['employee'],
                'first_date': first_date.isoformat(),
                'notify_date': pre_date.isoformat(),
            })

        # send deadline notification if due
        if deadline_should:
            subj = 'Уведомление: дедлайн на подачу заявления'
            try:
                body = sender.render_template(notifications.get('deadline_template'), {
                    'employee': row['employee'],
                    'first_date': first_date.isoformat(),
                    'deadline_date': deadline_date.isoformat()
                })
            except Exception:
                body = f"Напоминание: дедлайн подачи заявления на отпуск для {row['employee']} к {deadline_date.isoformat()}"
            to = [row['email']]
            cc = [e for e in [manager_email, fm_email] if e and not pd.isna(e)]
            attachments = [Path(config.get('paths', {}).get('attachments_folder', 'attachments')) / notifications.get('standard_attachment')]
            attachments = [str(p) for p in attachments if p.exists()]
            sender.send(subj, to, cc, body, attachments=attachments, dry_run=dry_run, preview_dir=preview_dir)
            sent.append({
                'type': 'deadline',
                'employee': row['employee'],
                'first_date': first_date.isoformat(),
                'notify_date': deadline_date.isoformat(),
            })

    return sent
