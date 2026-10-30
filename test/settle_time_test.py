import numpy as np

from app.cli.probe_settle_time import recommend_periode_pattern_ms, settle_time_ms


def _step(settle_at, period=16, n=25, low=100.0, high=5000.0):
    t = np.arange(n) * period
    return t, np.where(t + period < settle_at, low, high)


def test_settle_time_is_start_of_first_settled_reading():
    t, y = _step(settle_at=50)
    assert settle_time_ms(t, y, 100.0) == 48.0


def test_ramp_is_waited_out():
    t = np.arange(25) * 16.0
    y = np.interp(t, [0, 40, 100], [100, 100, 5000])      # slow rise
    assert settle_time_ms(t, y, 100.0) == 112.0


def test_invisible_step_is_not_reported():
    t = np.arange(25) * 16.0
    assert settle_time_ms(t, np.full(25, 100.0) + np.random.default_rng(0).normal(0, 2, 25), 100.0) is None


def test_never_settled_is_not_reported():
    t = np.arange(25) * 16.0
    assert settle_time_ms(t, np.linspace(100, 5000, 25), 100.0) is None


def test_recommendation_rounds_up_to_whole_frames():
    assert recommend_periode_pattern_ms([40], margin=1.25, frame_ms=16.67) == 51
    assert recommend_periode_pattern_ms([40], margin=1.25) == 50


def test_noisy_bright_level_still_settles():
    rng = np.random.default_rng(1)
    t = np.arange(25) * 16.0
    y = np.where(t < 64, 100.0, 5000.0) + rng.normal(0, 150, 25)     # 3 % noise on the bright level
    assert 48 <= settle_time_ms(t, y, 100.0) <= 80


def test_too_noisy_to_judge_is_not_reported():
    rng = np.random.default_rng(2)
    t = np.arange(25) * 16.0
    assert settle_time_ms(t, np.where(t < 64, 100.0, 1000.0) + rng.normal(0, 400, 25), 100.0) is None


def _pooled(settle_at, n_steps=40, period=30.0, noise=0.03, seed=3):
    from app.cli.probe_settle_time import pooled_response
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_steps):
        phase = rng.uniform(0, period)
        for t in np.arange(phase, 250, period):
            samples.append((t, float(t >= settle_at) + rng.normal(0, noise)))
    return pooled_response(samples)


def test_pooled_response_resolves_finer_than_one_reading():
    r = _pooled(settle_at=47)
    assert 40 <= r["t50"] <= 60 and 40 <= r["settled"] <= 60


def test_pooled_response_slow_tail_is_not_faster_than_typical():
    r = _pooled(settle_at=47)
    assert r["slow_settled"] >= r["settled"]


def test_onset_is_before_the_settle_time_and_bounds_the_hiding():
    from app.cli.probe_settle_time import recommend_latency_hiding_ms
    r = _pooled(settle_at=47)
    assert 30 <= r["onset"] <= 47
    assert recommend_latency_hiding_ms(r["onset"]) == int(r["onset"] * 0.6)
    assert recommend_latency_hiding_ms(None) == 0 and recommend_latency_hiding_ms(12) == 0
