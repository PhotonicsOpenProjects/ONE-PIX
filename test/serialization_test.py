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


# ---------------------------------------------------------------- compact storage of large arrays

@pytest.mark.parametrize("dtype", [np.float32, np.int32, np.uint16, np.bool_, np.complex64])
def test_large_arrays_are_stored_as_binary_and_come_back_unchanged(tmp_path, dtype):
    a = (RNG.random((30, 40, 10)) * 5000).astype(dtype)
    path = tmp_path / "x.json"
    utils.save_dict_json({"a": a}, path)
    assert '"encoding": "base64"' in path.read_text()
    back = utils.load_dict_json(path)["a"]
    assert back.dtype == a.dtype and back.shape == a.shape and back.flags.writeable
    np.testing.assert_array_equal(back, a)


def test_the_file_is_much_smaller_and_the_small_arrays_stay_readable(tmp_path):
    big = RNG.random((41, 41, 100)).astype(np.float32)
    small = np.array([1.5, 2.5, 3.5], dtype=np.float32)
    binary, text = tmp_path / "binary.json", tmp_path / "text.json"
    utils.save_dict_json({"big": big, "small": small, "metadata": {"imaging_method_name": "fouriershift"}}, binary)
    text.write_text(__import__("json").dumps({"big": big.astype(float).tolist()}))
    assert binary.stat().st_size < 0.5 * text.stat().st_size
    content = binary.read_text()
    assert '"imaging_method_name": "fouriershift"' in content           # metadata stays readable
    assert '"data": [\n' in content and "1.5" in content                 # a small array stays a list
    np.testing.assert_array_equal(utils.load_dict_json(binary)["small"], small)


def test_files_written_before_the_binary_format_still_load(tmp_path):
    old = {"a": {"__type__": "ndarray", "dtype": "float32", "shape": [2, 5], "data": [[0.5] * 5, [1.5] * 5]}}
    path = tmp_path / "old.json"
    path.write_text(__import__("json").dumps(old))
    back = utils.load_dict_json(path)["a"]
    assert back.dtype == np.float32 and back.shape == (2, 5) and back[1, 0] == 1.5


def test_byte_order_and_memory_layout_do_not_matter(tmp_path):
    base = RNG.random((60, 70)).astype(np.float32)
    for a in (base.astype(">f4"), np.asfortranarray(base), base[::2, ::3], base.T):
        back = round_trip(tmp_path, a)
        assert back.shape == a.shape
        np.testing.assert_array_equal(back, a)


def test_float64_is_still_stored_as_float32(tmp_path):
    a = RNG.random((50, 50, 3))
    back = round_trip(tmp_path, a.astype(np.float64))
    assert back.dtype == np.float32
    np.testing.assert_allclose(back, a, rtol=1e-6)


def test_the_binary_form_can_be_turned_off_for_readers_that_do_not_know_it(tmp_path, monkeypatch):
    a = RNG.random((30, 40, 10)).astype(np.float32)
    path = tmp_path / "x.json"
    for value in ("0", "false", "off", "No"):
        monkeypatch.setenv("ONEPIX_COMPACT_JSON", value)
        utils.save_dict_json({"a": a}, path)
        assert '"encoding"' not in path.read_text()
        np.testing.assert_array_equal(utils.load_dict_json(path)["a"], a)

    monkeypatch.setenv("ONEPIX_COMPACT_JSON", "1")
    utils.save_dict_json({"a": a}, path)
    assert '"encoding": "base64"' in path.read_text()
