#!/usr/bin/env python 

import os, sys
from dgitcore.plugins.validator import ValidatorBase
from dgitcore.config import get_config 
from dgitcore.helper import compute_sha256 

class MetadataValidator(ValidatorBase):     
    """
    Validate repository metdata

    Parameters
    ----------
    """
    def __init__(self): 
        self.enable = 'y'
        super(MetadataValidator, self).__init__('metadata-validator', 
                                               'v0', 
                                               "Validate integrity of the repository")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'metadata-validator', 
                'nature': 'validator',
                'variables': ['enable'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable repository metadata"
                    },            
                }
            }
        else:
            if (('checksum-validator' in params) and 
                'enable' in params['checksum-validator']): 
                self.enable = params['checksum-validator']['enable']
            else: 
                self.enable = 'y'

    def evaluate(self, repo, files, rules): 
        """
        Evaluate the files identified for checksum. 
        """
        print("Evaluating", files, rules)
        status = []
        for f in files: 
            status.append({
                'file': f,
                'status': 'OK',
                'message': ""
            })
        return status 

    
def setup(mgr): 
    
    obj = MetadataValidator()
    mgr.register('validator', obj)


