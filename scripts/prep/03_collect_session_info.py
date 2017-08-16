import pandas as pd
import os, argparse
from glob import glob
from utils import run, mkdir, to_tsv, read_tsv, add_info_to_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('bids_dir', help='bids dir')
    args = parser.parse_args()

    bids_dir = os.path.abspath(args.bids_dir)

    # Load data
    os.chdir(bids_dir)
    subjects = sorted(glob("sub-*"))
    df = pd.DataFrame([])
    for s in subjects:
        print(s)
        site = s.split("x")[0].strip("sub-")
        df_file = os.path.join(bids_dir, s, "{}_sessions.tsv".format(s))
        if os.path.isfile(df_file):
            df_ = read_tsv(df_file,  na_values=["n/a"])
            df_["site"] = site
            df = pd.concat((df, df_))

    to_tsv(df, "session_info.tsv")

