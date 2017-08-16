import json
import os
import subprocess
from collections import OrderedDict
from subprocess import Popen, PIPE

import numpy
import pandas as pd


def run(command, env={}, ignore_errors=False):
    merged_env = os.environ
    merged_env.update(env)
    # DEBUG env triggers freesurfer to produce gigabytes of files
    merged_env.pop('DEBUG', None)
    process = Popen(command, stdout=PIPE, stderr=subprocess.STDOUT, shell=True, env=merged_env)
    while True:
        line = process.stdout.readline()
        line = str(line, 'utf-8')[:-1]
        print(line)
        if line == '' and process.poll() != None:
            break
    if process.returncode != 0 and not ignore_errors:
        raise Exception("Non zero return code: %d" % process.returncode)


def mkdir(p):
    if not os.path.exists(p):
        os.makedirs(p)


def to_tsv(df, filename, header=True):
    df.to_csv(filename, sep="\t", index=False, header=header, na_rep="n/a")


def read_tsv(filename, na_values=["#"]):
    return pd.read_csv(filename, sep="\t", dtype={"participant_id": str}, na_values=na_values)


def get_json(bids_file):
    with open(bids_file) as fi:
        bids_data = json.load(fi)
    return bids_data


def add_info_to_json(bids_file, new_info, create_new=False):
    # if create_new=True: if file does not exist, file is created and new_info is written out
    if os.path.exists(bids_file):
        bids_data = get_json(bids_file)
    elif (not os.path.exists(bids_file)) and create_new:
        bids_data = {}
    else:
        raise FileNotFoundError("%s does not exist. Something migth be wrong. If a file should create, "
                                "use create_new=True " % bids_file)

    for k, v in new_info.items():
        if isinstance(v, numpy.ndarray):
            new_info[k] = v.tolist()
    bids_data.update(new_info)

    with open(bids_file, "w") as fi:
        json.dump(OrderedDict(sorted(bids_data.items())), fi, indent=4)