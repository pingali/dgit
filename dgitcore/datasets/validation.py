#!/usr/bin/env python 

from ..plugins.common import get_plugin_mgr 

#####################################################
# Validate content
#####################################################
def validate(repo):
    """
    Check the integrity of the dataset
    """

    mgr = get_plugin_mgr() 
        
    # keys =  {'validator': [Key(name='basic-validator', version='v0')]}
    validators = mgr.search(what='validator') 
    validators = validators['validator']
    print("validator keys = ", validators) 

    for v in validators: 
        v = mgr.get_by_key('validator', v)
        v.evaluate(repomanager, key)

