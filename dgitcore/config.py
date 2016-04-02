#!/usr/bin/env python
"""
dgit default configuration manager

[User] section:

* user.name: Name of the user
* user.email: Email address (to be used when needed)
* user.fullname: Full name of the user


"""
import os, sys, json, re, traceback, getpass

try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse

import configparser
from .plugins.common import plugins_get_mgr
config = None

###################################
# Input validators
###################################
class ChoiceValidator(object):
    def __init__(self, choices):
        self.choices = choices        
        message = "Supported options include: {}"
        self.message = message.format(",".join(self.choices))

    def is_valid(self, value):
        if value in self.choices:
            return True
        return False

class NonEmptyValidator(object):
    def __init__(self):
        self.message = "Value cannot be an empty string"

    def is_valid(self, value):
        if value is None or len(value) == 0:
            return False
        return True

class EmailValidator(object):
    def __init__(self):
        self.message = "Value has to be an email address"
        self.pattern = r"[^@]+@[^@]+\.[^@]+"

    def is_valid(self, value):
        if not re.match(self.pattern, value):
            return False
        return True

class URLValidator(object):
    def __init__(self):
        self.message = "Value should be a valid URL"

    def is_valid(self, value):
        o = urlparse(value)
        return o.scheme in ['http', 'https']


###################################
# Main helper functions...
###################################
def getprofileini():

    if 'DGIT_INI' in os.environ:
        profileini = os.environ['DGIT_INI']
    else:
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
        mgr = plugins_get_mgr()
        mgr.update_configs(config)

        if show:
            for source in config:
                print("[%s] :" %(source))
                for k in config[source]:
                    print("   %s : %s" % (k, config[source][k]))

    else:
        print("Profile does not exist. So creating one")
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
        'description': "General information",
        'variables': ['user.email', 'user.name',
                      'user.fullname'],
        'defaults': {
            'user.email': {
                'value': defaults.get('user.email',''),
                'description': "Email address",
                'validator': EmailValidator()
            },
            'user.fullname': {
                'value': defaults.get('user.fullname',''),
                'description': "Short Name",
                'validator': NonEmptyValidator()
            },
            'user.name': {
                'value': defaults.get('user.name', getpass.getuser()),
                'description': "Full Name",
                'validator': NonEmptyValidator()
            },
        }
    }]

    # Gather configuration requirements from all plugins
    mgr = plugins_get_mgr()
    extra_configs = mgr.gather_configs()
    allconfigs = generic_configs + extra_configs

    # Read the existing config and update the defaults
    for c in allconfigs:
        name = c['name']
        for v in c['variables']:
            try:
                c['defaults'][v]['value'] = config[name][v]
            except:
                continue

    for c in allconfigs:

        print("")
        print(c['description'])
        print("==================")
        if len(c['variables']) == 0:
            print("Nothing to do. Enabled by default")
            continue

        name = c['name']
        config[name] = {}
        config[name]['nature'] = c['nature']
        for v in c['variables']:

            # defaults
            value = ''
            description = v + " "
            helptext = ""
            validator = None

            # Look up pre-set values
            if v in c['defaults']:
                value = c['defaults'][v].get('value','')
                helptext = c['defaults'][v].get("description","")
                validator = c['defaults'][v].get('validator',None)
            if helptext != "":
                description += "(" + helptext + ")"

            # Get user input..
            while True:
                choice = input_with_default(description, value)
                if validator is not None:
                    if validator.is_valid(choice):
                        break
                    else:
                        print("Invalid input. Expected input is {}".format(validator.message))
                else:
                    break

            config[name][v] = choice


    with open(profileini, 'w') as fd:
        config.write(fd)

    print("Updated profile file:", config)

def get_config():
    if config is None:
        init()
    return config

