import argparse

from onepix.Reconstruction import Reconstruction


def main():
    parser = argparse.ArgumentParser(
        description="ONE-PIX reconstruction command line script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-a",
        "--acquisition_path",
        type=str,
        required=True,
        help="Path to an acquisition_results_*.json file to reconstruct",
    )
    parser.add_argument(
        "-n", "--filename", type=str, help="Filename to save the reconstructed data"
    )
    parser.add_argument("-p", "--save_path", type=str, help="Save path")

    args = parser.parse_args()

    print("ONE-PIX reconstruction beginning")
    print("-" * 100)
    rec = Reconstruction(args.acquisition_path)
    rec.data_reconstruction()
    rec.save_reconstruction_results(filename=args.filename, save_path=args.save_path)

    print("Reconstruction completed!")
    print("-" * 100)
    print("\n")


if __name__ == "__main__":
    main()
