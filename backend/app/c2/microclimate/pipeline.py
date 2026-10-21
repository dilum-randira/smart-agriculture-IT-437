"""Compatibility entry point; implementation moved to preprocessing.pipeline."""
from importlib import import_module as _import_module

_impl = _import_module("app.c2.microclimate.preprocessing.pipeline")
__all__ = [name for name in vars(_impl) if not name.startswith("_")]
globals().update({name: getattr(_impl, name) for name in __all__})


def __getattr__(name):
    return getattr(_impl, name)
