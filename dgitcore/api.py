#!/usr/bin/env python

import dgitcore 
from dgitcore import datasets, plugins, config  
from dgitcore.config import get_config 

__all__ = ['get_config', 'initialize']



def api_call_action(func): 
    """
    API wrapper documentation
    """
    def inner(*args, **kwargs):
        func(*args, **kwargs)
        return inner
    return inner 

def _reexport(mod):
    __all__.extend(mod.__all__)
    for var in mod.__all__:
        base = getattr(mod, var)
        f = api_call_action(base)
        f.__doc__ = base.__doc__
        globals()[var] = f 


def initialize():
    plugins.plugins_load()
    config.init()

# What all should be exported
_reexport(datasets)
_reexport(plugins)

