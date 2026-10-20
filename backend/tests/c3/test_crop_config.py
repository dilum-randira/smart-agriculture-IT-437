"""Checks that the crop settings in config.py match their stated sources.

The values are a PROXY (FAO-56 bell pepper), not Nai Miris data.
"""

from app.c3 import config


def test_crop_is_nai_miris():
    assert "Nai Miris" in config.CROP_NAME


def test_kc_values_match_fao56_table12_bell_pepper():
    assert config.KC_MID == 1.05
    assert config.KC_END == 0.90
    assert config.KC_INI is None  # not checked yet, so deliberately left empty


def test_root_depth_and_p_match_fao56_table22_bell_pepper():
    assert config.ROOT_DEPTH_MIN_M == 0.5
    assert config.ROOT_DEPTH_MAX_M == 1.0
    assert config.DEPLETION_FRACTION_P == 0.30
    assert config.ROOT_DEPTH_MIN_M < config.ROOT_DEPTH_MAX_M
