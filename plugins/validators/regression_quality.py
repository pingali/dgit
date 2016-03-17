#!/usr/bin/env python 

import os, sys, glob2, json 
import re 
from dgitcore.plugins.validator import ValidatorBase
from dgitcore.config import get_config 
from dgitcore.helper import compute_sha256, cd 

class RegressionQualityValidator(ValidatorBase):     
    """
    Validate repository metdata

    Parameters
    ----------
    """
    def __init__(self): 
        self.enable = 'y'
        super(RegressionQualityValidator, self).__init__('regression-quality-validator', 
                                                         'v0', 
                                                         "Check R2 of regression model")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'regression-quality-validator', 
                'nature': 'validator',
                'variables': ['enable'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable repository regression-quality checker"
                    },            
                }
            }
        else:
            if (('regression-quality-validator' in params) and 
                'enable' in params['regressio-quality-validator']): 
                self.enable = params['regression-quality-validator']['enable']
            else: 
                self.enable = 'y'

    def evaluate(self, repo, files, rules): 
        """
        Evaluate the files identified for checksum. 
        """

        status = []

        
        with cd(repo.rootdir): 
            rules = dict([(r, json.loads(open(r).read())) for r in rules])
            files = dict([(f, open(f).read()) for f in files])
            
            for r in rules: 
                if 'min-r2' not in rules[r]: 
                    continue
                minr2 = rules[r]['min-r2'] 
                for f in files:       
                    match = re.search(r"R-squared:\s+(\d.\d+)", files[f])
                    if match is None: 
                        status.append({
                            'target': "{} with {}".format(f, r),
                            'status': "ERROR",
                            'message': "Invalid model output"
                            })
                    else: 
                        r2 = match.group(1) 
                        r2 = float(r2)
                        if r2 > minr2: 
                            status.append({
                                'target': "{} with {}".format(f, r),
                                'status': "OK",
                                'message': "Acceptable R2"
                            })
                        else: 
                            status.append({
                                'target': "{} with {}".format(f, r),
                                'status': "ERROR",
                                'message': "R2 is too low"
                            })

        return status 
    
def setup(mgr): 
    
    obj = RegressionQualityValidator()
    mgr.register('validator', obj)


