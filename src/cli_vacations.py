import json
import sys
from pathlib import Path
from typing import Dict

from src.vacation_reader import read_vacation_schedule


def load_config(path: str) -> Dict:
    return json.load(open(path, 'r', encoding='utf-8'))


def main(argv=None):
    argv = argv or sys.argv[1:]
    config_path = argv[0] if argv else 'config/config.example.json'
    cfg = load_config(config_path)
    schedule = read_vacation_schedule(cfg)
    print(json.dumps(schedule, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
