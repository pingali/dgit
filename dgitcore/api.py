#!/usr/bin/env python

from .config import init as config_init, get_config
from .plugins import plugins_load
from dgitcore import datasets, plugins

__all__ = ['get_config', 'initialize']


def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        globals()[var] = getattr(mod, var)


def initialize():
    plugins_load()
    config_init()

# What all should be exported
initialize()
_reexport(datasets)
_reexport(plugins)
