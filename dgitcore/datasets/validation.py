#!/usr/bin/env python

import os, sys, json
from ..plugins.common import plugins_get_mgr

#####################################################
# Exports
#####################################################

__all__ = ['validate']

#####################################################
# Validate content
#####################################################

def instantiate(repo, validator_name=None, filename=None, rulesfiles=None):
    """
    Instantiate the validation specification
    """

    default_validators = repo.options.get('validator', {})

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
                    'rules': {},
                    'rules-files': []
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
            elif len(validators[v]['files']) > 0:
                matching_files = repo.find_matching_files(validators[v]['files'])
                validators[v]['files'] = matching_files

    #=========================================
    # Insert the rules files..
    #=========================================
    if rulesfiles is not None:
        # Command lines...
        matching_files = repo.find_matching_files([rulesfiles])
        if len(matching_files) == 0:
            print("Could not find matching rules files ({}) for {}".format(rulesfiles,v))
            raise Exception("Invalid rules")
        for v in validators:
            validators[v]['rules-files'] = matching_files
    else:
        # Instantiate the files from the patterns specified
        for v in validators:
            if 'rules-files' not in validators[v]:
                validators[v]['rules-files'] = []
            else:
                rulesfiles = validators[v]['rules-files']
                matching_files = repo.find_matching_files(rulesfiles)
                if len(matching_files) == 0:
                    print("Could not find matching rules files ({}) for {}".format(rules,v))
                    raise Exception("Invalid rules")
                validators[v]['rules-files'] = matching_files

    return validators

def validate(repo, validator_name=None, 
             filename=None, 
             rulesfiles=None,
             args=[]):
    """
    Validate the content of the files for consistency. Validators can
    look as deeply as needed into the files. dgit treats them all as
    black boxes.

    Parameters
    ----------

    repo: Repository object
    validator_name: Name of validator, if any. If none, then all validators specified in dgit.json will be included.
    filename: Pattern that specifies files that must be processed by the validators selected. If none, then the default specification in dgit.json is used.
    rules: Pattern specifying the files that have rules that validators will use
    show: Print the validation results on the terminal

    Returns
    -------

    status: A list of dictionaries, each with target file processed, rules file applied, status of the validation and any error  message.
    """

    mgr = plugins_get_mgr()

    # Expand the specification. Now we have full file paths
    validator_specs = instantiate(repo, validator_name, filename, rulesfiles)

    # Run the validators with rules files...
    allresults = []
    for v in validator_specs:

        keys = mgr.search(what='validator',name=v)['validator']
        for k in keys:
            validator = mgr.get_by_key('validator', k)
            result = validator.evaluate(repo, 
                                        validator_specs[v],
                                        args)
            allresults.extend(result)

    return allresults

