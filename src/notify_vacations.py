"""
Бизнес-логика уведомлений об отпусках.

Полный пайплайн:
1. Читает расписание отпусков из Excel (через vacation_reader).
2. Определяет, кому нужно отправить уведомление сегодня (preapproval / deadline).
3. Для каждого сотрудника находит email руководителя и ФМ (из того же Excel-файла).
4. Отправляет письма через EmailSender (или сохраняет .eml в режиме dry-run).
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from src.vacation_reader import read_vacation_schedule, _find_in_top_rows
from src.email_sender import EmailSender
import logging

logger = logging.getLogger(__name__)


def _iso_to_date(s: str) -> datetime.date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def _load_extra_columns(config: Dict) -> Optional[pd.DataFrame]:
    """Load raw Excel DataFrame once for manager/FM column lookups."""
    vs = config.get('vacation_settings', {})
    file = vs.get('file', '')
    path = Path(file)
    if not path.exists():
        path = Path('data') / file
        if not path.exists():
            return None
    try:
        xls = pd.ExcelFile(path)
        sheet = vs.get('sheet_name') or xls.sheet_names[0]
        return pd.read_excel(xls, sheet_name=sheet, header=None)
    except Exception as e:
        logger.warning(f'Could not load Excel for extra columns: {e}')
        return None


def _find_employee_extra(
    df: pd.DataFrame,
    employee_name: str,
    emp_col_name: str,
    manager_col_name: Optional[str],
    fm_col_name: Optional[str],
) -> dict:
    """Find manager and FM emails for a given employee from the raw DataFrame."""
    result = {'manager_email': None, 'fm_email': None}
    if df is None:
        return result

    emp_col_idx = _find_in_top_rows(df, emp_col_name, max_row=10)
    if emp_col_idx is None:
        return result

    emp_row_idx = None
    for r in range(df.shape[0]):
        v = df.iat[r, emp_col_idx]
        if not pd.isna(v) and str(v).strip() == employee_name:
            emp_row_idx = r
            break
    if emp_row_idx is None:
        return result

    if manager_col_name:
        man_idx = _find_in_top_rows(df, manager_col_name, max_row=10)
        if man_idx is not None:
            val = df.iat[emp_row_idx, man_idx]
            if not pd.isna(val) and str(val).strip():
                result['manager_email'] = str(val).strip()

    if fm_col_name:
        fm_idx = _find_in_top_rows(df, fm_col_name, max_row=10)
        if fm_idx is not None:
            val = df.iat[emp_row_idx, fm_idx]
            if not pd.isna(val) and str(val).strip():
                result['fm_email'] = str(val).strip()

    return result


def notify_due(config: Dict, dry_run=True, include_future: bool = False, preview_dir: str = None) -> List[Dict]:
    """
    Основная функция: определяет кому и когда отправлять уведомления и отправляет их.

    Args:
        config: Полный конфиг приложения.
        dry_run: Если True — письма не отправляются, только логируются и сохраняются как .eml.
        include_future: Если True — обрабатывает все записи (для тестирования / предпросмотра).
        preview_dir: Папка для сохранения .eml файлов.

    Returns:
        Список словарей с информацией об отправленных уведомлениях.
    """
    vs = config['vacation_settings']
    notifications = config.get('notifications', {})

    pre_offset = notifications.get('preapproval_offset_days', 21)
    deadline_offset = notifications.get('deadline_offset_days', 8)
    approval_deadline_days = notifications.get('approval_deadline_days', 7)
    send_only_due = notifications.get('send_only_due', True)

    manager_col = notifications.get('manager_email_column')
    fm_col = notifications.get('fm_email_column')

    schedule = read_vacation_schedule(config)
    logger.info(f'Loaded vacation schedule: {len(schedule)} employees')

    extra_df = _load_extra_columns(config)

    sender = EmailSender(
        config.get('smtp', {}),
        templates_path=config.get('paths', {}).get('templates_folder', 'templates')
    )

    attachments_folder = config.get('paths', {}).get('attachments_folder', 'attachments')
    standard_attachment = notifications.get('standard_attachment')

    attachment_paths = []
    if standard_attachment:
        att_path = Path(attachments_folder) / standard_attachment
        if att_path.exists():
            attachment_paths = [str(att_path)]
        else:
            logger.warning(f'Standard attachment not found: {att_path}')

    today = datetime.today().date()
    sent = []

    for row in schedule:
        if not row['vacations']:
            continue
        if not row['email']:
            logger.warning(f"No email for employee {row['employee']}, skipping")
            continue

        first_day = min(row['vacations'])
        first_date = _iso_to_date(first_day)

        extras = _find_employee_extra(
            extra_df, row['employee'],
            vs['employee_column'], manager_col, fm_col
        )
        cc_list = [e for e in [extras['manager_email'], extras['fm_email']] if e]

        pre_date = first_date - timedelta(days=pre_offset)
        deadline_date = first_date - timedelta(days=deadline_offset)

        if include_future:
            pre_should = True
            deadline_should = True
        else:
            if send_only_due:
                pre_should = (pre_date == today)
                deadline_should = (deadline_date == today)
            else:
                pre_should = (pre_date <= today)
                deadline_should = (deadline_date <= today)

        template_context = {
            'employee': row['employee'],
            'first_date': first_date.isoformat(),
            'approval_deadline_days': approval_deadline_days,
            'deadline_date': deadline_date.isoformat(),
            'vacations': row['vacations'],
        }

        if pre_should:
            subj = f"Уведомление: предстоящий отпуск ({row['employee']})"
            try:
                body = sender.render_template(
                    notifications.get('preapproval_template', 'preapproval.html'),
                    template_context
                )
            except Exception as e:
                logger.warning(f'Template render failed for preapproval: {e}')
                body = (
                    f"Уведомление: отпуск {row['employee']} начинается {first_date.isoformat()}.\n"
                    f"Пожалуйста, подайте заявление не позднее чем за {approval_deadline_days} дней."
                )

            ok = sender.send(
                subj, [row['email']], cc_list, body,
                attachments=attachment_paths, dry_run=dry_run, preview_dir=preview_dir
            )
            sent.append({
                'type': 'preapproval',
                'employee': row['employee'],
                'email': row['email'],
                'cc': cc_list,
                'first_date': first_date.isoformat(),
                'notify_date': pre_date.isoformat(),
                'sent': ok,
            })

        if deadline_should:
            subj = f"Срочно: дедлайн подачи заявления на отпуск ({row['employee']})"
            try:
                body = sender.render_template(
                    notifications.get('deadline_template', 'deadline.html'),
                    template_context
                )
            except Exception as e:
                logger.warning(f'Template render failed for deadline: {e}')
                body = (
                    f"Напоминание: дедлайн подачи заявления на отпуск для {row['employee']} "
                    f"к {deadline_date.isoformat()}. Отпуск начинается {first_date.isoformat()}."
                )

            ok = sender.send(
                subj, [row['email']], cc_list, body,
                attachments=attachment_paths, dry_run=dry_run, preview_dir=preview_dir
            )
            sent.append({
                'type': 'deadline',
                'employee': row['employee'],
                'email': row['email'],
                'cc': cc_list,
                'first_date': first_date.isoformat(),
                'notify_date': deadline_date.isoformat(),
                'sent': ok,
            })

    logger.info(f'Notifications processed: {len(sent)} total')
    return sent
