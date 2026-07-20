"Fame utility functions"

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd


def _inject_params(script:str, params:dict[str,str]) -> str:
    """Function that puts in params in str obj of fame script."""
    for key, value in params.items():
        script = script.replace(f"<<{key}>>", value)
    return script



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