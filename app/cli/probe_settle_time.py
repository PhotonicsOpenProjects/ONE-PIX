"""Measure how long the projector takes to show a new pattern, to set
"periode_pattern" (conf/hardware_config.json) from a measurement instead
of the 60 ms default.

periode_pattern is the wait between showing a pattern and measuring it;
with an on-demand spectrometer it is now the largest fixed cost of each
pattern. This script projects black <-> white steps, reads the spectrometer
continuously from the moment the step is shown, and finds when the signal
reaches its final level and stays there.

USAGE (the projector must light the spectrometer; nothing else may use them)
    python -m app.cli.probe_settle_time
    python -m app.cli.probe_settle_time --steps 12 --margin 1.3 --write
"""

import argparse
import json
import math
import random
import threading
import time

import cv2
import numpy as np

from onepix.hardware.HardwareConfig import Hardware
from onepix.utils import write_json_atomic
from onepix.hardware.display_timing import get_refresh_rate_hz, frame_period_ms
from onepix.hardware.gui_thread import gui_thread

# A step is held this long before it is timed (the previous level is
# fully settled), then read for READ_WINDOW_MS.
HOLD_MS = 500
READ_WINDOW_MS = 400

# "Settled" = within this fraction of the black-white swing of the final level.
SETTLE_TOLERANCE = 0.05

# Below this swing (counts) the spectrometer does not see the projector.
MIN_SWING_COUNTS = 50


def settle_time_ms(times_ms, levels, previous_level, tolerance=SETTLE_TOLERANCE):
    """Time (ms after the step was shown) from which `levels` stay within
    `tolerance` of the swing around their final value (median of the last
    quarter). `times_ms` are the start times of the readings, so a reading
    that straddles the change counts as unsettled. None if they never settle
    or the step is not visible."""
    levels = np.asarray(levels, dtype=float)
    times_ms = np.asarray(times_ms, dtype=float)
    tail = levels[-max(2, len(levels) // 4):]
    final = float(np.median(tail))
    swing = abs(final - previous_level)
    if swing < MIN_SWING_COUNTS:
        return None
    # at a short integration time the DLP flicker makes a bright level noisy
    # (proportionally to the level), so the band cannot be tighter than that noise
    # (estimated from successive differences, so a signal still drifting is not mistaken for noise)
    noise = float(np.std(np.diff(tail))) / np.sqrt(2)
    band = max(tolerance * swing, 3.0 * noise)
    if band > 0.5 * swing:
        return None
    unsettled = np.abs(levels - final) > band
    if unsettled[-1]:
        return None
    last_bad = np.flatnonzero(unsettled)
    return float(times_ms[last_bad[-1] + 1]) if len(last_bad) else float(times_ms[0])


def pooled_response(samples, bin_ms=10.0, tolerance=SETTLE_TOLERANCE, min_samples=4):
    """Step response from many steps pooled together.

    `samples` are (t_ms, level) with level normalised so that 0 is the level
    before the step and 1 the level after it. The readings of different
    steps start at random phases, so together they sample the response much
    more finely than one reading lasts. Per time bin the median is the
    typical response and the 10th percentile the slowest steps.

    Returns {"onset", "t50", "t90", "settled", "slow_settled"} in ms (None when not
    reached): `settled` for the typical response, `slow_settled` for the
    slowest 10 % of steps, allowing the spread that noise alone gives."""
    t = np.array([a for a, _ in samples], dtype=float)
    y = np.array([b for _, b in samples], dtype=float)
    edges = np.arange(0.0, t.max() + bin_ms, bin_ms)
    idx = np.digitize(t, edges) - 1
    centres, p50, p10, p90 = [], [], [], []
    for k in range(len(edges) - 1):
        v = y[idx == k]
        if len(v) >= min_samples:
            centres.append(edges[k])
            p50.append(np.median(v))
            p10.append(np.percentile(v, 10))
            p90.append(np.percentile(v, 90))
    centres, p50, p10, p90 = np.array(centres), np.array(p50), np.array(p10), np.array(p90)
    if len(centres) < 4:
        return {"t50": None, "t90": None, "settled": None, "slow_settled": None, "onset": None}

    def first_at_least(curve, level):
        hit = np.flatnonzero(curve >= level)
        return float(centres[hit[0]]) if len(hit) else None

    def stays_above(curve, level):
        below = np.flatnonzero(curve < level)
        if len(below) and below[-1] == len(curve) - 1:
            return None
        return float(centres[below[-1] + 1]) if len(below) else float(centres[0])

    tail = slice(-max(2, len(centres) // 4), None)
    noise = float(np.median(p50[tail] - p10[tail]))
    # first change of the light, on the fastest 10 % of the steps, one bin earlier
    # (a reading that already sees it started before it) - this is what bounds
    # how early the next pattern may be shown
    onset = first_at_least(p90, 0.15 + 2 * max(noise, 0.0))
    onset = None if onset is None else max(0.0, onset - bin_ms)
    return {
        "onset": onset,
        "t50": first_at_least(p50, 0.5),
        "t90": first_at_least(p50, 0.9),
        "settled": stays_above(p50, 1.0 - tolerance),
        "slow_settled": stays_above(p10, 1.0 - tolerance - max(noise, 0.0)),
    }


def recommend_latency_hiding_ms(onset_ms, factor=0.6):
    """How long before the end of a measurement the next pattern may be shown:
    a fraction of the dead time before the light starts to change (0 if the
    onset is unknown or too short to be worth it)."""
    if onset_ms is None:
        return 0
    hiding = int(onset_ms * factor)
    return hiding if hiding >= 10 else 0


def recommend_periode_pattern_ms(settle_times_ms, margin=1.25, frame_ms=None):
    """Worst settle time with a safety margin, rounded up to whole display
    frames (a new pattern cannot appear between two frames)."""
    worst = max(settle_times_ms) * margin
    if frame_ms:
        worst = math.ceil(worst / frame_ms) * frame_ms
    return int(math.ceil(worst))


def _level(hardware, intensities):
    return float(np.mean(intensities))


def measure_step(hardware, brightness, previous_level, interp_method, jitter_ms=0.0):
    """Show a flat pattern and read the spectrometer until READ_WINDOW_MS has
    elapsed. Returns (start times (ms since the pattern was shown), levels)."""
    pattern = cv2.resize(
        np.full((hardware.height, hardware.width), brightness, dtype=np.uint8),
        (hardware.width, hardware.height),
        interpolation=interp_method,
    )
    # as in Projection.thread_projection(): imshow, then waitKey pumps the window
    t0 = time.perf_counter()
    gui_thread.run(cv2.imshow, "ImageWindow", pattern)
    pump = threading.Thread(target=gui_thread.run, args=(cv2.waitKey, READ_WINDOW_MS))
    pump.start()
    # random phase between the step and the readings, so that the steps pooled
    # together sample the response at different instants
    time.sleep(random.uniform(0.0, jitter_ms) / 1000.0)

    times, levels = [], []
    while (time.perf_counter() - t0) * 1000 < READ_WINDOW_MS:
        start = time.perf_counter()
        levels.append(_level(hardware, hardware.spectrometer.get_intensities()))
        times.append((start - t0) * 1000)
    pump.join()
    return times, levels


def _write(hardware, rec, latency_hiding_ms=None):
    with open(hardware.hardware_config_path) as f:
        conf = json.load(f)
    before = conf.get("periode_pattern")
    conf["periode_pattern"] = rec
    if latency_hiding_ms is not None:
        conf["latency_hiding_ms"] = latency_hiding_ms
    write_json_atomic(hardware.hardware_config_path, conf, indent=2)
    print(f"Written to {hardware.hardware_config_path} (was {before})")


def main():
    parser = argparse.ArgumentParser(
        description="Measure the projector's pattern settle time.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--steps", type=int, default=10, help="black<->white steps timed")
    parser.add_argument("--margin", type=float, default=1.25, help="safety factor on the worst settle time")
    parser.add_argument("--integration-time", type=float, default=None,
                        help="integration time (ms) used for the probe only (shorter = finer time resolution, "
                             "but a noisier DLP flicker); the configured one is restored")
    parser.add_argument("--fine", action="store_true",
                        help="pool the readings of all steps at random phases: resolution of a few ms instead of "
                             "one reading (use with --steps 60 or more)")
    parser.add_argument("--hiding-factor", type=float, default=0.6,
                        help="fraction of the measured dead time used by latency_hiding_ms")
    parser.add_argument("--write-hiding", action="store_true",
                        help="with --fine, also store latency_hiding_ms in hardware_config.json (0 = off)")
    parser.add_argument("--write", action="store_true", help="store the result as periode_pattern in hardware_config.json")
    args = parser.parse_args()

    hardware = Hardware()
    try:
        hardware.hardware_initialisation()
        if args.integration_time is not None:
            hardware.spectrometer.integration_time_ms = args.integration_time
            hardware.spectrometer.set_integration_time()
        interp = cv2.INTER_LINEAR_EXACT
        hardware.projection.init_projection(
            [np.zeros((hardware.height, hardware.width), np.uint8)], None, interp
        )

        refresh_hz = get_refresh_rate_hz()
        frame_ms = frame_period_ms(refresh_hz)
        read_ms = np.median([
            (lambda t: (hardware.spectrometer.get_intensities(), time.perf_counter() - t)[1])(time.perf_counter())
            for _ in range(5)
        ]) * 1000
        print(f"Display {refresh_hz:.2f} Hz (frame {frame_ms:.1f} ms); one reading takes {read_ms:.1f} ms,"
              f" which is the time resolution of this measurement.")

        settle, level = {"rising": [], "falling": []}, 0.0
        pooled = {"rising": [], "falling": []}
        for i in range(args.steps):
            brightness = 255 if i % 2 == 0 else 0
            # settled previous level, to measure the size of the swing
            if i == 0:
                gui_thread.run(cv2.waitKey, HOLD_MS)
                level = _level(hardware, hardware.spectrometer.get_intensities())
            times, levels = measure_step(hardware, brightness, level, interp,
                                         jitter_ms=read_ms if args.fine else 0.0)
            t = settle_time_ms(times, levels, level)
            final = float(np.median(levels[-max(2, len(levels) // 4):]))
            if abs(final - level) >= MIN_SWING_COUNTS:
                pooled["rising" if brightness else "falling"].extend(
                    (a, (b - level) / (final - level)) for a, b in zip(times, levels))
            level = final
            print(f"  step {i:>2} -> {'white' if brightness else 'black'}: "
                  + ("not visible/never settled" if t is None else f"settled after {t:.0f} ms"))
            if t is not None:
                settle["rising" if brightness else "falling"].append(t)
            gui_thread.run(cv2.waitKey, HOLD_MS)

        print("-" * 80)
        if args.fine:
            slow, onsets = [], []
            for name, samples in pooled.items():
                r = pooled_response(samples) if len(samples) > 20 else {}
                print(f"{name:>8}: {len(samples)} readings pooled | 50 % at {r.get('t50')} ms, 90 % at {r.get('t90')} ms, "
                      f"settled at {r.get('settled')} ms (slowest 10 % of steps: {r.get('slow_settled')} ms)")
                slow.append(r.get("slow_settled"))
                onsets.append(r.get("onset"))
            if None in slow or not slow:
                print("A direction never settled in the pooled response: not enough signal or steps. "
                      "Nothing to recommend.")
                return
            rec = recommend_periode_pattern_ms([max(slow)], args.margin, frame_ms)
            print(f"Recommendation: periode_pattern = {rec} ms (slowest-10 % settle time x{args.margin}, "
                  f"whole frames); current: {hardware.periode_pattern} ms")
            known = [o for o in onsets if o is not None]
            hiding = recommend_latency_hiding_ms(min(known) if len(known) == len(onsets) else None, args.hiding_factor)
            print(f"Dead time before the light changes: {onsets} ms -> latency_hiding_ms = {hiding} "
                  f"(x{args.hiding_factor} of the shortest; 0 = not worth it); "
                  f"current: {getattr(hardware, 'latency_hiding_ms', 0)} ms")
            if args.write:
                _write(hardware, rec, latency_hiding_ms=hiding if args.write_hiding else None)
            return
        if min(len(v) for v in settle.values()) < max(2, args.steps // 4):
            print("Not enough valid steps in both directions "
                  f"(rising: {len(settle['rising'])}, falling: {len(settle['falling'])}); the spectrometer must "
                  f"see the projector (swing > {MIN_SWING_COUNTS} counts) and the signal must be stable "
                  "enough: try a longer integration time. Nothing to recommend.")
            return

        every = settle["rising"] + settle["falling"]
        for name, v in settle.items():
            print(f"{name:>8}: median {np.median(v):.0f} ms, worst {max(v):.0f} ms")
        rec = recommend_periode_pattern_ms([max(every)], args.margin, frame_ms)
        print(f"Recommendation: periode_pattern = {rec} ms "
              f"(worst settle time x{args.margin}, whole frames); current: {hardware.periode_pattern} ms")

        if args.write:
            _write(hardware, rec)
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
