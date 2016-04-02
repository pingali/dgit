#!/usr/bin/env python

import dgitcore 
from dgitcore.config import init as config_init, get_config
from dgitcore.plugins import plugins_load

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
_reexport(dgitcore.datasets)
_reexport(dgitcore.plugins)
