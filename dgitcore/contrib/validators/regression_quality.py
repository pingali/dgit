#!/usr/bin/env python

import os, sys, glob2, json
from collections import OrderedDict
import re
from dgitcore.plugins.validator import ValidatorBase
from dgitcore.config import get_config
from dgitcore.helper import compute_sha256, cd
from dgitcore.exceptions import * 

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
                'enable' in params['regression-quality-validator']):
                self.enable = params['regression-quality-validator']['enable']
            else:
                self.enable = 'n'

    def autooptions(self):
        return OrderedDict([
            ("files", ["*.txt"]),
            ("rules", OrderedDict([
                ("min-r2", 0.25)
            ])),
            ("rules-files",[])
        ])

    def evaluate(self, repo, spec, args):
        """
        Evaluate the files identified for checksum.
        """

        status = []

        # Do we have to any thing at all? 
        if len(spec['files']) == 0: 
            return status 

        with cd(repo.rootdir):
            
            rules = None 
            if 'rules-files' in spec and len(spec['rules-files']) > 0: 
                rulesfiles = spec['rules-files']
                rules = dict([(f, json.loads(open(f).read())) for f in rulesfiles])
            elif 'rules' in spec: 
                rules = {
                    'inline': spec['rules'] 
                }
                
            if rules is None or len(rules) == 0:
                print("Regression quality validation has been enabled but no rules file has been specified")
                print("Example: { 'min-r2': 0.25 }. Put this either in file or in dgit.json")
                raise InvalidParameters("Regression quality checking rules missing")

            files = dict([(f, open(f).read()) for f in spec['files']])

            for r in rules:
                if 'min-r2' not in rules[r]:
                    continue
                minr2 = float(rules[r]['min-r2'])
                for f in files:
                    match = re.search(r"R-squared:\s+(\d.\d+)", files[f])
                    if match is None:
                        status.append({
                            'target': f,
                            'validator': self.name,
                            'description': self.description,
                            'rules': r,
                            'status': "ERROR",
                            'message': "Invalid model output"
                            })
                    else:
                        r2 = match.group(1)
                        r2 = float(r2)
                        if r2 > minr2:
                            status.append({
                                'target': f,
                                'validator': self.name,
                                'description': self.description,
                                'rules': r,
                                'status': "OK",
                                'message': "Acceptable R2"
                            })
                        else:
                            status.append({
                                'target': f,
                                'validator': self.name,
                                'description': self.description,
                                'rules': r,
                                'status': "ERROR",
                                'message': "R2 is too low"
                            })

        return status

def setup(mgr):

    obj = RegressionQualityValidator()
    mgr.register('validator', obj)


