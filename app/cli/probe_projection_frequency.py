"""Empirically find the shortest spectrometer integration time that
reliably averages out a single-chip DLP projector's colour-wheel/DMD-PWM
flicker - see onepix/hardware/display_timing.py for the physics.

WHY NOT JUST POLL FAST AND LOOK AT THE WAVEFORM (FFT)?
-------------------------------------------------------
A DLP colour wheel typically spins at ~100-400 Hz. To resolve that
directly by polling get_intensities() as fast as possible and taking an
FFT, we'd need to sample well above twice that rate (Nyquist). But each
call to get_intensities() on this hardware costs several ms of USB/driver
overhead regardless of how short the integration time is set to (see
SpectrometerBridge.thread_singlepixel_measure()'s flush diagnostics) -
this script measures the actually-achievable call rate up front and, if
it's too low to resolve typical DLP frequencies, skips straight past the
misleading "fast poll + FFT" idea.

THE METHOD THIS SCRIPT ACTUALLY USES
-------------------------------------
Sidesteps that limit entirely by using the spectrometer's own *analog*
integration window as the low-pass filter, instead of our USB polling
rate:

For each candidate integration_time_ms (short to long), take many
repeated single readings of a static, uniformly bright pattern - each
one starting at an effectively random phase relative to the projector's
free-running colour wheel - and look at how much they disagree (relative
standard deviation). While integration_time_ms is shorter than the
flicker period, each reading catches a different, essentially random
slice of the cycle, so the readings disagree a lot. Once
integration_time_ms comfortably exceeds the flicker period, every
reading averages over one or more whole cycles and they should mostly
agree, whatever the starting phase - the disagreement collapses. That
collapse point *is* the answer, and finding it doesn't require sampling
anywhere near the flicker frequency itself.

The pattern's brightness is calibrated *separately for each candidate
integration time* (see measure_batch()), not once for the whole sweep:
on a bright projector, one fixed brightness that avoids saturating at
the longest integration time leaves the shortest one so dim its
readings sit in the noise floor / PWM-quantisation regime instead of
reflecting real flicker - which shows up as CV% *rising* with
integration time instead of settling, the opposite of the effect this
script is looking for. And that calibration is done using the *actual*
`repeats`-sized measurement batch (retried with less brightness if any
sample in it saturates), not a separate handful of throwaway probe
reads - at short integration times a small probe routinely misses a
peak that a full batch then hits, which otherwise shows up as an
erratic, non-monotonic brightness sequence with saturation appearing
and disappearing with no clear pattern.

USAGE
-----
    python -m app.cli.probe_projection_frequency
    python -m app.cli.probe_projection_frequency --repeats 30 \\
        --integration-times 1 2 3 5 8 12 17 25 35 50 70 100

Make sure nothing else (the Flask app, another script) is using the
spectrometer/projector at the same time - this script does not
coordinate with app/GUI/flask's hardware_lock.
"""

import argparse
import time

import cv2
import numpy as np

from onepix.hardware.HardwareConfig import Hardware
from onepix.hardware.display_timing import get_refresh_rate_hz, frame_period_ms
from onepix.hardware.gui_thread import gui_thread

# Settle time (ms) used when swapping the displayed pattern during
# calibration - unlike Projection.init_projection() (which also creates
# the window and always waits a fixed 3s, meant to be called once), this
# just needs to give the projector time to update an already-open window.
CALIBRATION_SETTLE_MS = 150

DEFAULT_INTEGRATION_TIMES_MS = [1, 2, 3, 5, 8, 12, 17, 25, 35, 50, 70, 100]

# Below this coefficient of variation (relative std-dev of repeated
# readings, in %), a candidate integration time is considered "settled" -
# i.e. long enough that phase no longer matters. 1.5% is comfortably
# above normal shot/dark noise on a healthy signal (which the sweep's
# printed table lets you sanity-check) while still well below the
# swings a real phase-dependent flicker produces.
SETTLED_CV_THRESHOLD_PCT = 1.5

# Report the recommendation only once this many *consecutive* candidates
# (in increasing order) are settled, so one lucky low-variance point
# right before a still-flickering region isn't mistaken for the answer.
SETTLED_STREAK_REQUIRED = 2

# 16-bit ADC ceiling. A saturated/clipped reading is *always* bit-for-bit
# identical to the next one (CV = 0%) regardless of any real flicker -
# that looks exactly like "settled" but means the opposite: the signal is
# unusable at that integration time. Treated as saturated once within 2%
# of this ceiling, to also catch near-clipping before it hits exactly
# 65535.
SATURATION_CEILING = 65535.0
SATURATION_MARGIN = 0.98

# Target peak (as a fraction of the ADC ceiling) to aim for at the
# *longest* integration time in the sweep when auto-calibrating the test
# pattern's brightness - low enough to leave headroom against the
# saturation ceiling, high enough to keep shot/dark noise from dominating
# the CV% readings at the short end of the sweep.
CALIBRATION_TARGET_FRACTION = 0.5


def measure_achievable_read_rate(spectrometer, n_calls=15):
    """How many get_intensities() calls/second this device+driver can
    actually sustain, regardless of integration_time_ms - tells us
    whether directly polling for a DLP-frequency waveform is even
    plausible (it needs roughly double the flicker frequency)."""

    t0 = time.perf_counter()

    for _ in range(n_calls):
        spectrometer.get_intensities()

    elapsed = time.perf_counter() - t0

    return n_calls / elapsed if elapsed > 0 else float("inf")


def _show_pattern(hardware, brightness, interp_method, settle_ms=CALIBRATION_SETTLE_MS):
    """Swap the already-open projection window to a new flat-brightness
    pattern - cheap compared to Projection.init_projection() (which also
    (re)creates the window and always waits a fixed 3s), so it's safe to
    call repeatedly during calibration."""

    pattern = np.full(
        (hardware.height, hardware.width), brightness, dtype=np.uint8
    )

    gui_thread.run(
        cv2.imshow,
        "ImageWindow",
        cv2.resize(
            pattern,
            (hardware.width, hardware.height),
            interpolation=interp_method,
        ),
    )
    gui_thread.run(cv2.waitKey, settle_ms)

    return pattern


def measure_batch(hardware, interp_method, target_peak, repeats, start_brightness=255, max_attempts=8):
    """Take `repeats` readings at a brightness chosen so *none of them*
    saturate, at the spectrometer's currently-set integration time -
    retrying with less brightness if any do, until a clean batch is
    found (or brightness bottoms out at 1).

    This replaces an earlier two-phase design (a handful of throwaway
    "calibration" probe reads to pick a brightness, then a *separate*
    batch of `repeats` reads used for the actual CV%): at short
    integration times, readings can swing wildly with the projector's
    flicker phase - that's the very thing this script is trying to
    characterise - and a small calibration probe (even taking the max of
    a few reads) routinely missed a peak that the larger, real batch
    then hit, saturating it. That showed up as an erratic,
    non-monotonic brightness/mean_peak sequence with saturation
    appearing and disappearing with no clear pattern.

    Checking (and retrying on) the *actual measurement batch itself*
    closes that gap completely: whatever data ends up being reported is
    exactly the data that was checked for saturation, at full `repeats`
    statistical power instead of a handful of throwaway probes.

    Returns (brightness, peaks, saturated) - `saturated` True only if
    brightness bottomed out at 1 and the batch still had a clipped
    sample.
    """

    spectrometer = hardware.spectrometer
    brightness = start_brightness
    peaks = None

    for _ in range(max_attempts):

        _show_pattern(hardware, brightness, interp_method)

        peaks = np.asarray([
            float(np.max(np.asarray(spectrometer.get_intensities())))
            for _ in range(repeats)
        ])

        observed_max = float(np.max(peaks))

        if observed_max < SATURATION_MARGIN * SATURATION_CEILING:
            return brightness, peaks, False

        if brightness <= 1:
            return brightness, peaks, True

        # Proportional correction from how far over target the observed
        # max was, capped at a plain halving so one very extreme outlier
        # reading can't overcorrect brightness to near-zero in one step.
        scale = target_peak / observed_max
        proportional = int(np.clip(round(brightness * scale), 1, 255))
        brightness = max(1, min(proportional, brightness // 2))

    return brightness, peaks, True


def sweep_integration_times(hardware, integration_times_ms, repeats, interp_method):
    """For each integration time: find a pattern brightness that keeps a
    full `repeats`-sized measurement batch under the ADC ceiling (see
    measure_batch - a single brightness can't serve the whole sweep on a
    bright projector, and a separate small calibration probe isn't
    reliable enough to guarantee the real batch won't saturate), and
    return
    {integration_time_ms: (mean_peak, cv_pct, saturated, brightness, samples)}.
    """

    spectrometer = hardware.spectrometer
    target_peak = CALIBRATION_TARGET_FRACTION * SATURATION_CEILING
    results = {}

    # Longer integration times need proportionally less brightness to
    # hit the same target_peak, so seeding each step's search from the
    # *previous* step's converged brightness (instead of always
    # restarting from 255) converges in far fewer attempts across a wide
    # sweep - starting from 255 every time can burn the whole attempt
    # budget on repeated halving before ever reaching a clean,
    # non-saturated batch at the longer end.
    last_brightness = 255

    for t_ms in sorted(integration_times_ms):

        spectrometer.integration_time_ms = t_ms
        spectrometer.set_integration_time()

        brightness, peaks, saturated = measure_batch(
            hardware, interp_method, target_peak, repeats,
            start_brightness=last_brightness,
        )
        last_brightness = brightness

        mean_peak = float(np.mean(peaks))
        cv_pct = (
            100.0 * float(np.std(peaks)) / mean_peak
            if mean_peak > 0
            else float("nan")
        )

        results[t_ms] = (mean_peak, cv_pct, saturated, brightness, peaks)

        flag = "  <- SATURATED (unreliable, ignored)" if saturated else ""

        print(
            f"  integration_time_ms={t_ms:>6.1f}  "
            f"brightness={brightness:>3d}/255  "
            f"mean_peak={mean_peak:>10.1f}  "
            f"CV={cv_pct:>5.2f}%{flag}"
        )

    return results


def find_settled_integration_time(results):
    """First integration_time_ms (in increasing order) after which CV%
    stays below SETTLED_CV_THRESHOLD_PCT for SETTLED_STREAK_REQUIRED
    consecutive *non-saturated* candidates - None if the sweep never
    settles (try extending --integration-times to larger values) or only
    "settles" via saturation (try lower --integration-times / a dimmer
    pattern)."""

    ordered = sorted(results.items())
    streak = 0

    for i, (t_ms, (_, cv_pct, saturated, _, _)) in enumerate(ordered):

        if saturated:
            streak = 0
            continue

        if cv_pct <= SETTLED_CV_THRESHOLD_PCT:
            streak += 1
            if streak >= SETTLED_STREAK_REQUIRED:
                # First candidate of the settled streak.
                first_idx = i - (SETTLED_STREAK_REQUIRED - 1)
                return ordered[first_idx][0]
        else:
            streak = 0

    return None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sweep spectrometer integration time against a static "
            "projected pattern to find the shortest value that "
            "averages out DLP colour-wheel/DMD-PWM flicker."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--integration-times",
        type=float,
        nargs="+",
        default=DEFAULT_INTEGRATION_TIMES_MS,
        help="Candidate integration times (ms) to test, low to high",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=20,
        help="Repeated readings per candidate integration time",
    )
    args = parser.parse_args()

    hardware = Hardware()

    try:
        hardware.hardware_initialisation()

        # Full brightness first, just to open/position the window - each
        # sweep step calibrates its own brightness from here (see
        # sweep_integration_times/calibrate_brightness_for_time).
        placeholder = np.full(
            (hardware.height, hardware.width), 255, dtype=np.uint8
        )
        hardware.projection.init_projection(
            [placeholder], None, cv2.INTER_LINEAR_EXACT
        )

        print("-" * 100)
        refresh_hz = get_refresh_rate_hz()
        print(
            f"Detected display refresh rate: {refresh_hz:.2f} Hz "
            f"(frame period {frame_period_ms(refresh_hz):.2f} ms)"
        )

        achievable_hz = measure_achievable_read_rate(hardware.spectrometer)
        print(
            f"Achievable get_intensities() rate on this setup: "
            f"~{achievable_hz:.1f} Hz"
        )

        if achievable_hz < 2 * 100:
            print(
                "-> Too slow to resolve a typical DLP colour wheel "
                "(~100-400 Hz) by direct polling/FFT (Nyquist). Using "
                "the integration-time sweep below instead, which doesn't "
                "need to sample the flicker directly."
            )

        print("-" * 100)
        print(
            f"Sweeping {len(args.integration_times)} integration times "
            f"({args.repeats} repeats each)..."
        )
        print("-" * 100)

        results = sweep_integration_times(
            hardware, args.integration_times, args.repeats, cv2.INTER_LINEAR_EXACT
        )

        print("-" * 100)
        settled_at = find_settled_integration_time(results)

        if settled_at is not None:
            print(
                f"Recommendation: integration_time_ms >= {settled_at} "
                f"(CV%% stays <= {SETTLED_CV_THRESHOLD_PCT}% from there on "
                "in this sweep)."
            )
            print(
                "Set this in conf/acquisition_parameters.json "
                "(\"integration_time_ms\")."
            )
        else:
            print(
                "No candidate settled below "
                f"{SETTLED_CV_THRESHOLD_PCT}% CV - try "
                "--integration-times with larger values, or check the "
                "signal level (a very weak/saturated signal inflates CV% "
                "for reasons unrelated to flicker)."
            )

        print("-" * 100)

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
