"""Measure the projector's gray-level response with the spectrometer.

The light the spectrometer receives is measured for uniform fields of increasing gray level. The result
(levels and relative light) can be written as a JSON file and used by "gray_response_path" in
conf/hardware_config.json, so that gray-level patterns (Fourier methods) give light proportional to
their value - see onepix/hardware/gray_response.py.

The integration time is long (50 ms by default) to average out the projector's flicker; the bright
fields would then saturate the brightest bands, so only the bands that stay unsaturated at white are
used (the response does not depend on the wavelength).

USAGE (the projector must light the spectrometer; nothing else may use them)
    python -m app.cli.probe_gray_response
    python -m app.cli.probe_gray_response --output conf/gray_response.json
"""

import argparse
import json

import cv2
import numpy as np

from onepix.hardware.HardwareConfig import Hardware
from onepix.hardware.gui_thread import gui_thread

SETTLE_MS = 350
BAND_FLOOR = 3000          # counts above the dark below which a band is too weak to be used
BAND_CEILING = 50000       # counts above which a band is close to saturation


def usable_bands(white_signal, floor=BAND_FLOOR, ceiling=BAND_CEILING):
    """Boolean mask of the bands that are neither too weak nor close to saturation at white
    (`white_signal`: spectrum at white minus dark; the ceiling is on the signal)."""
    white_signal = np.asarray(white_signal, float)
    return (white_signal > floor) & (white_signal < ceiling)


def light_curve(levels, signals_up, signals_down, white_up, white_down):
    """Relative light at each level (white = 1), the mean of an ascending and a descending pass.
    Returns (response, repeatability): the largest difference between the passes."""
    up, down = np.asarray(signals_up, float), np.asarray(signals_down, float)
    top = (white_up + white_down) / 2.0
    response = (up + down) / 2.0 / top
    return response, float(np.abs(up - down).max() / top)


def main():
    parser = argparse.ArgumentParser(
        description="Measure the projector's gray-level response.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--integration-time", type=float, default=50.0, help="integration time (ms)")
    parser.add_argument("--reads", type=int, default=10, help="readings averaged per level")
    parser.add_argument("--step", type=int, default=8, help="gray level step")
    parser.add_argument("--output", default=None, help="write the curve to this JSON file")
    args = parser.parse_args()

    hardware = Hardware()
    try:
        hardware.hardware_initialisation()
        spectrometer = hardware.spectrometer
        spectrometer.integration_time_ms = args.integration_time
        spectrometer.set_integration_time()
        wavelengths = spectrometer.get_wavelengths()
        hardware.projection.init_projection(
            [np.zeros((hardware.height, hardware.width), np.uint8)], None, cv2.INTER_LINEAR_EXACT
        )

        def show(level):
            gui_thread.run(cv2.imshow, "ImageWindow", np.full((hardware.height, hardware.width), level, np.uint8))
            gui_thread.run(cv2.waitKey, SETTLE_MS)

        def spectrum():
            return np.mean([np.asarray(spectrometer.get_intensities(), float) for _ in range(args.reads)], axis=0)

        show(0)
        dark = spectrum()
        show(255)
        white = spectrum() - dark
        bands = usable_bands(white)
        if bands.sum() < 10:
            raise SystemExit("Not enough usable bands: the spectrometer must see the projector "
                             f"(signal between {BAND_FLOOR} and {BAND_CEILING} counts at white).")
        print(f"{bands.sum()} bands used ({wavelengths[bands].min():.0f}-{wavelengths[bands].max():.0f} nm) "
              f"of {len(white)}, {args.integration_time:g} ms")

        levels = list(range(0, 255, args.step)) + [255]
        passes = {}
        for name, sequence in (("up", levels), ("down", levels[::-1])):
            passes[name] = {level: (show(level), (spectrum() - dark)[bands].sum())[1] for level in sequence}
        up = [passes["up"][level] for level in levels]
        down = [passes["down"][level] for level in levels]
        response, repeatability = light_curve(levels, up, down, up[-1], down[-1])

        print("-" * 70)
        for level, value in zip(levels, response):
            print(f"  level {level:3d}  light {100 * value:6.2f} %  (linear: {100 * level / 255:6.2f} %)  "
                  + "#" * int(round(value * 40)))
        print(f"Largest difference between the ascending and descending passes: {100 * repeatability:.2f} % of white")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump({"levels": levels, "response": [round(float(r), 5) for r in response],
                           "integration_time_ms": args.integration_time,
                           "bands_nm": [float(wavelengths[bands].min()), float(wavelengths[bands].max())]}, f, indent=1)
            print(f"Written to {args.output}")
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            hardware.spectrometer.spec_close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
