import numpy as np
import pytest

from onepix.hardware.display_timing import frame_multiples_ms
from onepix.hardware.gray_response import suggest_white_level
from onepix.hardware.tuning_advice import recommend_whole_frames, signal_stability_pct, stability_status

from .gray_response_test import LEVELS, RESPONSE

REFRESH = 60.0


def test_frame_multiples():
    assert frame_multiples_ms(3, REFRESH) == [16.667, 33.333, 50.0]
    assert frame_multiples_ms(2, 119.8)[1] == pytest.approx(16.694, abs=0.01)


def test_recommendation_is_a_whole_number_of_frames_closest_to_the_target():
    # what was measured on the projector: 12.4k, 24.5k and 36.7k counts at 1, 2 and 3 frames
    advice = recommend_whole_frames(peak=22050, integration_time_ms=30.0, refresh_rate_hz=REFRESH, target=30000)
    assert advice["frames"] == 2 and advice["recommended_ms"] == 33.333
    assert advice["expected_peak"] == pytest.approx(24500, rel=0.01)
    assert not advice["saturated"] and not advice["too_bright"] and advice["gray_factor"] is None
    # a weaker signal asks for more frames
    assert recommend_whole_frames(5000, 16.667, REFRESH)["frames"] == 6 or \
        recommend_whole_frames(5000, 16.667, REFRESH)["frames"] > 3


def test_a_signal_without_light_gives_no_advice():
    assert recommend_whole_frames(0, 30.0, REFRESH) is None
    assert recommend_whole_frames(1000, 0, REFRESH) is None


def test_a_reading_that_is_too_bright_even_for_one_frame_asks_for_less_light():
    advice = recommend_whole_frames(peak=40000, integration_time_ms=3.0, refresh_rate_hz=REFRESH)
    assert advice["frames"] == 1 and advice["too_bright"] is True
    assert advice["gray_factor"] == pytest.approx(30000 / (40000 / 3.0 * 16.667), rel=0.01)


def test_a_saturated_reading_is_not_extrapolated():
    advice = recommend_whole_frames(peak=70000, integration_time_ms=100.0, refresh_rate_hz=REFRESH)
    assert advice["saturated"] is True and advice["expected_peak"] is None
    assert advice["frames"] == 3 and advice["recommended_ms"] == 50.0          # half the time, in whole frames
    short = recommend_whole_frames(peak=70000, integration_time_ms=30.0, refresh_rate_hz=REFRESH)
    assert short["saturated"] and short["too_bright"] and short["frames"] == 1


def test_stability_separates_a_steady_signal_from_a_fluctuating_one():
    rng = np.random.default_rng(0)
    spectrum = 100 + 20000 * np.exp(-((np.arange(200) - 100) / 30.0) ** 2)
    steady = [spectrum * (1 + rng.normal(0, 0.003)) for _ in range(12)]
    flicker = [spectrum * (1 + rng.normal(0, 0.07)) for _ in range(12)]
    s, f = signal_stability_pct(steady), signal_stability_pct(flicker)
    assert s < 1.0 and f > 3.0
    assert stability_status(s) == "good" and stability_status(f) == "poor" and stability_status(2.0) == "fair"
    assert signal_stability_pct(steady[:3]) is None and stability_status(None) is None


def test_stability_ignores_the_detector_offset():
    rng = np.random.default_rng(1)
    signal = 5000 * np.exp(-((np.arange(200) - 100) / 30.0) ** 2)
    readings = [signal * (1 + rng.normal(0, 0.05)) + 3000 for _ in range(12)]     # 3000 counts of offset in every band
    assert signal_stability_pct(readings) == pytest.approx(5.0, abs=2.5)


def test_suggested_gray_level_comes_from_the_measured_curve():
    assert 158 <= suggest_white_level(LEVELS, RESPONSE, 255, 0.5) <= 164          # 50 % of the light needs level ~161
    assert 83 <= suggest_white_level(LEVELS, RESPONSE, 100, 0.5) <= 90
    assert suggest_white_level(LEVELS, RESPONSE, 100, 0.0001) is None            # in the dead zone
    assert suggest_white_level([0, 255], [0, 0], 255, 0.5) is None


def test_stability_of_a_flat_spectrum():
    flat = [np.full(50, 1000.0) for _ in range(8)]
    assert signal_stability_pct(flat) == pytest.approx(0.0, abs=1e-9)
    assert signal_stability_pct([np.zeros(50)] * 8) is None
