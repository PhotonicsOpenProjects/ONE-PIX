import numpy as np
import pytest

from onepix.hardware.gray_response import apply_lut, build_lut, load_lut

# Light measured on this setup (ViewSonic projector, Avenir Aris spectrometer, 50 ms)
LEVELS = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 255]
RESPONSE = [0.0001, 0.0, 0.0, 0.0, 0.0001, 0.0, 0.0015, 0.0066, 0.0161, 0.0301, 0.0483, 0.0717, 0.0996, 0.1338, 0.1728, 0.2165, 0.269, 0.3248, 0.3848, 0.4529, 0.4949, 0.5282, 0.5598, 0.6006, 0.6475, 0.6946, 0.7435, 0.7896, 0.8216, 0.861, 0.8814, 0.9408, 1.0]


def light(level, white=255):
    return np.interp(level, LEVELS, RESPONSE) / np.interp(white, LEVELS, RESPONSE)


@pytest.mark.parametrize("white", [255, 100])
def test_the_lut_makes_the_light_proportional_to_the_pattern(white):
    lut = build_lut(LEVELS, RESPONSE, white)
    assert lut.dtype == np.uint8 and lut.shape == (256,)
    assert lut[0] == 0 and lut[255] == white
    assert np.all(np.diff(lut.astype(int)) >= 0)
    pattern = np.arange(256)
    # above the first lit levels (the first steps are finer than the gray levels), within 2 % of the white
    err = np.abs(light(lut[pattern], white) - pattern / 255.0)[16:]
    assert err.max() < 0.02


def test_without_the_lut_the_response_is_far_from_linear():
    mid = np.arange(256)[128]
    assert abs(light(mid) - mid / 255.0) > 0.2           # mid-gray gives about a quarter of the light


def test_binary_patterns_are_unchanged_up_to_the_white_level():
    lut = build_lut(LEVELS, RESPONSE, 100)
    binary = np.array([[0, 255], [255, 0]], np.uint8)
    assert np.array_equal(apply_lut(binary, lut), np.array([[0, 100], [100, 0]], np.uint8))


def test_float_patterns_use_the_same_table():
    lut = build_lut(LEVELS, RESPONSE, 255)
    out = apply_lut(np.array([0.0, 0.5, 1.0]), lut)
    assert out[0] == 0 and out[2] == 1.0 and np.isclose(out[1] * 255, np.interp(127.5, np.arange(256), lut))
    ints = np.array([1, 2], np.int32)
    assert apply_lut(ints, lut) is ints


def test_dead_levels_and_noise_do_not_break_the_inversion():
    noisy = np.array(RESPONSE) + np.random.default_rng(0).normal(0, 3e-4, len(RESPONSE))
    lut = build_lut(LEVELS, noisy, 255)
    assert np.all(np.diff(lut.astype(int)) >= 0) and lut[1] > 0


def test_a_response_without_light_is_refused():
    with pytest.raises(ValueError):
        build_lut([0, 255], [0.0, 0.0])


def test_load_lut_reads_a_probe_file(tmp_path):
    import json
    path = tmp_path / "curve.json"
    path.write_text(json.dumps({"levels": LEVELS, "response": RESPONSE}))
    assert np.array_equal(load_lut(path, 100), build_lut(LEVELS, RESPONSE, 100))


def test_probe_keeps_only_bands_that_are_lit_but_not_saturated():
    from app.cli.probe_gray_response import light_curve, usable_bands
    mask = usable_bands([100, 5000, 30000, 49000, 52000, 65000])
    assert mask.tolist() == [False, True, True, True, False, False]
    response, repeat = light_curve([0, 128, 255], [0, 40, 100], [2, 44, 100], 100, 100)
    assert np.allclose(response, [0.01, 0.42, 1.0]) and np.isclose(repeat, 0.04)
