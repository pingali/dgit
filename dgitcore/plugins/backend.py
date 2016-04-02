#!/usr/bin/env python

import os, sys
import json
from collections import namedtuple

Key = namedtuple("Key", ["name","version"])

class BackendBase(object):
    """
    Backend object implements
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
        self.enable = 'y'
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

    def clone_repo(self, url, gitdir):
        """
        Clone a repo at specified URL
        """
        return

    def supported(self, url):
        """
        Check if a URL is supported by repo
        """
        return False

    def url_is_valid(self, url):
        """
        Check if a URL exists
        """
        return

    def push(self, state, name):
        """
        Push a data version to the server

        Parameters
        ----------

        state: Overall state object that has dataset details
        name: name of the dataset
        """
        return

    def config(self, what='get', params=None):
        return
