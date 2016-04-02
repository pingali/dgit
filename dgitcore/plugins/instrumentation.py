#!/usr/bin/env python

import os, sys
import json
from collections import namedtuple

Key = namedtuple("Key", ["name","version"])

class InstrumentationBase(object):
    """
    Pre-computed patterns
    """
    def __init__(self, name, version, description, supported=[]):
        self.enable = 'y'
        self.name = name
        self.version = version
        self.description = description
        self.support = supported + [name]
        self.initialize()

    def initialize(self):
        return

    def config(self, what='get', params=None):
        return
