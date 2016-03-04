#!/usr/bin/env python 
"""
Configuration parser 
"""
import os, sys, json
import shelve 
import configparser 
from .plugins import get_plugin_mgr 
config = None 

def getprofileini():
    homedir = os.path.abspath(os.environ['HOME'])
    profileini = os.path.join(homedir,'.dgit.ini') 
    return profileini

def init(globalvars=None, show=False):
    """
    Load profile INI 
    """
    global config
    
    profileini = getprofileini()    
    if os.path.exists(profileini):
        config = configparser.ConfigParser()    
        config.read(profileini)
        mgr = get_plugin_mgr() 
        mgr.update_configs(config)
        if show: 
            for source in config: 
                print("[%s] :" %(source))
                for k in config[source]: 
                    print("   %s : %s" % (k, config[source][k]))
            
    else:
        print("Profile does not exist")
        if not show:
            update(globalvars)
    
def input_with_default(message, default):
    res = input("%s [%s]: " %(message, default))
    return res or default

def update(globalvars):
    """
    Update the profile
    """
    global config 

    profileini = getprofileini()
    config = configparser.ConfigParser()    
    config.read(profileini)
    defaults = {}


    if globalvars is not None: 
        defaults = {a[0]: a[1] for a in globalvars }

    # Generic variables to be captured...
    generic_configs = [{
        'name': 'User',
        'nature': 'generic',
        'variables': ['user.name', 'user.email', 'user.fullname'],
        'defaults': {
            'user.email': { 
                'value': defaults.get('user.email',''),
                'description': "Email address" 
            },
            'user.fullname': {
                'value': defaults.get('user.fullname',''),
                'description': "User"
            },
            'user.name': {
                'value': defaults.get('user.name',''),
                'description': "User"
            }
        }
    }]
    
    mgr = get_plugin_mgr() 
    extra_configs = mgr.gather_configs()

    allconfigs = generic_configs + extra_configs 
    for c in allconfigs: 
        name = c['name']
        for v in c['variables']: 
            print("Looking at ", name, v)
            try: 
                c['defaults'][v]['value'] = config[name][v] 
            except:
                continue

    print(json.dumps(allconfigs, indent=4))

    for c in allconfigs: 
        name = c['name']
        config[name] = {} 
        config[name]['nature'] = c['nature']
        for v in c['variables']: 
            
            # defaults 
            value = ''
            description = v + " " 
            helptext = ""

            # Expand..
            if v in c['defaults']: 
                value = c['defaults'][v].get('value','')            
            if v in c['defaults']: 
                helptext = c['defaults'][v].get("description","") 
            if helptext != "": 
                description += "(" + helptext + ")"         

            # Get user input..
            choice = input_with_default(description, value)
            choice = choice.lower() 
            config[name][v] = choice
            if v == 'enable' and choice in ['n', 'no']: 
                # Dont bother to get the rest...
                break 

    with open(profileini, 'w') as fd:
        config.write(fd)

    print("Updated profile file:", config)

def get_config():
    if config is None: 
        init() 
    return config 

def set_default_dataset(dataset): 

    workspace = config['Local']['workspace'] 
    statefile = os.path.join(workspace, '.default')
    with open(statefile, 'w') as fd: 
        fd.write(dataset)

def clear_default_dataset(): 

    workspace = config['Local']['workspace'] 
    statefile = os.path.join(workspace, '.default')
    if os.path.exists(statefile): 
        os.remove(statefile) 

def get_default_dataset(): 

    workspace = config['Local']['workspace'] 
    statefile = os.path.join(workspace, '.default')    

    dataset = None 
    if os.path.exists(statefile): 
        dataset = open(statefile).read()         
        if dataset == "":
            dataset = None 

    return dataset 

        
    
def get_state():
    
    config = get_config()
    workspace = config['Local']['workspace']         
    
    if not os.path.exists(workspace): 
        os.makedirs(workspace)

    statefile = os.path.join(workspace, "datasets.state.shelve")
    state = shelve.open(statefile, writeback=True)
    state['config'] = config # may have changed...
    state.sync() 

    return state 
    
