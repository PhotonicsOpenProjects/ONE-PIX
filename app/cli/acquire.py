import argparse
import json
from pathlib import Path

from onepix.Acquisition import Acquisition

CONF_DIR = Path(__file__).resolve().parent.parent.parent / "conf"
ACQUISITION_JSON_PATH = CONF_DIR / "acquisition_parameters.json"
HARDWARE_JSON_PATH = CONF_DIR / "hardware_config.json"

# Each CLI flag overrides a value that actually lives in one of two
# different config files - keep track of which, so it's written back
# to the right place instead of silently creating an unused key.
ACQUISITION_ARGS = {
    "imaging_method_name",
    "spatial_res",
    "integration_time_ms",
    "spectro_scans2avg",
}
HARDWARE_ARGS = {"wl_lim", "height", "width"}


def read_json(path):
    with open(path, "r") as file:
        return json.load(file)


def write_json(path, data):
    with open(path, "w") as file:
        json.dump(data, file, indent=4)


def apply_overrides(args):
    acquisition_json = read_json(ACQUISITION_JSON_PATH)
    hardware_json = read_json(HARDWARE_JSON_PATH)

    print("\n")
    for arg in vars(args):
        value = getattr(args, arg)

        if value is None:
            source = ACQUISITION_JSON_PATH if arg in ACQUISITION_ARGS else HARDWARE_JSON_PATH
            default = (acquisition_json if arg in ACQUISITION_ARGS else hardware_json).get(arg)
            print("-" * 100)
            print(f"{arg} not specified by user. Default value {default} taken from {source}")
            continue

        if arg in ACQUISITION_ARGS:
            acquisition_json[arg] = value
        elif arg in HARDWARE_ARGS:
            hardware_json[arg] = value

    print("-" * 100)
    print("\n")

    write_json(ACQUISITION_JSON_PATH, acquisition_json)
    write_json(HARDWARE_JSON_PATH, hardware_json)


def main():
    parser = argparse.ArgumentParser(
        description="ONE-PIX acquisition command line script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-m", "--imaging_method_name", type=str, help="Imaging method name")
    parser.add_argument("-r", "--spatial_res", type=int, help="Spatial resolution")
    parser.add_argument(
        "-t",
        "--integration_time_ms",
        type=float,
        help="Spectrometer integration time (ms)",
    )
    parser.add_argument(
        "-l",
        "--wl_lim",
        type=float,
        nargs=2,
        metavar=("MIN", "MAX"),
        help="Wavelengths range, e.g. -l 350 800",
    )
    parser.add_argument("-H", "--height", type=int, help="Projection window height")
    parser.add_argument("-W", "--width", type=int, help="Projection window width")
    parser.add_argument(
        "-s",
        "--spectro_scans2avg",
        type=int,
        help="Number of spectral measure per pattern",
    )

    args = parser.parse_args()

    apply_overrides(args)

    print("Acquisition beginning")
    print("-" * 100)
    acq = Acquisition()
    acq.thread_acquisition()
    acq.save_raw_data()

    print("Acquisition completed!")
    print("-" * 100)
    print("\n")


if __name__ == "__main__":
    main()
