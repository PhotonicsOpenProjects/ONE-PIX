import argparse
import json
import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Reconstruction import Reconstruction

acquisition_json_path = "../../conf/acquisition_parameters.json"


def read_json():
    with open(acquisition_json_path, "r") as file:
        acquisition_json_object = json.load(file)
    return acquisition_json_object


def write_json(acquisition_json_object):
    with open(acquisition_json_path, "w") as file:
        json.dump(acquisition_json_object, file, indent=4)


def check_args(args):
    acquisition_json_object = read_json()
    print("\n")
    for arg in vars(args):
        value = getattr(args, arg)
        if value is None:
            # change argparser value per json value
            print("-" * 100)
            print(
                f"{arg} not specified by user. Default value {acquisition_json_object[arg]} taken from conf/acquisition_parameters.json"
            )
        else:
            acquisition_json_object[f"{arg}"] = value

    print("-" * 100)
    print("\n")

    write_json(acquisition_json_object)


def main():
    parser = argparse.ArgumentParser(
        description="ONE-PIX reconstruction command line script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-n", "--filename", type=str, help="filename to save a reconstructed data")
    parser.add_argument("-p", "--save_path", type=int, help="save path ")
   

    args = parser.parse_args()

    #check_args(args)

    print("ONE-PIX reconstruction begginning")
    print("-" * 100)
    rec = Reconstruction()
    rec.data_reconstruction()
    rec.save_reconstructed_image(args.filename,args.save_path)

    print("reconstruction completed !")
    print("-" * 100)
    print("\n")


if __name__ == "__main__":
    main()
