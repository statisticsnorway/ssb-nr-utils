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

    print("returncode:", result.returncode)
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)

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


def _call_x13_from_df(df: pd.DataFrame, spec_folder:str, out_prefix:str,x13_bin:str) -> pd.DataFrame:


    all_series = {}
    
    for col in df.columns:

        spec_path = Path(f"{spec_folder}/{col}.spc")
        original_text = spec_path.read_text()

        pd_series = df[col]

        try:
            modified_text = _insert_data(original_text, _build_data_line(pd_series))
            spec_path.write_text(modified_text)
    
            
            _call_x13(spec=str(spec_path)[:-4],out_prefix=f"{out_prefix}/{col}", x13_bin=x13_bin)
    
        finally:
            spec_path.write_text(original_text)
        
        
        all_series[f"{col}_seasadj"] = result["seasadj"]
        all_series[f"{col}_trend"] = result["trend"]
        all_series[f"{col}_irregular"] = result["irregular"]

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
    
            _call_x13_from_df(df=df, spec_folder=spec_folder,out_prefix=out_prefix,x13_bin=x13_bin)
            
    else:
        _call_x13_from_df(df=df, spec_folder=spec_folder,out_prefix=f"{outdir}",x13_bin=x13_bin)


    return df_seasonal






def main():


    df = pd.DataFrame(
        {
            "test_series":[
    117.6321, 110.6025, 104.8950, 96.9695, 86.7018, 78.8318, 78.0121, 82.1642,
    96.5159, 102.3555, 113.5752, 123.6357, 119.9755, 115.5377, 107.2848, 95.9743,
    93.2637, 86.0345, 84.4102, 92.9304, 106.4474, 113.0026, 120.1865, 124.5225,
    122.7044, 114.2969, 109.8878, 99.4937, 101.2351, 94.5265, 93.4225, 97.1657,
    111.0839, 117.6951, 125.3150, 136.3268, 129.2745, 124.0235, 117.0190, 106.7959,
    106.4826, 101.6068, 96.4737, 102.2382, 115.4476, 126.5961, 135.7104, 136.4260,
    138.5409, 132.2199, 125.7574, 117.4867, 110.9020, 109.4147, 103.4894, 110.1698,
    125.0512, 135.3186, 142.0268, 148.3604, 139.8691, 132.6253, 129.6352, 122.6646,
    120.3349, 112.2253, 111.9255, 114.2364, 132.5346, 140.4152, 145.2409, 148.9917,
    140.8448, 139.6680, 132.5025, 126.3962, 124.0231, 115.3350, 112.0360, 116.0306,
    132.4485, 137.1384, 144.3527, 152.8708, 146.5735, 142.9108, 130.1298, 126.7866,
    123.9890, 119.3467, 119.5382, 118.7328, 133.9700, 144.5159, 144.7231, 154.1961,
    146.2567, 141.1788, 134.2238, 128.9506, 125.0671, 119.1353, 114.0103, 120.9332,
    131.4628, 141.9426, 147.6159, 153.4491, 152.5089, 137.9397, 136.1164, 130.0892,
    120.8811, 112.1872, 111.8570, 116.4022, 130.0293, 143.2727, 149.5855, 153.8786,
    150.4865, 150.5271, 137.5098, 130.0893, 132.0464, 124.9229, 122.7883,
]
        }
    )

    run_x13_from_df(df= df, spec_folder=str(MODULE_DIR),outdir=str(MODULE_DIR / "out"))

    run_x13(spec=str(MODULE_DIR /"series"),outdir=str(MODULE_DIR / "out"))

if __name__=="__main__":

    main()