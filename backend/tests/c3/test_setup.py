"""Stage 1 tests. Run from backend/ with:  python -m pytest tests/c3"""

from app.c3 import config


def test_schedule_covers_seven_days():
    assert config.SCHEDULE_DAYS == 7


def test_data_folder_is_inside_backend():
    assert config.DATA_DIR.parent == config.BACKEND_DIR


def test_pymoo_has_nsga2():
    from pymoo.algorithms.moo.nsga2 import NSGA2

    assert NSGA2 is not None
