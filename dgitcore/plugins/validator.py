#!/usr/bin/env python

import os, sys
import json
from collections import namedtuple
import requests

Key = namedtuple("Key", ["name","version"])

class ValidatorBase(object):
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

    def autooptions(self):
        """
        Get default options
        """
        return None

    def evaluate(self, repo, files, rules):
        """
        Evaluate the repo

        returns: A list of dictionaries with:
           target: relative path of the file
           rules: rules file used
           validator: name of the validator
           status: OK/Success/Error
           Message: Any additional information
        """
        return []
