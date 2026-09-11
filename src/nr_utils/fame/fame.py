"""Fame utility functions"""

import subprocess
import tempfile
from pathlib import Path
import pandas as pd


def _run_fame_script(script: str, famedb: str) -> None:
    with tempfile.TemporaryDirectory(prefix="fame_prog_nr_utils") as tmp:
        spec_path = Path(tmp) / "run.inp"
        spec_path.write_text(script)

        try:
            with open(spec_path, "r") as spec_file:
                result = subprocess.run(
                    ["ssh", famedb, "fame"],
                    stdin=spec_file,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except OSError as e:
            # ssh binary missing, permissions issue, etc.
            raise RuntimeError(f"Failed to launch ssh: {e}") from e

        if result.returncode != 0:
            raise RuntimeError(
                f"ssh/fame failed (exit code {result.returncode}): {result.stderr.strip()}"
            )


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


# def _assert_no_gaps(data: pd.DataFrame) -> None:
#     """Guard against silent value-list misalignment from a gapped index."""
#     expected = pd.date_range(
#         data.index[0], data.index[-1], freq=data.index.freq or "MS"
#     )
#     assert data.index.equals(
#         expected
#     ), "gaps detected in data.index -- would misalign value-list"


def _create_series_lines(
    data: pd.DataFrame, db_alias: str, precision: bool = True
) -> str:
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


def create_fame_db(
    data: pd.DataFrame,
    freq: str,
    start_date: str,
    end_date: str,
    db_path: str,
    db_alias: str = "mydb",
    famedb: str = "sl-fame-p1",
    precision: bool = True,
) -> None:
    """Create a brand-new FAME database and populate it with the given series.

    WARNING: uses ACCESS OVERWRITE, which replaces any existing file at
    db_path entirely. Call this only for a genuinely new database -- use
    update_fame_db for writing to one that already exists.

    Args:
        data: wide DataFrame, datetime index, one column per series.
        freq: FAME frequency keyword, e.g. "monthly".
        start_date: Date str for from date, format YYYY:MM.
        end_date: Date str for to date.
        db_path: path to the FAME database file to create.
        db_alias: channel alias for the OPEN ... AS clause.
        famedb: FAME server hostname.
        precision: type used for the newly created series.
    Returns:
        None
    """
    # _assert_no_gaps(data)
    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (MODULE_DIR / "fame_prog" / "opprett_db_template.inp").read_text()

    params = {
        "DB_PATH": db_path,
        "FREQ": freq,
        "FROM_DATE": start_date,
        "TO_DATE": end_date,
        "MYDB": db_alias,
        "SERIES_LINES": _create_series_lines(data, db_alias, precision),
    }
    _run_fame_script(_inject_params(original_script, params), famedb)


def update_fame_db(
    data: pd.DataFrame,
    freq: str,
    start_date: str,
    end_date: str,
    db_path: str,
    db_alias: str = "mydb",
    famedb: str = "sl-fame-1.ssb.no",
) -> None:
    """Write a range of values into an existing FAME database's existing series.

    Uses ACCESS SHARED, so the write can proceed alongside a concurrent
    reader. Fails against series that don't already exist -- this function
    assumes a fixed, known set of series (see create_fame_db for new ones).

    Args:
        data: wide DataFrame, datetime index, one column per series.
        freq: FAME frequency keyword, e.g. "monthly".
        start_date: Date str for from date, format YYYY:MM.
        end_date: Date str for to date.
        db_path: path to the existing FAME database file.
        db_alias: channel alias for the OPEN ... AS clause.
        famedb: FAME server hostname.
    Returns:
        None
    """
    # _assert_no_gaps(data)
    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (
        MODULE_DIR / "fame_prog" / "oppdater_db_template.inp"
    ).read_text()

    params = {
        "DB_PATH": db_path,
        "FREQ": freq,
        "FROM_DATE": start_date,
        "TO_DATE": end_date,
        "MYDB": db_alias,
        "SERIES_LINES": _update_series_lines(data, db_alias),
    }
    _run_fame_script(_inject_params(original_script, params), famedb)


def get_fame(
    db_path: str,
    csv_path: str,
    freq: str,
    start_date: str,
    end_date: str,
    rounding: str = "auto",
    famedb: str = "sl-fame-p1",
) -> None:
    """Read data from a FAME database and write it out to a CSV file.

    Args:
        db_path: Path to the existing FAME database file.
        csv_path: Path to store csv file.
        freq: FAME frequency keyword, e.g. "monthly".
        start_date: Date str for from date, format YYYY:MM.
        end_date: Date str for to date.
        rounding: Number of decimals, eiher auto or number as str.
        famedb: FAME server hostname.
    Returns:
        None
    """
    DATE_IMAGE_BY_FREQ = {
        "annual": "<year>",
        "quarterly": "<year>Q<p>",
        "monthly": "<year>-<mz>",
        "daily": "<year>-<mz>-<dz>",
    }

    params = {
        "TARGET_DB": db_path,
        "FREQUENCY": freq,
        "START_DATE": start_date,
        "END_DATE": end_date,
        "OUTPUT_FILE": csv_path,
        "DECIMAL": rounding,
        "DATE_IMAGE": DATE_IMAGE_BY_FREQ[freq],
    }

    MODULE_DIR = Path(__file__).resolve().parent
    original_script = (MODULE_DIR / "fame_prog" / "lag_csv_template.inp").read_text()
    script = _inject_params(original_script, params)

    # print(script)
    
    _run_fame_script(script, famedb)



# def main():
#     print("Test ny fame funksjonalitet!")

#     df_annual = pd.DataFrame({
#         "test.1.vl": [100.5, 102.3, 104.1, 106.0],
#         # "date": ["2023", "2024", "2025", "2026"],
#     })
    
#     df_quarterly = pd.DataFrame({
#         "test.1.vl": [100.5, 101.2, 102.0, 102.8, 103.5],
#         # "date": ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"],
#     })
    
#     df_monthly = pd.DataFrame({
#         "test.1.vl": [100.5, 100.8, 101.1, 101.4, 101.9, 102.2],
#         # "date": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
#     })

#     df_daily = pd.DataFrame({
#         "test.1.vl": [100.5, 100.6, 100.4, 100.9, 101.1, 101.0, 101.3, 101.5, 101.4, 101.8],
#         # "date": [
#         #     "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05",
#         #     "2026-06-06", "2026-06-07", "2026-06-08", "2026-06-09", "2026-06-10",
#         # ],
#     })

#     print("Skriv inn brukernavn:")
#     user = input()
#     root_path = f"/ssb/bruker/{user}"

#     test_cases = [
#         ("annual", df_annual, "2023", "2026"),
#         ("quarterly", df_quarterly, "2025:1", "2026:1"),
#         ("monthly", df_monthly, "2026:1", "2026:6"),
#         ("daily", df_daily, "2026:1", "2026:10"),
#     ]

#     for freq, df, start_date, end_date in test_cases:
#         db_path = f"{root_path}/test_db_{freq}.db"
#         csv_path = f"{root_path}/test_out_{freq}.csv"
#         print(df)
#         # 1. write test data into a FAME db
#         create_fame_db(
#             data=df,
#             freq=freq,
#             start_date=start_date,
#             end_date=end_date,
#             db_path=db_path,
#         )
    
#         # 2. read it back out via your existing get_fame
#         get_fame(
#             db_path=db_path,
#             csv_path=csv_path,
#             freq=freq,
#             start_date=start_date,
#             end_date=end_date,
#         )
    
#         # 3. compare
#         result = pd.read_csv(csv_path, sep=";")
#         print(f"--- {freq} ---")
#         print(result)
    
# if __name__ == "__main__":
#     main()