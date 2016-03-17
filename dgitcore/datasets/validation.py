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
                    'files': [],
                    'rules': []
                }
            }
    else: 
        validators = default_validators 

    #=========================================
    # Insert the file names 
    #=========================================
    if filename is not None: 
        matching_files = repo.find_matching_files([filename])
        if len(matching_files) == 0: 
            print("Filename could not be found", filename) 
            raise Exception("Invalid filename pattern")
        for v in validators: 
            validators[v]['files'] = matching_files
    else: 
        # Instantiate the files from the patterns specified
        for v in validators: 
            if 'files' not in validators[v]: 
                validators[v]['files'] = []
            else: 
                matching_files = repo.find_matching_files(validators[v]['files'])
                validators[v]['files'] = matching_files
    #=========================================
    # Insert the rules files..
    #=========================================
    if rules is not None: 
        # Command lines...
        matching_files = repo.find_matching_files(rules)
        if len(matching_files) == 0: 
            print("Could not find matching rules files ({}) for {}".format(rules,v))
            raise Exception("Invalid rules")
        for v in validators: 
            validators[v]['rules'] = matching_files
    else: 
        # Instantiate the files from the patterns specified
        for v in validators: 
            if 'rules' not in validators[v]: 
                validators[v]['rules'] = []
            else: 
                rules = validators[v]['rules']
                matching_files = repo.find_matching_files(rules)
                if len(matching_files) == 0: 
                    print("Could not find matching rules files ({}) for {}".format(rules,v))
                    raise Exception("Invalid rules")
                validators[v]['rules'] = matching_files        

    return validators

def run_validation(repo, validator_name=None, filename=None, rules=None): 
    """
    Check the integrity of the dataset
    """

    mgr = get_plugin_mgr() 

    # Expand the specification. Now we have full file paths 
    validator_specs = instantiate(repo, validator_name, filename, rules) 
    
    # Run the validators with rules files...
    allresults = []
    for v in validator_specs: 
        
        files = validator_specs[v]['files']
        rules = validator_specs[v]['rules']

        keys = mgr.search(what='validator',name=v)['validator']        
        for k in keys: 
            validator = mgr.get_by_key('validator', k)
            result = validator.evaluate(repo, files, rules) 
            allresults.extend(result)

    return allresults
    
def validate(repo, validator_name=None, filename=None, rules=None): 
            
    results = run_validation(repo, validator_name, filename, rules)
    
    validators = list(set([r['validator'] for r in results]))
    for v in validators: 
        print(v)
        print("==========")
        for r in results: 
            if r['validator'] == v: 
                print("({}) {} : {} {}".format(r['rules'],
                                               r['target'], 
                                               r['status'],
                                               r['message']))
        print("")
