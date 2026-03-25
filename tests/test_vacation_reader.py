import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.vacation_reader import read_vacation_schedule, _is_vacation_marker


class TestVacationMarkers:
    def test_valid_markers(self):
        for m in ['+', 'V', 'v', 'X', 'x', 'Х', 'х']:
            assert _is_vacation_marker(m), f'Expected {m!r} to be a vacation marker'

    def test_invalid_markers(self):
        assert not _is_vacation_marker(None)
        assert not _is_vacation_marker('')
        assert not _is_vacation_marker(' ')
        assert not _is_vacation_marker('A')
        assert not _is_vacation_marker('1')
        assert not _is_vacation_marker(float('nan'))


class TestReadVacationSchedule:
    def _make_sheet(self, tmp_path, rows):
        df = pd.DataFrame(rows)
        file = tmp_path / 'vac_test.xlsx'
        df.to_excel(file, index=False, header=False)
        return file

    def _cfg(self, file_path, months=None):
        return {
            'vacation_settings': {
                'file': str(file_path),
                'sheet_name': None,
                'employee_column': 'ФИО сотрудника',
                'email_column': 'email работника',
                'months': months or ['Январь', 'Февраль'],
                'year': 2026
            }
        }

    def test_basic_schedule(self, tmp_path):
        row0 = ['ФИО сотрудника', 'email работника', 'Январь', None, None, 'Февраль', None]
        row1 = [None, None, 1, 2, 3, 1, 2]
        row2 = ['Иванов Иван', 'ivan@example.com', None, '+', None, None, None]
        row3 = ['Петров Петр', 'petr@example.com', None, None, 'V', '+', None]

        file = self._make_sheet(tmp_path, [row0, row1, row2, row3])
        res = read_vacation_schedule(self._cfg(file))

        assert len(res) == 2

        ivan = next(r for r in res if r['employee'] == 'Иванов Иван')
        assert ivan['email'] == 'ivan@example.com'
        assert ivan['vacations'] == ['2026-01-02']

        petr = next(r for r in res if r['employee'] == 'Петров Петр')
        assert set(petr['vacations']) == {'2026-01-03', '2026-02-01'}

    def test_non_marker_cells_ignored(self, tmp_path):
        """Cells with text that isn't a recognized marker should be ignored."""
        row0 = ['ФИО сотрудника', 'email работника', 'Январь'] + [None] * 5
        row1 = [None, None, 1, 2, 3, 4, 5, 6]
        row2 = ['Сидоров', 'sid@example.com', 'БОЛЕН', '+', None, None, None, None]

        file = self._make_sheet(tmp_path, [row0, row1, row2])
        res = read_vacation_schedule(self._cfg(file, months=['Январь']))

        assert len(res) == 1
        assert res[0]['vacations'] == ['2026-01-02']

    def test_empty_schedule(self, tmp_path):
        row0 = ['ФИО сотрудника', 'email работника', 'Январь'] + [None] * 5
        row1 = [None, None, 1, 2, 3, 4, 5, 6]
        row2 = ['Козлов', 'koz@example.com', None, None, None, None, None, None]

        file = self._make_sheet(tmp_path, [row0, row1, row2])
        res = read_vacation_schedule(self._cfg(file, months=['Январь']))

        assert len(res) == 1
        assert res[0]['vacations'] == []

    def test_missing_vacation_settings(self):
        with pytest.raises(ValueError, match='vacation_settings'):
            read_vacation_schedule({})

    def test_file_not_found(self):
        cfg = {
            'vacation_settings': {
                'file': 'nonexistent_file.xlsx',
                'employee_column': 'ФИО',
                'email_column': 'email',
                'months': ['Январь'],
                'year': 2026
            }
        }
        with pytest.raises(FileNotFoundError):
            read_vacation_schedule(cfg)
