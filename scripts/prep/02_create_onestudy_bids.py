import os, shutil, argparse
from glob import glob
from bids.grabbids import BIDSLayout
import pandas as pd
import json
import numpy
from collections import OrderedDict


def mkdir(p):
    if not os.path.exists(p):
        os.makedirs(p)


def to_tsv(df, filename, header=True):
    df.to_csv(filename, sep="\t", index=False, header=header)


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
    parser.add_argument('root_dir', help='root_dir {expects root_dir}/dl folder and will write to '
                                         '{expects root_dir}/bids')
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

    for site_orig_name in sites:
        site = site_orig_name.replace("_", "")  # without _
        site_dir = os.path.join(dl_dir, site_orig_name)

        layout = BIDSLayout(site_dir)
        df = layout.as_data_frame()
        #
        # import pdb
        # pdb.set_trace()
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
                    source_file = layout.get_bval(file.path)
                    dest_file = get_new_file(source_file, site_dir, out_dir, file.subject, site)
                    shutil.copyfile(source_file, dest_file)

                    source_file = layout.get_bvec(file.path)
                    dest_file = get_new_file(source_file, site_dir, out_dir, file.subject, site)
                    shutil.copyfile(source_file, dest_file)

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
                    raise FileNotFoundError(json_source_file)

                # update json with orig path
                add_info_to_json(json_dest_file, {"OrigFile": file.path})


            elif "_sessions.tsv" in dest_file:
                ses = read_tsv(dest_file)
                ses["participant_id"] = site + "x" + ses["participant_id"]
                to_tsv(ses, dest_file)
            else:
                raise Exception(file.path)