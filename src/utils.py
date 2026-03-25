"""Общие утилиты для проекта xcell-proc."""
import json
import logging
import sys
from pathlib import Path
from typing import Dict


def load_config(path: str) -> Dict:
    """Загрузить JSON-конфиг из файла."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f'Config not found: {path}')
    return json.load(p.open(encoding='utf-8'))


def setup_logging(config: Dict):
    """Настроить логирование на основе секции 'logging' в конфиге."""
    log_cfg = config.get('logging', {})
    level = getattr(logging, log_cfg.get('level', 'INFO').upper(), logging.INFO)
    fmt = log_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handlers = []
    if log_cfg.get('console', True):
        handlers.append(logging.StreamHandler(sys.stdout))

    log_file = log_cfg.get('file')
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(str(log_path), encoding='utf-8'))

    logging.basicConfig(level=level, format=fmt, handlers=handlers)
