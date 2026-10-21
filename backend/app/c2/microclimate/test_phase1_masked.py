"""Compatibility entry point; implementation moved to preprocessing.tests.test_phase1_masked."""
from importlib import import_module as _import_module

_impl = _import_module("app.c2.microclimate.preprocessing.tests.test_phase1_masked")
__all__ = [name for name in vars(_impl) if not name.startswith("_")]
globals().update({name: getattr(_impl, name) for name in __all__})


def __getattr__(name):
    return getattr(_impl, name)


def load_tests(loader, tests, pattern):
    # Discovery finds canonical packages; explicit legacy module names still run.
    import unittest
    return loader.loadTestsFromModule(_impl) if pattern is None else unittest.TestSuite()


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
