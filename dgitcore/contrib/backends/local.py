#!/usr/bin/env python
"""
Implements a simple filesystem-based backend for dgit.

[Local] section:

* workspace: Directory to be used by dgit for storing repositories

"""
import os, sys
from dgitcore.config import NonEmptyValidator
from dgitcore.plugins.backend import BackendBase

class LocalBackend(BackendBase):
    """
    Filesystem based backend
    """
    def __init__(self):

        self.enable = 'y'
        self.workspace = None
        super(LocalBackend,self).__init__('local', 'v0',
                                          "Local Filesystem Backend")

    def url_is_valid(self, url):
        """
        Check if a URL exists
        """
        # Check if the file system path exists...
        if url.startswith("file://"):
            url = url.replace("file://","")

        return os.path.exists(url)


    def config(self, what='get', params=None):
        if what == 'get':
            return {
                'name': 'Local',
                'variables': ['workspace'],
                'nature': 'backend',
                'defaults': {
                    'workspace': {
                        "value": os.path.join(os.environ['HOME'], '.dgit'),
                        "description": "Local directory to store datasets",
                        'validator': NonEmptyValidator()
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



