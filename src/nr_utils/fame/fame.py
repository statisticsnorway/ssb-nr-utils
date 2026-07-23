"""Fame utility functions"""
import os
import re
import subprocess
import tempfile
from pathlib import Path
import pandas as pd


def _inject_params(script: str, params: dict[str, str]) -> str:
    """Function that puts in params in str obj of fame script."""
    for key, value in params.items():
        script = script.replace(f"<<{key}>>", value)
    return script


def _fame_period(date: pd.Timestamp, freq: str) -> str:
    """Format a timestamp as a FAME date literal for the given frequency.

    NOTE: "<year>:<month>" confirmed working for monthly via a tested .inp
    file. Other frequencies below are still unverified -- test before use.
    """
    if freq == "monthly":
        return f"{date.year}:{date.month}"
    if freq == "quarterly":
        return f"{date.year}:{date.quarter}"
    if freq == "annual":
        return f"{date.year}"
    if freq == "daily":
        return f"{date.year}:{date.month}:{date.day}"
    raise ValueError(f"Unhandled frequency: {freq}")


def _assert_no_gaps(data: pd.DataFrame) -> None:
    """Guard against silent value-list misalignment from a gapped index."""
    expected = pd.date_range(data.index[0], data.index[-1], freq=data.index.freq or "MS")
    assert data.index.equals(expected), "gaps detected in data.index -- would misalign value-list"


def _create_series_lines(data: pd.DataFrame, db_alias: str, precision: bool = True) -> str:
    """Build one SERIES statement per column, creating and populating each object.

    Args:
        data: wide DataFrame, datetime index (one row per period, no gaps,
              sorted ascending), one column per series (column name = FAME
              object name).
        db_alias: channel alias from the OPEN ... AS clause.
        precision: use :precision (15 sig. figures) rather than :numeric
                   (7 sig. figures).
    """
    type_clause = ":precision" if precision else ":numeric"
    lines = []
    for name in data.columns:
        values = ", ".join(f"{v:g}" for v in data[name])
        lines.append(f"series {name} {type_clause} indexed by date = {values}")
    return "\n".join(lines)


def _update_series_lines(data: pd.DataFrame, db_alias: str) -> str:
    """Build one UPDATE statement per column, writing into existing objects.

    Args:
        data: wide DataFrame, datetime index (one row per period, no gaps,
              sorted ascending), one column per series (column name = FAME
              object name).
        db_alias: channel alias from the OPEN ... AS clause.
    """
    lines = []
    for name in data.columns:
        values = ", ".join(f"{v:g}" for v in data[name])
        lines.append(f"update {name} = {values}")
    return "\n".join(lines)


def _run_fame_script(script: str, famedb: str) -> None:
    with tempfile.TemporaryDirectory(prefix="fame_prog_nr_utils") as tmp:
        spec_path = Path(tmp) / "run.inp"
        spec_path.write_text(script)
        res = os.system(f"ssh {famedb} fame <{str(spec_path)}>>/dev/null")


def create_fame_db(data: pd.DataFrame, freq: str, db_path: str, db_alias: str = "mydb",
                    famedb: str = "sl-fame-1.ssb.no", precision: bool = True) -> None:
    """Create a brand-new FAME database and populate it with the given series.

    WARNING: uses ACCESS OVERWRITE, which replaces any existing file at
    db_path entirely. Call this only for a genuinely new database -- use
    update_fame_db for writing to one that already exists.

    Args:
        data: wide DataFrame, datetime index, one column per series.
        freq: FAME frequency keyword, e.g. "monthly".
        db_path: path to the FAME database file to create.
        db_alias: channel alias for the OPEN ... AS clause.
        famedb: FAME server hostname.
        precision: type used for the newly created series.
    Returns:
        None
    """
    _assert_no_gaps(data)
    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (MODULE_DIR / "fame_prog" / "opprett_db_template.inp").read_text()

    params = {
        "DB_PATH": db_path,
        "FREQ": freq,
        "FROM_DATE": _fame_period(data.index[0], freq),
        "TO_DATE": _fame_period(data.index[-1], freq),
        "MYDB": db_alias,
        "SERIES_LINES": _create_series_lines(data, db_alias, precision),
    }
    _run_fame_script(_inject_params(original_script, params), famedb)


def update_fame_db(data: pd.DataFrame, freq: str, db_path: str, db_alias: str = "mydb",
                    famedb: str = "sl-fame-1.ssb.no") -> None:
    """Write a range of values into an existing FAME database's existing series.

    Uses ACCESS SHARED, so the write can proceed alongside a concurrent
    reader. Fails against series that don't already exist -- this function
    assumes a fixed, known set of series (see create_fame_db for new ones).

    Args:
        data: wide DataFrame, datetime index, one column per series.
        freq: FAME frequency keyword, e.g. "monthly".
        db_path: path to the existing FAME database file.
        db_alias: channel alias for the OPEN ... AS clause.
        famedb: FAME server hostname.
    Returns:
        None
    """
    _assert_no_gaps(data)
    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (MODULE_DIR / "fame_prog" / "oppdater_db_template.inp").read_text()

    params = {
        "DB_PATH": db_path,
        "FREQ": freq,
        "FROM_DATE": _fame_period(data.index[0], freq),
        "TO_DATE": _fame_period(data.index[-1], freq),
        "MYDB": db_alias,
        "SERIES_LINES": _update_series_lines(data, db_alias),
    }
    _run_fame_script(_inject_params(original_script, params), famedb)


def get_fame(params: dict[str, str], famedb: str = "sl-fame-1.ssb.no") -> None:
    """Read data from a FAME database and write it out to a CSV file.

    Args:
        params: dict with parameters for famedb, from and to date, and output_path
                (whatever placeholders lag_csv_template.inp expects).
        famedb: FAME server hostname.
    Returns:
        None
    """
    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (MODULE_DIR / "fame_prog" / "lag_csv_template.inp").read_text()
    script = _inject_params(original_script, params)
    _run_fame_script(script, famedb)



def main():

    df = pd.DataFrame(
        data = {
            "test.1.vr":[900,1000,1100],
            "test.2.vl":[9,10,11]
        },
        index=pd.date_range(start="2026-01-01",end="2026-03-01",freq="MS")
    )

    create_fame_db(
        data=df,
        freq="monthly",
        db_path="/ssb/bruker/ged/my_first_db.db",
        db_alias="mydb"
    )

    get_fame(
        params = {
            "TARGET_DB": "/ssb/bruker/ged/my_first_db.db",
            "START_DATE": "2026:1",
            "END_DATE":   "2026:3",
            "OUTPUT_FILE": "/ssb/bruker/ged/test_csv.csv"
        }
    )

    df = pd.DataFrame(
        data= {
            "test.1.vr":[900,1000,1100],
            "test.2.vl":[9,10,11]
        },
        index=pd.date_range(start="2026-03-01",end="2026-05-01",freq="MS")
    )

    update_fame_db(
        data=df,
        freq="monthly",
        db_path="/ssb/bruker/ged/my_first_db.db",
        db_alias="mydb"
    )

    get_fame(
        params = {
            "TARGET_DB": "/ssb/bruker/ged/my_first_db.db",
            "START_DATE": "2026:1",
            "END_DATE":   "2026:5",
            "OUTPUT_FILE": "/ssb/bruker/ged/test_csv2.csv"
        }
    )


if __name__=="__main__":
    main()