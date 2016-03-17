#!/usr/bin/env python 

import os, sys, json
from ..plugins.common import get_plugin_mgr 

#####################################################
# Validate content
#####################################################
    
def instantiate(repo, validator_name=None, filename=None, rules=None): 
    """
    Instantiate the validation specification
    """

    default_validators = repo.options.get('validate', {})

    validators = {} 
    if validator_name is not None:
        # Handle the case validator is specified..
        if validator_name in default_validators: 
            validators = { 
                validator_name : default_validators[validator_name]
            }
        else: 
            validators = { 
                validator_name : {
                    'files': []
                }
            }
    else: 
        validators = default_validators 
        
    # Insert the file names 
    if filename is not None: 
        matching_files = repo.find_matching_files(filename)
        if len(matching_files): 
            print("Filename could not be found", filename) 
            raise Exception("Invalid filename pattern")
        for v in validators: 
            validators[v]['files'] = matching_files
    else: 
        # Instantiate the files from the patterns specified
        for v in validators: 
            matching_files = repo.find_matching_files(validators[v]['files'])
            validators[v]['files'] = matching_files

    # Insert the file names 
    if rules is not None: 
        matching_files = repo.find_matching_files(rules)
        if len(matching_files): 
            print("Rules file could not be found", rules) 
            return 
        for v in validators: 
            validators[v]['rules'] = matching_files
    else: 
        # Instantiate the files from the patterns specified
        for v in validators: 
            if 'rules' not in validators[v]: 
                continue 
            rules = validators[v]['rules']
            if len(rules) == 0 or rules is None: 
                continue 
            matching_files = repo.find_matching_files(rules)
            if len(matching_files) == 0: 
                print("Could not find matching rules files ({}) for {}".format(rules,v))
                return 
            validators[v]['rules'] = matching_files        

    return validators

def validate(repo, validator_name=None, filename=None, rules=None): 
    """
    Check the integrity of the dataset
    """

    mgr = get_plugin_mgr() 

    # Expand the specification. Now we have full file paths 
    validator_specs = instantiate(repo, validator_name, filename, rules) 
    
    # Run the validators with rules files...
    for v in validator_specs: 
        
        files = validator_specs[v]['files']
        rules = validator_specs[v]['rules']

        keys = mgr.search(what='validator',name=v)['validator']        
        for k in keys: 
            validator = mgr.get_by_key('validator', k)
            validator.evaluate(repo, files, rules) 
