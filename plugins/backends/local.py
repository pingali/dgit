#!/usr/bin/env python 

import os, sys
from dgitcore.backend import BackendBase, BackendContext

class LocalBackend(BackendBase): 
    """
    Filesystem based backend 
    """
    def __init__(self): 
        
        self.workspace = None 
        super(LocalBackend,self).__init__('local', 'v0',
                                          "Local filesystem backend")
    def initialize(self, connect=False): 
        pass
        
    def config(self, what='get', params=None): 
        if what == 'get': 
            return {
                'name': 'Local', 
                'variables': ['workspace'],
                'nature': 'backend',
                'defaults': { 
                    'workspace': {
                        "value": os.path.join(os.environ['HOME'], '.dgit'),
                        "description": "Local directory to store datasets"
                    },
                }
            }
        else: 
            self.workspace = params['Local']['workspace']

    def connect(self):
        pass 
        
    def push(self):
        pass 
        
    def pull(self):
        pass 

def setup(mgr): 
    
    obj = LocalBackend()
    mgr.register('backend', obj)



