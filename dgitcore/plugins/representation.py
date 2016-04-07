#!/usr/bin/env python

import os, sys
import json
from collections import namedtuple

Key = namedtuple("Key", ["name","version"])

class RepresentationBase(object):
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

    def __str__(self): 
        return self.name 

    def initialize(self):
        return

    def config(self, what='get', params=None):
        return

    def can_process(self, filename): 
        return False 
        
    def get_schema(self, filename):
        return []
    
    def get_diff(self, filename1, filename2): 
        return [] 
