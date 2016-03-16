#!/usr/bin/env python 

import os, sys
import json
from collections import namedtuple 
import requests 

Key = namedtuple("Key", ["name","version"])

class MetadataContext: 
    """A helper object passed to Metadata computation functions 
    """
    pass 

class MetadataBase(object):
    """
    This is the base class for all backends including 
    """
    def __init__(self, name, version, description, supported=[]):
        """        
        Parameters: 
        -----------
        name: Name of the backend service e.g., s3 
        version: Version of this implementation 
        description: Text description of this service 
        supported: supported services with including name 
        
        For example, there may be multiple s3 implementations that
        support different kinds of services.  

        """
        self.name = name
        self.version = version        
        self.description = description  
        self.support = supported + [name]
        self.initialize() 

    def initialize(self): 
        """
        Called to initialize sessions, internal objects etc. 
        """
        return 

    def post(self, repo): 
        """
        Post to the metadata server 
        
        Parameters
        ----------

        repo 
        """
        
        datapackage = repo.package 

        url = self.url 
        token = self.token 
        headers = {
            'Authorization': 'Token {}'.format(token),
            'Content-Type': 'application/json'
        }
        r = requests.post(url, 
                          data = json.dumps(datapackage),
                          headers=headers) 

        print(r.request.headers)
        print(r) 
        print(r.content)
        return 
