#!/usr/bin/env python

import os, shutil, argparse
from glob import glob
from bids.grabbids import BIDSLayout
import pandas as pd
import json
import numpy
from collections import OrderedDict
from utils import run


def mkdir(p):
    if not os.path.exists(p):
        os.makedirs(p)


def to_tsv(df, filename, header=True):
    df.to_csv(filename, sep="\t", index=False, header=header, na_rep="n/a")


def read_tsv(filename):
    return pd.read_csv(filename, sep="\t", dtype={"participant_id": str}, na_values=["#"])


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('root_dir', help='root_dir expects {root_dir}/dl folder and will write to '
                                         '{root_dir}/bids')
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root_dir)

    dl_dir = os.path.join(root_dir, "dl")
    out_dir = os.path.join(root_dir, "bids")
    mkdir(out_dir)

    descr_file = os.path.join(out_dir, "dataset_description.json")
    info = {"Name": "CORR", "BIDSVersion": "1.0.2"}
    add_info_to_json(descr_file, info, create_new=True)

    os.chdir(dl_dir)
    sites = glob("*")

    participants = pd.DataFrame([])
    participants_missing = pd.DataFrame([])

    for site_orig_name in sites:
        site = site_orig_name.replace("_", "")  # without _
        print("Converting {}".format(site))
        site_dir = os.path.join(dl_dir, site_orig_name)

        # merge participants files
        participants_file = os.path.join(site_dir, "participants.tsv")
        if os.path.isfile(participants_file):
            participants_site = read_tsv(participants_file)
            participants_site["site"] = site
            participants_site["orig_participant_id"] = participants_site["participant_id"]
            participants_site["participant_id"] = participants_site["site"] + "x" + participants_site["orig_participant_id"]
            participants = pd.concat((participants, participants_site))
        else:
            participants_site = pd.DataFrame({"site": [site], "participant_id": "participants file missing"})
            participants_missing = pd.concat((participants_missing, participants_site))


        # get file df
        layout = BIDSLayout(site_dir)
        df = layout.as_data_frame()
        copy_files = df[df.path.str.endswith(".nii.gz") | df.path.str.endswith("_sessions.tsv")]


        def get_new_file(source_file, site_dir, out_dir, old_subject, site):
            new_file = os.path.relpath(source_file, site_dir).replace(old_subject, site + "x" + old_subject)
            dest_file = os.path.join(out_dir, new_file)
            dest_dir = os.path.dirname(dest_file)
            mkdir(dest_dir)
            return dest_file


        for r in copy_files.iterrows():
            file = r[1]

            source_file = file.path
            dest_file = get_new_file(source_file, site_dir, out_dir, file.subject, site)

            if os.path.isfile(dest_file) and dest_file.endswith(".nii.gz"):
                print("{} found. Do nothing.".format(dest_file))
            else:
                print("copy {} --> {}".format(source_file, dest_file))
                shutil.copyfile(source_file, dest_file)

            # deal with additional files files
            if ".nii.gz" in file.path:
                # bvec/bvals
                if file.modality == "dwi":
                    extra_source_file = layout.get_bval(file.path)
                    extra_dest_file = get_new_file(extra_source_file, site_dir, out_dir, file.subject, site)
                    shutil.copyfile(extra_source_file, extra_dest_file)

                    extra_source_file = layout.get_bvec(file.path)
                    extra_dest_file = get_new_file(extra_source_file, site_dir, out_dir, file.subject, site)
                    shutil.copyfile(extra_source_file, extra_dest_file)

                # copy jsons
                task_str = "task-{}_".format(file.task) if file.task and not pd.isnull(file.task) else ""
                acq_str = "acq-{}_".format(file.acquisition) if "acquisition" in file and file.acquisition and not \
                    pd.isnull(file.acquisition) else ""

                # fix for nki:
                if task_str == "task-breathhold_":
                    task_str = "task-breathholding_"

                json_source_file = os.path.join(site_dir, "{}{}{}.json".format(task_str, acq_str, file.type))
                if os.path.isfile(json_source_file):
                    json_dest_file = dest_file.strip(".nii.gz") + ".json"
                    shutil.copyfile(json_source_file, json_dest_file)
                else:
                    json_source_file = os.path.join(site_dir, "ses-{}_{}{}{}.json".format(file.session, task_str,
                                                                                          acq_str, file.type))
                    if os.path.isfile(json_source_file):
                        json_dest_file = dest_file.strip(".nii.gz") + ".json"
                        shutil.copyfile(json_source_file, json_dest_file)
                    else:
                        raise FileNotFoundError(json_source_file)

                # update json with orig path
                add_info_to_json(json_dest_file, {"OrigFile": file.path})


            elif "_sessions.tsv" in dest_file:
                ses = read_tsv(dest_file)
                ses["participant_id"] = site + "x" + ses["participant_id"]
                to_tsv(ses, dest_file)
            else:
                raise Exception(file.path)

    # save participants
    to_tsv(participants, os.path.join(out_dir, "participants_all.tsv"))
    mri_participants = [os.path.basename(s) for s in sorted(glob(os.path.join(out_dir, "sub-*")))]
    mri_participants = [s.split("-")[-1] for s in mri_participants]
    participants = participants[participants.participant_id.isin(mri_participants)]
    to_tsv(participants, os.path.join(out_dir, "participants_mri.tsv"))
    to_tsv(participants_missing, os.path.join(out_dir, "participants_missing.tsv"))

    run("bids-validator {}".format(out_dir))

    # check nii file counts
    n_orig = len(glob(os.path.join(dl_dir, "*/sub-*/ses-*/*/*nii.gz")))
    n_bids = len(glob(os.path.join(out_dir, "sub-*/ses-*/*/*nii.gz")))
    print("Checking N files", n_orig, n_bids)
    assert n_orig == n_bids, "File counts not equal"

    print("Converted {} sites. Everything seems fine.".format(len(sites)))