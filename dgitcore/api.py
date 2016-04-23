#!/usr/bin/env python

import os, sys
import dgitcore 
from dgitcore import datasets, plugins, config  
from dgitcore.config import get_config 

__all__ = ['get_config', 'initialize']



def api_call_action(func): 
    """
    API wrapper documentation
    """
    def _inner(*args, **kwargs):
        return func(*args, **kwargs)
    _inner.__name__ = func.__name__
    _inner.__doc__ = func.__doc__
    return _inner 

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        base = getattr(mod, var)
        f = api_call_action(base)
        globals()[var] = f 


def initialize():
    plugins.plugins_load()
    config.init()

# What all should be exported
_reexport(datasets)
_reexport(plugins)

