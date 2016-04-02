#!/usr/bin/env python
"""
Interfaces to dgit plugins
"""

__all__ = []

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        globals()[var] = getattr(mod, var)

from ..plugins import common
_reexport(common)
