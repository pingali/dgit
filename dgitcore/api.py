#!/usr/bin/env python

from .config import init as config_init 
from .plugins import load as plugins_load 

# Load available repos 
plugins_load() 
config_init()

from dgitcore import datasets, plugins 
