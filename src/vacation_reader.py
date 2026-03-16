"""
Утилита для чтения расписания отпусков из Excel по `vacation_settings`.

Возвращает список словарей: {"employee": ..., "email": ..., "vacations": ["YYYY-MM-DD", ...]}
"""
from pathlib import Path
from typing import List, Dict
import logging
import pandas as pd

"""
Robust vacation reader.

Approach:
- Reads sheet with header=None to access raw cell grid.
- Detects month header columns by scanning top rows for month names.
- Detects the row that contains day numbers (1..31).
- Finds employee and email column indices by searching header rows.
- For each employee row collects any non-empty cell under day columns and maps to date using day number from day-row.

Returns list of dicts: {"employee","email","vacations": [ISO dates]}
"""
from pathlib import Path
from typing import List, Dict, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def _find_in_top_rows(df: pd.DataFrame, value: str, max_row=5) -> Optional[int]:
    """Return column index where value is found in top `max_row` rows (exact, case-insensitive)."""
    for col_idx in range(df.shape[1]):
        for r in range(min(max_row, df.shape[0])):
            cell = df.iat[r, col_idx]
            if pd.isna(cell):
                continue
            try:
                if str(cell).strip().lower() == value.strip().lower():
                    return col_idx
            except Exception:
                continue
    return None


def _detect_month_positions(df: pd.DataFrame, months: List[str], max_row=5) -> Dict[str, int]:
    positions = {}
    for m in months:
        pos = _find_in_top_rows(df, m, max_row=max_row)
        if pos is None:
            raise ValueError(f"Month header not found: {m}")
        positions[m] = pos
    return positions


def _detect_day_row(df: pd.DataFrame, min_count=5, max_search_rows=10) -> Optional[int]:
    # find row index that contains many integers in 1..31
    for r in range(min(max_search_rows, df.shape[0])):
        cnt = 0
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if pd.isna(v):
                continue
            try:
                iv = int(v)
                if 1 <= iv <= 31:
                    cnt += 1
            except Exception:
                continue
        if cnt >= min_count:
            return r
    return None


def read_vacation_schedule(config: Dict) -> List[Dict]:
    vs = config.get('vacation_settings')
    if not vs:
        raise ValueError('vacation_settings is required in config')

    file = vs['file']
    sheet = vs.get('sheet_name')
    emp_col_name = vs['employee_column']
    email_col_name = vs['email_column']
    months = vs['months']
    year = vs.get('year')

    path = Path(file)
    if not path.exists():
        path = Path('data') / file
        if not path.exists():
            raise FileNotFoundError(f'Vacation file not found: {file}')

    # read raw grid
    xls = pd.ExcelFile(path)
    sheet_name = sheet or xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    # detect month columns by scanning top rows
    month_positions = _detect_month_positions(df, months)

    # group columns per month (contiguous from month pos to next month pos)
    sorted_months = sorted(month_positions.items(), key=lambda x: x[1])
    month_ranges = {}
    for idx, (m, pos) in enumerate(sorted_months):
        start = pos  # days may start in the same column as the month header
        if idx + 1 < len(sorted_months):
            end = sorted_months[idx + 1][1]
        else:
            end = df.shape[1]
        month_ranges[m] = (start, end)

    # detect day row (row which lists numbers 1..31)
    day_row = _detect_day_row(df)
    if day_row is None:
        raise ValueError('Could not detect day header row')

    # find employee and email column indices in top rows
    emp_col_idx = _find_in_top_rows(df, emp_col_name)
    email_col_idx = _find_in_top_rows(df, email_col_name)
    if emp_col_idx is None or email_col_idx is None:
        raise ValueError('Employee or email column header not found in top rows')

    # data rows start after header area: choose start = max(day_row, max month header row for months) + 1
    max_month_row = 0
    for c in month_positions.values():
        # find the row where the month string occurs for this column
        for r in range(0, min(10, df.shape[0])):
            if pd.isna(df.iat[r, c]):
                continue
            if str(df.iat[r, c]).strip().lower() in [m.lower() for m in months]:
                max_month_row = max(max_month_row, r)
                break

    data_start = max(max_month_row, day_row) + 1

    results = []
    for r in range(data_start, df.shape[0]):
        raw_emp = df.iat[r, emp_col_idx]
        if pd.isna(raw_emp):
            continue
        employee = str(raw_emp).strip()
        if not employee:
            continue
        raw_email = df.iat[r, email_col_idx]
        email = str(raw_email).strip() if not pd.isna(raw_email) else ''

        vacations = []
        for m in months:
            start, end = month_ranges[m]
            month_number = months.index(m) + 1
            for c in range(start, end):
                # read day number from day_row at column c
                day_cell = df.iat[day_row, c]
                try:
                    day = int(day_cell)
                except Exception:
                    # if day header not numeric, skip
                    continue

                # check employee cell at r,c
                cell = df.iat[r, c]
                if pd.isna(cell):
                    continue
                # any non-empty cell counts as vacation day
                vacations.append(f"{int(year):04d}-{month_number:02d}-{int(day):02d}")

        results.append({
            'employee': employee,
            'email': email,
            'vacations': sorted(sorted(set(vacations)))
        })

    return results
