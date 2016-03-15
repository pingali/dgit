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

    def evaluate(self, repomanager, key): 
        """
        Evaluate the repo
        
        Parameters
        ----------

        repo manager
        repo
        """
        repo = repomanager.get_repo_details(key)    
        rootdir = repo['rootdir']    
        package = repo['package'] 
        
        files = package['resources'] 
        print('files', len(files))
        for f in files: 
            print(f['relativepath'])
            coded_sha256 = f['sha256'] 
            computed_sha256 = compute_sha256(os.path.join(rootdir,
                                                          f['relativepath']))
            if computed_sha256 != coded_sha256: 
                print("Sha 256 mismatch between file and datapackage")
    


    
def setup(mgr): 
    
    obj = ChecksumValidator()
    mgr.register('validator', obj)


