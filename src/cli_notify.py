"""
CLI для запуска уведомлений об отпусках.

Это основной скрипт, который вызывается из cron/systemd через run_daily_notify.sh.
Полный пайплайн: парсинг Excel → определение получателей → отправка уведомлений.

Примеры:
    # Dry-run (без отправки, сохраняет .eml для предпросмотра)
    python src/cli_notify.py -c config/config.json

    # Реальная отправка
    python src/cli_notify.py -c config/config.json --send

    # Предпросмотр всех уведомлений (включая будущие)
    python src/cli_notify.py -c config/config.json --all --preview-dir logs/email_previews
"""
import argparse
import json
import os
import sys
import pathlib
import logging

root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=root.joinpath('.env'), override=False)

from src.notify_vacations import notify_due


def setup_logging(config: dict):
    log_cfg = config.get('logging', {})
    level = getattr(logging, log_cfg.get('level', 'INFO').upper(), logging.INFO)
    fmt = log_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handlers = []
    if log_cfg.get('console', True):
        handlers.append(logging.StreamHandler(sys.stdout))

    log_file = log_cfg.get('file')
    if log_file:
        log_path = pathlib.Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(str(log_path), encoding='utf-8'))

    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def main():
    p = argparse.ArgumentParser(
        description='Уведомления об отпусках: парсинг Excel → рассылка уведомлений'
    )
    p.add_argument('--config', '-c', default='config/config.json',
                   help='Путь к конфигурационному файлу (default: config/config.json)')
    p.add_argument('--send', action='store_true',
                   help='Реально отправить письма (без флага — dry-run)')
    p.add_argument('--all', action='store_true',
                   help='Обработать все записи, включая будущие (для тестирования)')
    p.add_argument('--preview-dir', default='logs/email_previews',
                   help='Папка для сохранения .eml предпросмотров')
    args = p.parse_args()

    cfg_path = pathlib.Path(args.config)
    if not cfg_path.exists():
        print(f'Config not found: {cfg_path}', file=sys.stderr)
        sys.exit(1)

    cfg = json.load(cfg_path.open(encoding='utf-8'))

    smtp_cfg = cfg.get('smtp', {})
    env_overrides = {
        'server':     os.environ.get('SMTP_SERVER'),
        'port':       os.environ.get('SMTP_PORT'),
        'username':   os.environ.get('SMTP_USERNAME'),
        'password':   os.environ.get('SMTP_PASSWORD'),
        'from_email': os.environ.get('SMTP_FROM_EMAIL'),
        'from_name':  os.environ.get('SMTP_FROM_NAME'),
    }
    for key, val in env_overrides.items():
        if val is not None:
            smtp_cfg[key] = int(val) if key == 'port' else val
    cfg['smtp'] = smtp_cfg

    paths = cfg.get('paths', {})
    for cfg_key, env_key in [('excel_folder', 'EXCEL_FOLDER'),
                              ('attachments_folder', 'ATTACHMENTS_FOLDER'),
                              ('templates_folder', 'TEMPLATES_FOLDER')]:
        env_val = os.environ.get(env_key)
        if env_val:
            paths[cfg_key] = env_val
    cfg['paths'] = paths

    setup_logging(cfg)
    logger = logging.getLogger('cli_notify')

    dry_run = not args.send
    mode = 'DRY-RUN' if dry_run else 'SEND'
    logger.info(f'Starting vacation notifications [{mode}]')

    try:
        results = notify_due(
            cfg,
            dry_run=dry_run,
            include_future=args.all,
            preview_dir=args.preview_dir,
        )
    except FileNotFoundError as e:
        logger.error(f'Excel file not found: {e}')
        sys.exit(1)
    except ValueError as e:
        logger.error(f'Configuration error: {e}')
        sys.exit(1)

    if results:
        logger.info(f'Processed {len(results)} notification(s):')
        for r in results:
            status = 'SENT' if r.get('sent') else 'FAILED'
            if dry_run:
                status = 'DRY-RUN'
            logger.info(f"  [{r['type']}] {r['employee']} ({r['email']}) -> {status}")
    else:
        logger.info('No notifications due today.')

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
