#!/usr/bin/env python

from .config import init as config_init 
from .plugins import plugins_load 

# Load available repos 
plugins_load() 
config_init()

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        globals()[var] = getattr(mod, var)

__all__ = []

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        globals()[var] = getattr(mod, var)

from dgitcore import datasets, plugins 
_reexport(datasets)
_reexport(plugins)
