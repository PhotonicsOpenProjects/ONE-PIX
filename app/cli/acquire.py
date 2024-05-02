import argparse
import json
import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Acquisition import Acquisition

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
        description="ONE-PIX acquisition command line script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-m", "--imaging_method", type=str, help="imaging_method")
    parser.add_argument("-r", "--spatial_res", type=int, help="Spatial resolution")
    parser.add_argument(
        "-t",
        "--integration_time_ms",
        type=int,
        help="Spectrometer integration time (ms)",
    )
    parser.add_argument("-l", "--wl_lim", type=list, help="Wavelengths range")
    parser.add_argument("-H", "--height", type=int, help="Projection window height")
    parser.add_argument("-W", "--width", type=int, help="Projection window height")
    parser.add_argument(
        "-s",
        "--spectro_scans2avg",
        type=int,
        help="Number of spectral measure per pattern",
    )

    args = parser.parse_args()

    check_args(args)

    print("Acquisition begginning")
    print("-" * 100)
    acq = Acquisition()
    acq.thread_acquisition()
    acq.save_raw_data()

    print("Acqusition completed !")
    print("-" * 100)
    print("\n")


if __name__ == "__main__":
    main()
