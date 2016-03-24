#!/usr/bin/env python 

import os, sys, json
from ..plugins.common import plugins_get_mgr 

#####################################################    
# Exports 
#####################################################    

__all__ = ['generate']
#####################################################
# Validate content
#####################################################
    
def instantiate(repo, generator_name=None, filename=None): 
    """
    Instantiate the generator and filename specification
    """

    default_generators = repo.options.get('generate', {})

    generators = {} 
    if generator_name is not None:
        # Handle the case generator is specified..
        if generator_name in default_generators: 
            generators = { 
                generator_name : default_generators[generator_name]
            }
        else: 
            generators = { 
                generator_name : {
                    'files': [],
                }
            }
    else: 
        generators = default_generators 

    #=========================================
    # Insert the file names 
    #=========================================
    if filename is not None: 
        matching_files = repo.find_matching_files([filename])
        print("Matching 1 ", matching_files)
        if len(matching_files) == 0: 
            print("Filename could not be found", filename) 
            raise Exception("Invalid filename pattern")
        for v in generators: 
            generators[v]['files'] = matching_files
    else: 
        # Instantiate the files from the patterns specified
        for g in generators: 
            if (('files' not in generators[g]) or 
                (generators[g]['files'] is None)):
                generators[g]['files'] = []
            elif len(generators[g]['files']) > 0:
                matching_files = repo.find_matching_files(generators[g]['files'])
                generators[g]['files'] = matching_files

    return generators

def run_generate(repo, generator_name=None, filename=None, force=False):
    """
    Materialize
    """

    mgr = plugins_get_mgr() 

    # Expand the specification. Now we have full file paths 
    generator_specs = instantiate(repo, generator_name, filename) 
    
    # Run the validators with rules files...
    allresults = []
    for v in generator_specs: 
        
        files = generator_specs[v]['files']
        keys = mgr.search(what='generator',name=v)['generator'] 
        for k in keys: 
            generator = mgr.get_by_key('generator', k)
            result = generator.evaluate(repo, files, force) 
            allresults.extend(result)

    return allresults
    
def generate(repo, 
             generator_name=None, 
             filename=None, 
             force=False,
             show=True): 
    """
    Materialize queries/other content within the repo. 
    
    Parameters
    ----------
    
    repo: Repository object 
    generator_name: Name of generator, if any. If none, then all generators specified in dgit.json will be included. 
    filename: Pattern that specifies files that must be processed by the generators selected. If none, then the default specification in dgit.json is used. 

    """            
    results = run_generate(repo, generator_name, filename, force)

    if not show: 
        return results

    if len(results) == 0: 
        print("No output") 
    else: 
        generators = list(set([r['generator'] for r in results]))
        for g in generators: 
            print(g)
            print("==========")
            for r in results: 
                if r['generator'] == g: 
                    print("{} : {} {}".format(r['target'], 
                                              r['status'],
                                              r['message']))
            print("")

    return results 
