"""Sesonjustering funksjoner for MNR

Bruker x13 fra US Census https://www.census.gov/data/software/x13as.X-13ARIMA-SEATS.html#accordion-bfdec081de-item-fb93ad60cf

Programmet kjører fra Linux, men vi bruker python til å orkestrere kjøringen og sende inn data.
"""
import pandas as pd

import subprocess
import tempfile
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



# def main():

#     run_x13(spec=str(MODULE_DIR /"series"),outdir=str(MODULE_DIR / "out"))

# if __name__=="__main__":

#     main()