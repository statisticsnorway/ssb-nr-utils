"Fame utility functions"

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd





def get_fame(params:dict[str,str], famedb:str="sl-fame-1.ssb.no") -> None:
    """Function to get fame data as a csv file output.

    Args:
        params: Dict with paramets for famedb, from and to date, and output_path.
        famedb: str for fame server.

    Returns:
        None
    """

    MODULE_DIR = Path(__file__).resolve().parent

    
    
    prog_path = Path(MODULE_DIR / "fame_prog" / "lag_csv_template.inp")
    original_script = prog_path.read_text()
    script = _inject_params(original_script, params)

    with tempfile.TemporaryDirectory(prefix="fame_prog_nr_utils") as tmp:

        tmpdir = Path(tmp)
        spec_path = tmpdir / "run.inp"
        spec_path.write_text(script) 

        res = os.system(f"ssh {famedb} fame <{str(spec_path)}>>/dev/null")




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


def _build_series_lines(data: pd.DataFrame, db_alias: str) -> str:
    """Build SERIES + channel-assignment lines for each column of a wide DataFrame.

    Args:
        data: wide DataFrame, datetime index (one row per period, no gaps,
              sorted ascending), one column per series (column name = FAME
              object name).
        db_alias: the channel alias used in the OPEN ... AS clause of the
                  .inp template -- must match exactly (FAME only allows the
                  alias to be set once per script).
    """
    lines = []
    for name in data.columns:
        values = ", ".join(f"{v:g}" for v in data[name])
        lines.append(f"series !{name} = {values}")
        lines.append(f"{db_alias}.{name} = {name}")
    return "\n".join(lines)


def _remote_db_exists(db_path: str, famedb: str) -> bool:
    """Check whether the FAME database file already exists on the remote server.

    Args:
        db_path: path to the FAME database file (without or with .db extension --
                 adjust the test path below to match what FAME actually names
                 the file on disk).
        famedb: FAME server hostname.
    Returns:
        True if the file exists on famedb, False otherwise.
    """
    result = subprocess.run(
        ["ssh", famedb, f"test -f {db_path}"],
        capture_output=True,
    )
    return result.returncode == 0


def put_fame(data: pd.DataFrame, freq: str, db_path: str, famedb: str, db_alias: str = "mydb") -> None:
    """Write a range of series data to a FAME database from a wide DataFrame.

    If the database already exists, opens it with ACCESS UPDATE so existing
    data outside the given range/series is left untouched. If it does not
    exist, creates it fresh with ACCESS OVERWRITE.

    Args:
        data: wide DataFrame, datetime index, one column per series.
        freq: FAME frequency keyword, e.g. "monthly".
        db_path: path to the FAME database file.
        db_alias: channel alias to use for the OPEN ... AS clause. Must be a
                  valid FAME identifier; FAME allows this to be set once only
                  per script.
        famedb: FAME server hostname.
    Returns:
        None
    """
    MODULE_DIR = Path(__file__).resolve().parent
    prog_path = Path(MODULE_DIR / "fame_prog" / "skriv_data_template.inp")
    original_script = prog_path.read_text()

    from_date = _fame_period(data.index[0], freq)
    to_date = _fame_period(data.index[-1], freq)

    access_mode = "update" if _remote_db_exists(db_path, famedb) else "overwrite"

    params = {
        "DB_PATH": db_path,
        "ACCESS_MODE": access_mode,
        "FREQ": freq,
        "FROM_DATE": from_date,
        "TO_DATE": to_date,
        "MYDB": db_alias,
        "SERIES_LINES": _build_series_lines(data, db_alias),
    }
    script = _inject_params(original_script, params)

    with tempfile.TemporaryDirectory(prefix="fame_prog_nr_utils") as tmp:
        tmpdir = Path(tmp)
        spec_path = tmpdir / "run.inp"
        spec_path.write_text(script)
        print(script)
        res = os.system(f"ssh {famedb} fame <{str(spec_path)}>>/dev/null")



def main():

    df = pd.DataFrame(
        data ={
        "test.1.vr":[800,900,9000],
        # "test.2.vl":[10,11,12]
        },
        index=pd.date_range("2026-05-01","2026-07-01",freq="MS")
    )

    print(df)

    put_fame(data=df, freq="monthly", db_path="/ssb/bruker/ged/my_first_db.db", famedb="sl-fame-p1", db_alias="ged_test_db")



if __name__=="__main__":
    main()



