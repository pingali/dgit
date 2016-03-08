#!/usr/bin/env python 

import os, sys
from dgitcore.validator import ValidatorBase
from dgitcore.config import get_config 
from dgitcore.helper import compute_sha256 

class ValidatorDefault(ValidatorBase):     
    """
    Simple validator backend for the datasets.

    Parameters
    ----------
    """
    def __init__(self): 
        self.enable = False 
        self.token = None 
        self.url = None 
        super(ValidatorDefault, self).__init__('basic-validator', 
                                              'v0', 
                                              "Basic validator of the content")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'basic-validator', 
                'nature': 'validator',
                'variables': ['enable'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable Validator server?" 
                    },            
                }
            }
        else:
            try: 
                self.enable = params['basic-validator']['enable']
            except:
                self.enable = 'n'

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
    
    obj = ValidatorDefault()
    mgr.register('validator', obj)


