"""Sesonjustering funksjoner for MNR

Bruker x13 fra US Census https://www.census.gov/data/software/x13as.X-13ARIMA-SEATS.html#accordion-bfdec081de-item-fb93ad60cf

Programmet kjører fra Linux, men vi bruker python til å orkestrere kjøringen og sende inn data.
"""
import pandas as pd

import subprocess
import tempfile
import re
from pathlib import Path

# Directory containing this .py file
MODULE_DIR = Path(__file__).resolve().parent

def _call_x13(spec:str,out_prefix:str,x13_bin:str) -> None:
    """Function to call on x13 binary program"""
    result = subprocess.run(
        [str(x13_bin), "-i", spec, "-o", out_prefix],
        capture_output=True,
        text=True
    )

    # print("returncode:", result.returncode)
    # print("STDOUT:\n", result.stdout)
    # print("STDERR:\n", result.stderr)

    if result.returncode != 0:
        print("STDERR:", result.stderr)
        for f in tmp.glob("*.err"):
            print(f.read_text())
        raise RuntimeError("X-13 failed — see output above")


def run_x13(spec: str, series: str = "x13", hmtl: bool = False, outdir: str = None):
    """Function to run the x13 binary file.
    
    Args:
        spec: Path to spec.
        series: name for series.
        html: Bool of wether or not to run the html version, default false.
        outdir: Dir for temp output from the x13 run.
        
    Returns:
        None
    """
    if hmtl:
        x13_bin = MODULE_DIR / "bin" /"x13as_html"
    else:
        x13_bin = MODULE_DIR / "bin" /"x13as"

    if outdir is None:
        with tempfile.TemporaryDirectory(prefix="x13_") as tmpdir:
            tmpdir = Path(tmpdir)
            out_prefix = tmpdir / series
    
            _call_x13(spec=spec,out_prefix=out_prefix,x13_bin=x13_bin)
            
    else:
        _call_x13(spec=spec,out_prefix=f"{outdir}/{series}",x13_bin=x13_bin)



DATA_LINE_PATTERN = re.compile(r"^\s*data\s*=\s*\([^)]*\)\s*\n?", re.IGNORECASE | re.MULTILINE)
SERIES_BLOCK_PATTERN = re.compile(r"(series\s*\{)", re.IGNORECASE)


def _build_data_line(s: pd.Series) -> str:
    values = [str(v) for v in s.dropna().values]
    lines = "\n".join(f"    {v}" for v in values)
    return f"    data = (\n{lines}\n    )"


def _insert_data(spec_text: str, data_line: str) -> str:
    if not SERIES_BLOCK_PATTERN.search(spec_text):
        raise ValueError("No series{ block found in spec file")
    return SERIES_BLOCK_PATTERN.sub(lambda m: f"{m.group(1)}\n{data_line}", spec_text, count=1)


def _compute_start(s: pd.Series) -> str:
    """
    Returns the X-13 start= string (e.g. '2016.1') based on the first
    non-null observation in the series, matching what _build_data_line
    actually sends (since it drops NaNs).
    """
    valid = s.dropna()
    if valid.empty:
        raise ValueError("Series has no valid (non-NaN) observations")

    first_date = pd.to_datetime(valid.index[0])

    return f"{first_date.year}.{first_date.month}"


START_LINE_PATTERN = re.compile(r"^\s*start\s*=\s*\S+\s*\n?", re.IGNORECASE | re.MULTILINE)

def _set_start(spec_text: str, start: str) -> str:
    spec_text = START_LINE_PATTERN.sub("", spec_text)
    return re.sub(
        r"(data\s*=\s*\([^)]*\))",   # <-- single closing paren now, not two
        lambda m: f"{m.group(1)}\n    start = {start}",
        spec_text,
        count=1,
        flags=re.DOTALL,
    )


def _read_saved_series(path: Path) -> pd.Series:
    df = pd.read_csv(
        path,
        sep=r"\s+",
        skiprows=2,           # skip header row + dashed separator
        header=None,
        names=["date", "value"],
        dtype={"date": str},
    )

    # date can be yyyymm (monthly) or yyyyq (quarterly, 5 digits)
    if df["date"].str.len().iloc[0] == 6:
        idx = pd.to_datetime(df["date"], format="%Y%m")
    elif df["date"].str.len().iloc[0] == 5:
        years = df["date"].str[:4].astype(int)
        quarters = df["date"].str[4].astype(int)
        idx = pd.PeriodIndex(
            [f"{y}Q{q}" for y, q in zip(years, quarters)], freq="Q"
        ).to_timestamp()
    else:
        raise ValueError(f"Unrecognized date format in {path}: {df['date'].iloc[0]!r}")

    values = df["value"].astype(float)
    return pd.Series(values.values, index=idx)


def _call_x13_from_df(df: pd.DataFrame, spec_folder:str, out_prefix:str,x13_bin:str) -> pd.DataFrame:


    all_series = {}
    i = 0
    length = len(df.columns)
    
    for col in df.columns:
        try:
            spec_path = Path(f"{spec_folder}/{col}.spc")
            original_text = spec_path.read_text()
        except FileNotFoundError:
            continue

        pd_series = df[col]

        try:
            modified_text = _insert_data(original_text, _build_data_line(pd_series))
            modified_text = _set_start(modified_text, _compute_start(pd_series)) 
            spec_path.write_text(modified_text)
    
            
            _call_x13(spec=str(spec_path)[:-4],out_prefix=f"{out_prefix}/{col}", x13_bin=x13_bin)
    
        finally:
            spec_path.write_text(original_text)
        
        
        all_series[f"{col}.s"] = _read_saved_series(f"{out_prefix}/{col}.d11")
        all_series[f"{col}.t"] = _read_saved_series(f"{out_prefix}/{col}.d12")
        all_series[f"{col}.i"] = _read_saved_series(f"{out_prefix}/{col}.d13")

        i+=1

        if i % 100 == 0:
            print(f"Seasonaly adjusted series {i} of {length}")
        

    return pd.concat(all_series, axis=1)

    
def run_x13_from_df(df: pd.DataFrame, spec_folder: str, series: str = "x13", hmtl: bool = False, outdir: str = None):
    """Function to run the x13 binary file.
    
    Args:
        df: Pandas df with data to adjust.
        spec: Path to spec.
        series: name for series.
        html: Bool of wether or not to run the html version, default false.
        outdir: Dir for temp output from the x13 run.
        
    Returns:
        None
    """
    if hmtl:
        x13_bin = MODULE_DIR / "bin" /"x13as_html"
    else:
        x13_bin = MODULE_DIR / "bin" /"x13as"

    if outdir is None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            out_prefix = tmpdir
    
            df_seasonal = _call_x13_from_df(df=df, spec_folder=spec_folder,out_prefix=out_prefix,x13_bin=x13_bin)
            
    else:
        df_seasonal = _call_x13_from_df(df=df, spec_folder=spec_folder,out_prefix=f"{outdir}",x13_bin=x13_bin)


    return df_seasonal
