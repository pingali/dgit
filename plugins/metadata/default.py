#!/usr/bin/env python 

import os, sys
from dgitcore.plugins.metadata import MetadataBase
from dgitcore.config import get_config 

class MetadataDefault(MetadataBase):     
    """
    Metadata backend for the datasets.

    Parameters
    ----------
    Configuration (token) 
    """
    def __init__(self): 
        self.enable = False 
        self.token = None 
        self.url = None 
        super(MetadataDefault, self).__init__('generic-metadata', 
                                              'v0', 
                                              "Basic metadata tracker")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'generic-metadata', 
                'nature': 'metadata',
                'variables': ['enable', 'token', 'url'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable Metadata server?" 
                    },            
                    'token': {
                        'value': '',
                        'description': 'Provide API token to be used for posting',
                    },
                    'url': {
                        'value': '',
                        'description': 'URL to which metadata should be posted'
                    },
                }
            }
        else:
            try: 
                self.enable = params['generic-metadata']['enable']
            except:
                self.enable = 'n'
                return 
                
            metadata = params['generic-metadata']
            self.enable     = metadata['enable']
            self.token      = metadata.get('token', None)
            self.url        = metadata.get('url', None) 
            if self.enable == 'y': 
                if self.token is None:
                    print("If metadata is enabled, Token should be provided")
                    raise Exception("Invalid configuration")
                if self.url is None:
                    print("If metadata is enabled, Token should be provided")
                    raise Exception("Invalid configuration")

    
def setup(mgr): 
    
    obj = MetadataDefault()
    mgr.register('metadata', obj)


