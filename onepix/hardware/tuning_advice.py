"""Advice for the live integration-time tuning (pure functions, no hardware).

What the measurements on a DLP projector showed:
- the integration time has to be a whole number of display frames (16.7 ms at 60 Hz): any other value
  catches a different share of the projector's flicker at each reading;
- the single-sided methods are tuned on the open field, the brightest pattern they project;
- a saturated reading says nothing about how much light there really is, so a recommendation computed
  from it can only be a first step;
- when even one display frame is too bright, the light has to be reduced (max_gray_level), not the time.
"""
import numpy as np

from onepix.hardware.display_timing import frame_period_ms

# A reading above this is probably clipped by the detector (16 bit ADCs stop around 65 000 counts).
SATURATION_SUSPECT_COUNTS = 60000

# Highest peak accepted for a recommendation: a margin under the saturation of a 16 bit detector.
SAFE_PEAK_COUNTS = 55000

STABILITY_GOOD_PCT = 1.0
STABILITY_FAIR_PCT = 3.0

MAX_FRAMES = 12


def recommend_whole_frames(peak, integration_time_ms, refresh_rate_hz=None, target=30000,
                           safe_peak=SAFE_PEAK_COUNTS, saturated_at=SATURATION_SUSPECT_COUNTS,
                           max_frames=MAX_FRAMES):
    """The whole number of display frames whose peak is the closest to `target` counts, from a reading
    of `peak` counts at `integration_time_ms` (the light is proportional to the time).

    Returns None without signal, else a dict:
      frame_ms, frames, recommended_ms, expected_peak,
      saturated      the reading is clipped: the advice is a first step (half the time), to check again
      too_bright     even one frame exceeds `safe_peak`: reduce the light instead (gray_factor says by how much)
      gray_factor    light to keep, to get the target at one frame (None unless too_bright)"""
    if peak is None or peak <= 0 or integration_time_ms <= 0:
        return None
    frame = frame_period_ms(refresh_rate_hz)
    per_ms = peak / integration_time_ms
    result = {"frame_ms": round(frame, 3), "saturated": False, "too_bright": False, "gray_factor": None}

    if peak >= saturated_at:
        # the true light is unknown (only a lower bound): halve the time, in whole frames
        frames = max(1, int((integration_time_ms / 2.0) / frame + 0.01))
        result.update(saturated=True, frames=frames, recommended_ms=round(frames * frame, 3),
                      expected_peak=None, too_bright=frames == 1 and integration_time_ms <= 2 * frame)
        return result

    candidates = [(n, per_ms * n * frame) for n in range(1, max_frames + 1)]
    usable = [c for c in candidates if c[1] <= safe_peak]
    if not usable:
        frames, expected = candidates[0]
        result.update(too_bright=True, gray_factor=round(target / expected, 4))
    else:
        frames, expected = min(usable, key=lambda c: abs(np.log(c[1] / target)))
    result.update(frames=frames, recommended_ms=round(frames * frame, 3), expected_peak=round(expected))
    return result


def signal_stability_pct(readings, min_readings=5):
    """Fluctuation of the signal from one reading to the next, in % (None with too few readings).

    `readings`: spectra (n, bands) taken at the same integration time. The detector's offset (the level of
    the weakest bands) is removed, then the bands that carry the signal (more than half of the strongest
    one) are summed, so that neither the offset nor the noise of the empty bands hides the fluctuation."""
    readings = np.asarray(readings, float)
    if readings.ndim != 2 or len(readings) < min_readings:
        return None
    mean = readings.mean(axis=0)
    base = np.percentile(mean, 5)
    signal = mean - base
    if signal.max() <= 0:                                   # a flat spectrum: nothing to separate from the offset
        totals = readings.sum(axis=1)
    else:
        totals = (readings[:, signal >= 0.5 * signal.max()] - base).sum(axis=1)
    if totals.mean() <= 0:
        return None
    return float(100.0 * totals.std() / totals.mean())


def stability_status(pct):
    """"good" up to 1 %, "fair" up to 3 %, else "poor" (None: not known yet)."""
    if pct is None:
        return None
    if pct <= STABILITY_GOOD_PCT:
        return "good"
    return "fair" if pct <= STABILITY_FAIR_PCT else "poor"
