#!/usr/bin/env python 

import os, sys, requests, json 
from dgitcore.plugins.metadata import MetadataBase
from dgitcore.config import get_config, ChoiceValidator, URLValidator, NonEmptyValidator

class BasicMetadata(MetadataBase):     
    """
    Metadata backend for the datasets.

    Parameters
    ----------
    Configuration (token) 
    """
    def __init__(self): 
        self.enable = False 
        self.token = None 
        self.url = None 
        super(BasicMetadata, self).__init__('basic-metadata', 
                                              'v0', 
                                              "Basic metadata server")

    def config(self, what='get', params=None): 
        
        if what == 'get': 
            return {
                'name': 'basic-metadata', 
                'nature': 'metadata',
                'variables': ['enable', 'token', 'url'], 
                'defaults': { 
                    'enable': {
                        'value': "y",
                        "description": "Enable generic Metadata server?",
                        'validator': ChoiceValidator(['y','n'])
                    },
                    'token': {
                        'value': '',
                        'description': 'Provide API token to be used for posting',
                        'validator': NonEmptyValidator(),
                    },
                    'url': {
                        'value': '',
                        'description': 'URL to which metadata should be posted',
                        'validator': URLValidator()
                    },
                }
            }
        else:
            try: 
                self.enable = params['basic-metadata']['enable']
            except:
                self.enable = 'n'
                return 
                
            metadata = params['basic-metadata']
            self.enable     = metadata['enable']
            self.token      = metadata.get('token', None)
            self.url        = metadata.get('url', None) 
            if self.enable == 'y': 
                if self.token is None:
                    print("If metadata is enabled, Token should be provided")
                    raise Exception("Invalid configuration")
                if self.url is None:
                    print("If metadata is enabled, Token should be provided")
                    raise Exception("Invalid configuration")


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

        try: 
            r = requests.post(url, 
                              data = json.dumps(datapackage),
                              headers=headers) 

            return r 
        except: 
            print("Could not post to server") 
        return ""
    
def setup(mgr): 
    
    obj = BasicMetadata() 
    mgr.register('metadata', obj)


