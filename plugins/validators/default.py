#!/usr/bin/env python 

import os, sys
from dgitcore.plugins.validator import ValidatorBase
from dgitcore.config import get_config 
from dgitcore.helper import compute_sha256 

class ChecksumValidator(ValidatorBase):     
    """
    Simple validator backend for the datasets.

    Parameters
    ----------
    """
    def __init__(self): 
        self.enable = False 
        self.token = None 
        self.url = None 
        super(ChecksumValidator, self).__init__('checksum-validator', 
                                              'v0', 
                                              "Validate checksum for all files")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'checksum-validator', 
                'nature': 'validator',
                'variables': ['enable'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable checksum validation?" 
                    },            
                }
            }
        else:
            self.enable = params['checksum-validator']['enable']

    def evaluate(self, repo, files, rules): 
        """
        Evaluate the files identified for checksum. 
        """
        
        print(self.name)
        for f in files: 
            r = repo.get_resource(f)
            coded_sha256 = r['sha256']             
            computed_sha256 = compute_sha256(r['localfullpath'])
            if computed_sha256 != coded_sha256: 
                print("Sha 256 mismatch between file and datapackage")
            else: 
                print(f,": OK")
    


    
def setup(mgr): 
    
    obj = ChecksumValidator()
    mgr.register('validator', obj)


