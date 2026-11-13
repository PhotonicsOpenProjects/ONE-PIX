"""Dynamic integration time: the time is re-tuned for every pattern, the spectra stay in counts per ms
and the dark is removed, on a fake spectrometer whose signal is  rate * t + offset."""
import collections
import threading

import numpy as np
import pytest

from onepix.hardware.SpectrometerBridge import SpectrometerBridge

BANDS = 40
OFFSET = 800.0          # readout offset, counts: not proportional to the exposure
DARK_RATE = 0.0         # no dark current: the offset is the whole dark


class FakeSpectrometer:
    """counts = rate * t + OFFSET, saturating at 65535. `rate` is set by the test, per pattern."""
    DeviceName = "fake"
    ON_DEMAND = True

    def __init__(self):
        self.integration_time_ms = 10.0
        self.rate = 100.0           # counts per ms at the peak
        self.shape = np.ones(BANDS)
        self.applied = []

    def set_integration_time(self):
        self.applied.append(self.integration_time_ms)

    def get_wavelengths(self):
        return np.linspace(400, 800, BANDS)

    def get_intensities(self):
        counts = self.rate * self.shape * self.integration_time_ms + OFFSET
        return np.minimum(counts, 65535.0)


def make_bridge(plugin, repetition=2, integration_time_ms=10.0):
    b = SpectrometerBridge.__new__(SpectrometerBridge)
    b.spectro_name = "fake"
    b.integration_time_ms = integration_time_ms
    b.effective_integration_time_ms = integration_time_ms
    b.repetition = repetition
    b.hw_averaging = False
    b._measure_times_s = collections.deque(maxlen=20)
    b.spectrometer = plugin
    b.idx_wl_lim = [0, BANDS - 1]
    return b


def run_measure(b, plugin, rates, **kwargs):
    """Measure one pattern per entry of `rates` (counts per ms of that pattern's peak)."""
    event, stop = threading.Event(), threading.Event()
    spectra = np.zeros((len(rates), BANDS))
    t = threading.Thread(target=b.thread_singlepixel_measure, args=(event, stop, spectra), kwargs=kwargs)
    t.start()
    for rate in rates:
        plugin.rate = rate
        event.set()
        while event.is_set():
            pass
    t.join(10)
    assert not t.is_alive()
    return spectra


# ---------------------------------------------------------------- snapping

def test_ladder_times_are_few_and_close_to_the_proposal():
    snapped = {SpectrometerBridge.snap_to_ladder(t) for t in np.linspace(5, 1000, 400)}
    assert len(snapped) < 30
    for t in (7.3, 33.0, 250.0, 999.0):
        assert abs(SpectrometerBridge.snap_to_ladder(t) / t - 1) < 0.1


def test_frame_times_are_whole_frames_on_the_ladder():
    frame = 1000 / 60
    for t in (5, 17, 40, 100, 333):
        snapped = SpectrometerBridge.snap_to_frames(t, frame)
        frames = snapped / frame
        assert abs(frames - round(frames)) < 1e-3 and round(frames) >= 1
    assert len({SpectrometerBridge.snap_to_frames(t, frame) for t in np.linspace(5, 1000, 400)}) < 30


# ---------------------------------------------------------------- autoexpose

def test_autoexpose_reaches_the_target_and_keeps_the_projector_windows(monkeypatch):
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    plugin.rate = 40.0
    closed = []
    monkeypatch.setattr("onepix.hardware.SpectrometerBridge.cv2.destroyAllWindows", lambda: closed.append(1))
    t = b.autoexpose(max_iterations=10, verbose=False)
    peak = plugin.rate * t + OFFSET
    assert abs(peak - b.TARGET_PEAK_COUNTS) < b.PEAK_TOLERANCE
    assert closed == [], "autoexpose runs between patterns: it must not close the projection window"
    b.get_optimal_integration_time(verbose=False)
    assert closed == [1], "the standalone tuning still closes its window"


def test_autoexpose_uses_the_snapped_times_and_stops_when_stuck():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    plugin.rate = 40.0
    frame = 1000 / 60
    t = b.autoexpose(max_iterations=10, snap=lambda x: SpectrometerBridge.snap_to_frames(x, frame), verbose=False)
    assert abs(t / frame - round(t / frame)) < 1e-3
    # a rate so high that even the minimum saturates: it settles at the minimum, it does not loop
    plugin.rate = 1e7
    assert b.autoexpose(max_iterations=10, verbose=False) == b.MIN_INTEGRATION_TIME_MS


# ---------------------------------------------------------------- the measurement

def test_fixed_time_measurement_is_unchanged():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    b.set_integration_time()
    spectra = run_measure(b, plugin, [50.0, 50.0])
    assert np.allclose(spectra, (50.0 * 10.0 + OFFSET) / 10.0)
    assert getattr(b, "tints_requested_ms", None) is None


def test_dynamic_times_follow_the_brightness_and_spectra_stay_in_counts_per_ms():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    b.set_integration_time()
    rates = [20.0, 400.0, 20.0, 2000.0]
    spectra = run_measure(b, plugin, rates, dynamic_tint=True, tint_frame_ms=None)
    t = b.tints_requested_ms
    assert not np.isnan(t).any()
    assert t[1] < t[0] / 5 and t[3] < t[1] / 3      # brighter pattern, shorter time
    for i, rate in enumerate(rates):
        peak_counts = rate * t[i] + OFFSET
        assert peak_counts < 65535, "no pattern may saturate"
        assert abs(peak_counts - b.TARGET_PEAK_COUNTS) < 2 * b.PEAK_TOLERANCE
    # without the dark correction the offset is divided by a different time for each pattern
    assert not np.allclose(spectra.max(axis=1), rates, rtol=1e-3)
    assert b.integration_time_ms == 10.0, "the configured time is restored after the measurement"


def test_dark_correction_gives_back_the_signal_rate_whatever_the_times():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    b.set_integration_time()
    rates = [20.0, 400.0, 20.0, 2000.0, 400.0]
    spectra = run_measure(b, plugin, rates, dynamic_tint=True)
    plugin.rate = 0.0                                    # projector black
    dark = b.measure_dark_and_correct()
    assert len(dark) == len(set(b.tints_requested_ms))   # one dark exposure per distinct time
    assert np.allclose(spectra.max(axis=1), rates, rtol=1e-6)
    assert b.integration_time_ms == 10.0


def test_dark_correction_needs_a_dynamic_measurement():
    b = make_bridge(FakeSpectrometer())
    with pytest.raises(RuntimeError):
        b.measure_dark_and_correct()


# ---------------------------------------------------------------- black pattern (HAS)

def test_a_black_pattern_is_measured_with_the_previous_time_not_searched_for():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    b.tints_requested_ms = None
    # zones, then the black pattern HAS ends with
    rates = [40.0, 20.0, 80.0, 0.0]
    spectra = run_measure(b, plugin, rates, dynamic_tint=True,
                          dark_patterns=np.array([False, False, False, True]))
    tints = b.tints_requested_ms
    assert not np.isnan(tints).any()
    assert tints[3] == tints[2], "the black pattern keeps the time of the zone before it"
    assert tints[3] in set(tints[:3]), "no time of its own: no extra dark exposure needed"
    assert tints.max() < b.MAX_INTEGRATION_TIME_MS, "no climb to MAX_INTEGRATION_TIME_MS"


def test_without_the_black_pattern_flag_it_is_searched_for_as_before():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    run_measure(b, plugin, [40.0, 0.0], dynamic_tint=True)
    assert b.tints_requested_ms[1] > b.tints_requested_ms[0]


def test_the_dark_correction_zeroes_the_black_pattern_at_every_time_used():
    plugin = FakeSpectrometer()
    b = make_bridge(plugin)
    rates = [40.0, 20.0, 80.0, 0.0]
    spectra = run_measure(b, plugin, rates, dynamic_tint=True,
                          dark_patterns=np.array([False, False, False, True]))
    plugin.rate = 0.0       # projector black for the dark exposures
    b.measure_dark_and_correct()
    assert np.allclose(spectra[3], 0.0, atol=1e-6)
    for i, rate in enumerate(rates[:3]):
        assert np.allclose(spectra[i], rate, rtol=1e-6), "offset removed: back to counts per ms of the signal"
