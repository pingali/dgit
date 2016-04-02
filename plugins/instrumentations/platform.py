#!/usr/bin/env python

import os, sys
from dgitcore.plugins.instrumentation import InstrumentationBase
from dgitcore.config import get_config
import platform
import getpass

class PlatformInstrumentation(InstrumentationBase):
    """
    Instrumentation to extract platform-specific information
    """
    def __init__(self):
        super(PlatformInstrumentation, self).__init__('platform',
                                                      'v0',
                                                      "Execution platform information")

    def get_metadata(self):
        return {
            'client': {
                'name': platform.node(),
                'os': platform.system(),
                'release': platform.release(),
                'processor': platform.processor(),
                'python': platform.python_version(),
                'distribution': platform.linux_distribution()
            },
            'ownership': {
                'user': getpass.getuser()
            }
        }

    def update(self, config):
        metadata = self.get_metadata()
        config['metadata'].update(metadata['client'])
        config['ownership'].update(metadata['ownership'])
        return config

def setup(mgr):

    obj = PlatformInstrumentation()
    mgr.register('instrumentation', obj)


