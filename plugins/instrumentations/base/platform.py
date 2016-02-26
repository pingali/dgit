#!/usr/bin/env python 

import os, sys
from dgitcore.instrumentation import InstrumentationBase, InstrumentationHelper
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

    def update(self, config):
        config['metadata'].update({ 
            'client': {
                'name': platform.node(),
                'os': platform.system(),
                'os-release': platform.release(),
                'processor': platform.processor(),
                'python': platform.python_version(),
                'distribution': platform.linux_distribution()
            },
        })
        config['ownership'].update({ 
                'user': getpass.getuser()
        })

        return config 
    
def setup(mgr): 
    
    obj = PlatformInstrumentation()
    mgr.register('instrumentation', obj)


