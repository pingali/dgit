#!/usr/bin/env python

import os, sys, json
from ..plugins.common import plugins_get_mgr
from dgitcore import exceptions

#####################################################
# Exports
#####################################################

__all__ = ['transform']
#####################################################
# Validate content
#####################################################

def instantiate(repo, name=None, filename=None):
    """
    Instantiate the generator and filename specification
    """

    default_transformers = repo.options.get('transformer', {})

    # If a name is specified, then lookup the options from dgit.json
    # if specfied. Otherwise it is initialized to an empty list of
    # files.
    transformers = {}
    if name is not None:
        # Handle the case generator is specified..
        if name in default_transformers:
            transformers = {
                name : default_transformers[name]
            }
        else:
            transformers = {
                name : {
                    'files': [],
                }
            }
    else:
        transformers = default_transformers

    #=========================================
    # Map the filename patterns to list of files
    #=========================================
    # Instantiate the files from the patterns specified
    input_matching_files = None
    if filename is not None:
        input_matching_files = repo.find_matching_files([filename])

    for t in transformers:
        for k in transformers[t]:
            if "files" not in k:
                continue
            if k == "files" and input_matching_files is not None:
                # Use the files specified on the command line..
                transformers[t][k] = input_matching_files
            else:
                # Try to match the specification
                if transformers[t][k] is None or len(transformers[t][k]) == 0:
                    transformers[t][k] = []
                else:
                    matching_files = repo.find_matching_files(transformers[t][k])
                    transformers[t][k] = matching_files

    return transformers

def transform(repo,
              name=None,
              filename=None,
              force=False,
              args=[]):
    """
    Materialize queries/other content within the repo.

    Parameters
    ----------

    repo: Repository object
    name: Name of transformer, if any. If none, then all transformers specified in dgit.json will be included.
    filename: Pattern that specifies files that must be processed by the generators selected. If none, then the default specification in dgit.json is used.

    """
    mgr = plugins_get_mgr()

    # Expand the specification. Now we have full file paths
    specs = instantiate(repo, name, filename)

    # Run the validators with rules files...
    allresults = []
    for s in specs:
        keys = mgr.search(what='transformer',name=s)['transformer']
        for k in keys:
            t = mgr.get_by_key('transformer', k)
            result = t.evaluate(repo,
                                specs[s],
                                force,
                                args)
            allresults.extend(result)

    return allresults
