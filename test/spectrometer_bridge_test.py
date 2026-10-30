import threading

import numpy as np

from onepix.hardware.SpectrometerBridge import SpectrometerBridge


class FakePlugin:
    DeviceName = "fake"

    def __init__(self, effective=None):
        self.integration_time_ms = 2.5
        self.calls = 0
        self.averaging = []
        if effective is not None:
            self.effective_integration_time_ms = effective

    def set_integration_time(self):
        pass

    def get_intensities(self):
        self.calls += 1
        return np.full(4, 100.0)


class OnDemandPlugin(FakePlugin):
    ON_DEMAND = True

    def set_scans_to_average(self, n=None):
        self.averaging.append(n)
        return 1 if n is None else min(n, 8)


def bridge(plugin, repetition=4, integration_time_ms=2.5):
    b = SpectrometerBridge.__new__(SpectrometerBridge)
    b.spectro_name = "fake"
    b.integration_time_ms = integration_time_ms
    b.effective_integration_time_ms = integration_time_ms
    b.repetition = repetition
    b.hw_averaging = False
    b._measure_times_s = __import__("collections").deque(maxlen=20)
    b.spectrometer = plugin
    b.idx_wl_lim = [0, 3]
    return b


def measure(b, n_patterns=3):
    event, stop = threading.Event(), threading.Event()
    spectra = np.zeros((n_patterns, 4))
    t = threading.Thread(target=b.thread_singlepixel_measure, args=(event, stop, spectra))
    t.start()
    for _ in range(n_patterns):
        event.set()
        while event.is_set():
            pass
    t.join(5)
    return spectra


def test_spectra_are_normalised_by_the_applied_integration_time():
    b = bridge(FakePlugin(effective=2.0))
    b.set_integration_time()
    assert b.effective_integration_time_ms == 2.0
    assert np.allclose(measure(b), 100.0 / 2.0)


def test_requested_time_is_used_when_the_plugin_does_not_report_one():
    b = bridge(FakePlugin())
    b.set_integration_time()
    assert np.allclose(measure(b), 100.0 / 2.5)


def test_free_running_plugin_is_flushed_after_setting_the_integration_time():
    plugin = FakePlugin()
    b = bridge(plugin)
    b.set_integration_time()
    before = plugin.calls
    assert b.flush_stale_scans() >= 1 and plugin.calls > before


def test_on_demand_plugin_is_never_flushed():
    plugin = OnDemandPlugin()
    b = bridge(plugin)
    assert b.flush_stale_scans() == 0 and plugin.calls == 0


def test_on_demand_plugin_averages_inside_the_device_then_is_restored():
    plugin = OnDemandPlugin()
    b = bridge(plugin, repetition=4)
    measure(b, 3)
    assert plugin.calls == 3                      # one transfer per pattern
    assert plugin.averaging == [4, None]


def test_device_that_cannot_average_enough_falls_back_to_software():
    plugin = OnDemandPlugin()
    b = bridge(plugin, repetition=20)             # the fake device stops at 8
    measure(b, 2)
    assert plugin.calls == 2 * 20 and not b.hw_averaging
    assert plugin.averaging[-1] is None


def test_measure_time_is_recorded_for_the_projection():
    b = bridge(OnDemandPlugin())
    assert b.measure_time_s() is None
    measure(b, 2)
    assert b.measure_time_s() > 0


def test_gray_level_is_limited_for_every_kind_of_pattern():
    from onepix.hardware.Projection import limit_gray_level
    binary = np.array([[0, 255], [255, 0]], np.uint8)
    assert np.array_equal(limit_gray_level(binary, 255), binary)
    assert np.array_equal(limit_gray_level(binary, 100), np.array([[0, 100], [100, 0]], np.uint8))
    assert limit_gray_level(binary, 100).dtype == np.uint8
    assert np.allclose(limit_gray_level(np.array([0.0, 1.0]), 100), [0.0, 100 / 255])
    ints = np.array([1, 2], np.int32)
    assert limit_gray_level(ints, 100) is ints
