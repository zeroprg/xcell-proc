import json
import tempfile
import sys
from pathlib import Path

import pandas as pd

# ensure project root is on sys.path so `src` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.vacation_reader import read_vacation_schedule


def test_read_vacation_schedule(tmp_path):
    # build a small DataFrame representing a simplified vacation sheet
    # build a sheet where row0 has month names, row1 has day numbers, rows 2+ are employees
    # columns: ['ФИО сотрудника', 'email работника', 'Январь', day1, day2, 'Февраль', day1]
    row0 = ['ФИО сотрудника', 'email работника', 'Январь', None, None, 'Февраль', None]
    row1 = [None, None, 1, 2, 3, 1, 2]
    row2 = ['Иванов Иван', 'ivan@example.com', None, 'X', None, None, None]
    row3 = ['Петров Петр', 'petr@example.com', None, None, 'Y', 'Z', None]
    df = pd.DataFrame([row0, row1, row2, row3])

    file = tmp_path / 'vac_test.xlsx'
    df.to_excel(file, index=False, header=False)

    cfg = {
        'vacation_settings': {
            'file': str(file),
            'sheet_name': None,
            'employee_column': 'ФИО сотрудника',
            'email_column': 'email работника',
            'months': ['Январь', 'Февраль'],
            'year': 2026
        }
    }

    res = read_vacation_schedule(cfg)
    assert isinstance(res, list)
    # expect two employees
    assert len(res) == 2
    # each should have at least one vacation day (non-empty cell)
    for r in res:
        assert 'employee' in r and 'vacations' in r
        assert len(r['vacations']) >= 1
