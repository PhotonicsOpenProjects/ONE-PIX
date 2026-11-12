"""save_dict_json / load_dict_json must give back what was saved (onepix/utils.py)."""
import numpy as np
import pytest

from onepix import utils

RNG = np.random.default_rng(0)


def round_trip(tmp_path, value):
    path = tmp_path / "x.json"
    utils.save_dict_json({"value": value}, path)
    return utils.load_dict_json(path)["value"]


@pytest.mark.parametrize("shape", [(5, 6, 1), (5, 6, 3), (5, 6, 4), (40, 40, 3), (70, 70, 3), (70, 70, 4), (70, 70), (100, 100)])
@pytest.mark.parametrize("dtype", [np.float32, np.uint16, np.int32])
def test_arrays_that_look_like_images_but_are_not_8_bit_keep_their_values(tmp_path, shape, dtype):
    a = (RNG.random(shape) * 5000).astype(dtype)
    back = round_trip(tmp_path, a)
    assert back.dtype == a.dtype and back.shape == a.shape
    np.testing.assert_array_equal(back, a)


def test_float64_maps_come_back_as_float32_values_not_8_bit(tmp_path):
    a = RNG.random((100, 100))                      # an index map in 0-1
    back = round_trip(tmp_path, a)
    assert back.dtype == np.float32
    np.testing.assert_allclose(back, a, rtol=1e-6)


@pytest.mark.parametrize("shape", [(21, 21, 3), (5, 6, 4), (80, 90), (5, 6, 1)])
def test_8_bit_images_are_still_stored_losslessly_as_png(tmp_path, shape):
    a = RNG.integers(0, 256, shape, dtype=np.uint8)
    path = tmp_path / "x.json"
    utils.save_dict_json({"img": a}, path)
    assert '"image_png"' in path.read_text()
    back = utils.load_dict_json(path)["img"]
    assert back.dtype == np.uint8 and back.shape == a.shape
    np.testing.assert_array_equal(back, a)


def test_masks_round_trip_as_booleans(tmp_path):
    mask = RNG.random((80, 80)) > 0.5
    back = round_trip(tmp_path, mask)
    assert back.dtype == bool
    np.testing.assert_array_equal(back, mask)


def test_a_datacube_with_many_bands_is_unchanged(tmp_path):
    cube = RNG.random((11, 11, 1610)).astype(np.float32)
    np.testing.assert_array_equal(round_trip(tmp_path, cube), cube)
