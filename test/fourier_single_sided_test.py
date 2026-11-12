"""fouriershift single-sided mode, and the fouriersplit dependency on fouriershift.

These tests run against the installed plugins. The versions before the single-sided mode
(onepix-fouriershift 0.1.3) are in test/fixtures/fouriershift_0.1.3/."""
import importlib.machinery
import importlib.util
import os

import numpy as np
import pytest

# these tests exercise the installed fouriershift / fouriersplit plugins: skipped without the single-sided mode
pytest.importorskip("fouriershift._single_sided", reason="needs a fouriershift with the single-sided mode")
pytest.importorskip("fouriersplit")

from fouriershift import PatternsCreation as shift_patterns
from fouriershift.ImageReconstruction import Reconstruction as ShiftReconstruction
from fouriersplit import PatternsCreation as split_patterns
from fouriersplit.ImageReconstruction import Reconstruction as SplitReconstruction

BANDS = 3
REFERENCE_SOURCES = os.path.join(os.path.dirname(__file__), "fixtures", "fouriershift_0.1.3")


# The resolution is set here, not read from the plugin: onepix-fis-common-function changed its default
# (21, then 5) and the scene below has a bright block that needs a cube of at least 12 pixels.
SIZE = 21


@pytest.fixture(autouse=True)
def fixed_spatial_resolution(monkeypatch):
    from fis_common_function import FIS_common_acquisition as FIS
    monkeypatch.setattr(FIS.FisCommonAcquisition, "_load_json", lambda self, path: {"spatial_res": SIZE})


def scene(seed=0):
    rng = np.random.default_rng(seed)
    cube = rng.uniform(0.1, 1.0, (SIZE, SIZE, BANDS))
    cube[3:8, 5:12] += 1.0
    return cube


def measure(patterns, cube, lamp=None, background=None):
    n = len(patterns)
    lamp = np.ones(n) if lamp is None else lamp
    background = np.zeros(n) if background is None else background
    return np.array([lamp[i] * np.tensordot(np.asarray(p, float) / 255.0, cube, axes=([0, 1], [0, 1])) + background[i]
                     for i, p in enumerate(patterns)])


def shift_creator(**settings):
    c = shift_patterns.CreationPatterns(SIZE, SIZE)
    c.load_settings = lambda: dict(shift_patterns.DEFAULT_SETTINGS, **settings)
    return c


def shift_acquisition(c, patterns, spectra):
    r = c.acquisition_results
    return dict(r, spectra=spectra, wavelengths=np.arange(BANDS))


def load_orig(name):
    path = os.path.join(REFERENCE_SOURCES, name + ".py")
    loader = importlib.machinery.SourceFileLoader("orig_" + name, path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# --- what fouriersplit relies on -------------------------------------------------------------

def test_creation_freq_patterns_still_returns_the_signed_patterns():
    c = shift_patterns.CreationPatterns(SIZE, SIZE)
    for freq in [(0, 0), (1, -2), (4, 3)]:
        preal, pim = c.creation_freq_patterns(freq)
        j, k = freq
        angle = 2 * np.pi * (c.X * k / SIZE + c.Y * j / SIZE)
        assert preal.dtype == pim.dtype == np.float32 and preal.shape == (SIZE, SIZE)
        assert np.allclose(preal, np.cos(angle), atol=1e-5) and np.allclose(pim, np.sin(angle), atol=1e-5)


def test_creation_freq_patterns_is_unchanged_from_the_original_module():
    orig = load_orig("PatternsCreation")
    new, old = shift_patterns.CreationPatterns(SIZE, SIZE), orig.CreationPatterns(SIZE, SIZE)
    for freq in [(0, 0), (2, 5), (7, -3)]:
        assert all(np.array_equal(a, b) for a, b in zip(new.creation_freq_patterns(freq), old.creation_freq_patterns(freq)))


def test_constructing_the_shift_patterns_never_reads_the_single_sided_config():
    c = shift_patterns.CreationPatterns(SIZE, SIZE)
    assert c.settings == shift_patterns.DEFAULT_SETTINGS and hasattr(c, "fis") and hasattr(c, "spatial_res")


def test_fouriersplit_patterns_are_unchanged():
    c = split_patterns.CreationPatterns(SIZE, SIZE)
    c.creation_patterns()
    s = (SIZE - 1) // 2
    patterns = c.acquisition_results["patterns"]
    assert len(patterns) == 4 * (s + 1) * (2 * s + 1) and all(p.dtype == np.uint8 for p in patterns)
    assert not any(n in ("open", "closed") for n in c.acquisition_results["patterns_order"])
    pos_r, neg_r, pos_im, neg_im = c.creation_freq_patterns((2, 3))
    preal, pim = c.fourier_shift.creation_freq_patterns((2, 3))
    assert np.array_equal(pos_r, np.uint8(255 * np.where(preal > 0, preal, 0)))
    assert np.array_equal(neg_im, np.uint8(255 * np.where(pim < 0, abs(pim), 0)))


# --- single-sided mode -------------------------------------------------------------------------

def test_single_sided_patterns_are_displayable_and_fewer_than_split():
    c = shift_creator(ref_every=16)
    patterns = c.creation_patterns()
    order = c.acquisition_results["patterns_order"]
    s = (SIZE - 1) // 2
    n_coeff = 2 * (s + 1) * (2 * s + 1)
    assert len(patterns) == len(order) == c.nb_patterns
    assert n_coeff < len(patterns) < 4 * (s + 1) * (2 * s + 1)
    assert order[:2] == ["open", "closed"] and order[-2:] == ["open", "closed"]
    assert all(p.dtype == np.uint8 and p.shape == (SIZE, SIZE) for p in patterns)
    assert patterns[0].min() == 255 and patterns[1].max() == 0
    k = order.index("preal(%d,0)" % s)
    expected = np.uint8(np.round(255 * (1 + c.creation_freq_patterns((0, 0))[0]) / 2))
    assert np.array_equal(patterns[k], expected) and expected.min() == 255      # frequency 0: the whole field


def test_single_sided_equals_fouriersplit_without_drift():
    cube = scene()
    c = shift_creator()
    patterns = c.creation_patterns()
    single = ShiftReconstruction(shift_acquisition(c, patterns, measure(patterns, cube))).image_reconstruction()
    sc = split_patterns.CreationPatterns(SIZE, SIZE)
    sc.creation_patterns()
    sp = sc.acquisition_results
    split = SplitReconstruction(dict(sp, spectra=measure(sp["patterns"], cube), wavelengths=np.arange(BANDS))
                                ).image_reconstruction()
    # both are limited by the 8 bit patterns: each within 1 % of the scene, and of each other
    relative = lambda a, b: np.linalg.norm(a - b) / np.linalg.norm(b)
    assert relative(single, cube) < 0.015 and relative(split, cube) < 0.015 and relative(single, split) < 0.015


def test_lamp_and_background_drift_are_corrected():
    cube = scene()
    c = shift_creator(ref_every=8)
    patterns = c.creation_patterns()
    n = len(patterns)
    t = np.linspace(0, 1, n)
    spectra = measure(patterns, cube, lamp=1 - 0.25 * t, background=0.3 * t + 0.2 * t ** 2)
    out = ShiftReconstruction(shift_acquisition(c, patterns, spectra)).image_reconstruction()
    assert np.linalg.norm(out - cube) / np.linalg.norm(cube) < 0.05

    c2 = shift_creator(ref_every=8, drift="offset")
    patterns2 = c2.creation_patterns()
    out2 = ShiftReconstruction(shift_acquisition(c2, patterns2, measure(patterns2, cube, lamp=1 - 0.25 * t[:len(patterns2)],
                                                                         background=0.3 * t[:len(patterns2)]))).image_reconstruction()
    assert np.linalg.norm(out2 - cube) > np.linalg.norm(out - cube)


def test_legacy_mode_and_legacy_data_are_kept():
    orig_patterns, orig_recon = load_orig("PatternsCreation"), load_orig("ImageReconstruction")
    c = shift_creator(single_sided=False)
    patterns = c.creation_patterns()
    old = orig_patterns.CreationPatterns(SIZE, SIZE)
    old_patterns = old.creation_patterns()
    assert len(patterns) == len(old_patterns) and all(np.array_equal(a, b) for a, b in zip(patterns, old_patterns))
    assert c.acquisition_results["patterns_order"] == old.acquisition_results["patterns_order"]
    spectra = np.random.default_rng(0).uniform(0, 1, (len(patterns), BANDS))
    acq = {"spectra": spectra, "patterns_order": c.acquisition_results["patterns_order"], "wavelengths": np.arange(BANDS)}
    assert np.array_equal(ShiftReconstruction(acq).image_reconstruction(), orig_recon.Reconstruction(acq).image_reconstruction())


def test_a_saturated_open_field_is_flagged():
    cube = scene()
    c = shift_creator()
    patterns = c.creation_patterns()
    spectra = measure(patterns, cube)
    rec = ShiftReconstruction(shift_acquisition(c, patterns, spectra))
    rec.image_reconstruction()
    assert rec.reconstruction_results["saturation_suspected"] is False
    clipped = spectra.copy()
    for i, name in enumerate(c.acquisition_results["patterns_order"]):
        if name == "open":
            clipped[i] *= 0.6
    rec = ShiftReconstruction(shift_acquisition(c, patterns, clipped))
    rec.image_reconstruction()
    assert rec.reconstruction_results["saturation_suspected"] is True


# --- reconstruction compensating the display's non-linearity and the noise -----------------------------

def measure_nonlinear(patterns, cube, a=0.15):
    """A display whose light is x + a x (1 - x) for a pattern level x: white and black are exact, the
    complement identity open - P' = P'' is not."""
    out = []
    for p in patterns:
        x = np.asarray(p, float) / 255.0
        out.append(np.tensordot(x + a * x * (1 - x), cube, axes=([0, 1], [0, 1])))
    return np.array(out)


def reconstruct(c, patterns, spectra, **options):
    return ShiftReconstruction(dict(shift_acquisition(c, patterns, spectra), **options))


def test_common_bias_of_a_non_linear_display_is_removed():
    cube = scene()
    c = shift_creator()
    patterns = c.creation_patterns()
    spectra = measure_nonlinear(patterns, cube)
    rel = lambda out: np.linalg.norm(out - cube) / np.linalg.norm(cube)
    plain = reconstruct(c, patterns, spectra, bias_correction=False)
    fixed = reconstruct(c, patterns, spectra, bias_correction=True)
    err_plain, err_fixed = rel(plain.image_reconstruction()), rel(fixed.image_reconstruction())
    assert err_plain > 0.2 and err_fixed < err_plain / 2
    assert plain.reconstruction_results["saturation_suspected"] is True
    assert fixed.reconstruction_results["saturation_suspected"] is False
    assert fixed.reconstruction_results["common_bias_percent"] > 0          # the bias that was removed


def test_bias_correction_leaves_a_linear_display_untouched():
    cube = scene()
    c = shift_creator()
    patterns = c.creation_patterns()
    spectra = measure(patterns, cube)
    a = reconstruct(c, patterns, spectra, bias_correction=False).image_reconstruction()
    b = reconstruct(c, patterns, spectra, bias_correction=True).image_reconstruction()
    assert np.linalg.norm(a - b) / np.linalg.norm(a) < 0.01


def test_low_rank_denoising_keeps_the_scene_and_removes_noise():
    rng = np.random.default_rng(5)
    abundance = rng.uniform(0, 1, (SIZE, SIZE, 2))
    spectra_basis = np.abs(rng.normal(1, 0.5, (2, 60)))
    cube = abundance @ spectra_basis                                          # two materials, 60 bands
    global BANDS
    previous, BANDS = BANDS, 60
    try:
        c = shift_creator()
        patterns = c.creation_patterns()
        clean = measure(patterns, cube)
        noisy = clean + rng.normal(0, 0.05 * clean.std(), clean.shape)
        rel = lambda out: np.linalg.norm(out - cube) / np.linalg.norm(cube)
        raw = rel(reconstruct(c, patterns, noisy, denoise_rank=0).image_reconstruction())
        low = rel(reconstruct(c, patterns, noisy, denoise_rank=2).image_reconstruction())
        no_noise = rel(reconstruct(c, patterns, clean, denoise_rank=2).image_reconstruction())
    finally:
        BANDS = previous
    assert low < raw * 0.7 and no_noise < 0.02
