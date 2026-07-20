import os
import pandas as pd
import re
import subprocess
import tempfile
from pathlib import Path


params = {
    "TARGET_DB": "/ssb/stamme02/nasjregn/mnr_hr2024/sesongjust/famedb/mnru.db",
    "START_DATE": "2016:1",
    "END_DATE":   "2026:3",
    "OUTPUT_FILE": "/ssb/bruker/ged/nr_utils_test.csv",
}




def _inject_params(script, params):

    for key, value in params.items():
        script = script.replace(f"<<{key}>>", value)
    return script



def get_fame(params,famedb:str="sl-fame-1.ssb.no"):


    prog_path = Path("src/nr_utils/fame/fame_prog/lag_csv_template.inp")
    original_script = prog_path.read_text()
    script = _inject_params(original_script, params)

    with tempfile.TemporaryDirectory(prefix="fame_prog_nr_utils") as tmp:


        tmpdir = Path(tmp)
        spec_path = tmpdir / "run.inp"
        spec_path.write_text(script) 


        res = os.system(f"ssh {famedb} fame <{str(spec_path)}>>/dev/null")

        
        if res != 0:
            raise OSError('Noe gikk galt')



def main():

    get_fame(famedb="sl-fame-1.ssb.no",params=params)



if __name__=="__main__":

    main()