#!/usr/bin/env python
"""
dgit datasets API

.. currentmodule:: dgitcore.datasets

"""

__all__ = []

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        globals()[var] = getattr(mod, var)

from ..datasets import common, files, validation, auto, transformation

_reexport(common)
_reexport(files)
_reexport(validation)
_reexport(auto)
_reexport(transformation)
