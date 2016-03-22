Configuration
=============

There are two configuration files 

* ~/.dgit.ini : INI file that specifies generic parameters such as
  client authentication and working space driectories etc.

* dgit.json : Repository-specific configuration file that specifies
  user preferences for a given repository such as validation rules
  that must be executed.

Both can be setup easily and updated at any time. This document gives
you a detailed list of options for completeness. 


Generic Configuration (~/.dgit.ini)
-----------------------------------

Summary
~~~~~~~

dgit is composed to multiple modules, each of which requires
configuration if enabled. This file lists the parameters for each of
the modules. 

1) Basic configuration

.. automodule:: dgitcore.config

2) Repository Manager (Git)

.. automodule:: plugins.repomanagers.gitmanager

3) Backend Manager (S3) 

.. automodule:: plugins.backends.s3

4) Backend Manager (Local) 

.. automodule:: plugins.backends.local

5) Metadata Server (Local) 

.. automodule:: plugins.metadata.default

Execution
~~~~~~~~~

::

   # .dgit.ini in ~ 
   $ dgit config init 
   General information
   ==================
   user.email (Email address) [pingali@gmail.com]: 
   user.name (Full Name) [pingali]: 
   user.fullname (Short Name) [Venkata Pingali]: 
   
   Local Filesystem Backend
   ==================
   workspace (Local directory to store datasets) [/home/pingali/.dgit]: 
   
   S3 backend
   ==================
   enable (Enable S3 backend?) [y]: 
   client (Command line tool to use for repo backup (aws|s3cmd)) [aws]: 
   s3cfg (s3cfg configuration file if s3cmd is chosen. Otherwise ignore) [/home/pingali/.s3cfg]: 
   bucket (Bucket into which the datasets are stored) [appsloka]: 
   prefix (Prefix within bucket to backup the repos) [git]: 
   
   Git-based Repository Manager
   ==================
   Nothing to do. Enabled by default
   
   Basic metadata server
   ==================
   enable (Enable generic Metadata server?) [y]: 
   token (Provide API token to be used for posting) [02ea2997272026303]: 
   url (URL to which metadata should be posted) [http://<server>/api/metdata/]: 
   
   Validate integrity of the dataset metadata
   ==================
   enable (Enable repository metadata integrity check) [y]: 
   
   Check R2 of regression model
   ==================
   enable (Enable repository regression-quality checker) [y]: 
   



Dataset-specific Configuration File (dgit.json)
----------------------------------------------

Summary
~~~~~~~

A dgit configuration file is automatically generated in the local
directory to reduce the need for the user to specify preferences each
time, and work as much as possible in the auto mode.

- username : Name of the user (string)
- reponame : Name of the dataset (unique for a given user) 
- title : One line summary 
- description : Detailed description of the repository 
- remoteurl : Path to the archive of the repo
    - git@github.com:pingali/dgit.git 
    - https://github.com:pingali/dgit.git 
    - s3://mybucket/git/pingali/dgit.git 
- dependencies: List of other repositories that this dataset depends on 
- working-directory : Directory that must be searched for updated 
- tracking : Dictionary specifying files to include and exclude 

    - includes : list of patterns that should be used to include files
    - excludes : list of patterns that should be used to exclude files 

        - Example: .git 

- import : Transformations that must be performed while importing
  files from the local directory into the dataset. 
    - directory-mapping: dictionary with local: repo directory mapping


Execution
~~~~~~~~~

::

   $ dgit auto 
   Let us know a few details about your data repository
   Please specify username [pingali]
   Please specify repo name [simple-regression]
   Please specify remote URL [s3://mybucket/git/pingali/simple-regression.git]
   One line summary of your repo: Simple regression model
   Add any more details:
   
   Updated dataset specific config file: dgit.json
   Please edit it and rerun dgit auto.
   Tip: Consider committing dgit.json to the code repository.

   $ cat dgit.json 
   
   {
       "username": "pingali",
       "reponame": "simple-regression",
       "remoteurl": "s3://appsloka/git/pingali/simple-regression.git",
       "title": " Simple regression model demo",
       "description": " Simple regression model demo",
       "working-directory": ".",
       "track": {
           "includes": [
               "*.csv",
               "*.tsv",
               "*.txt",
               "*.json",
               "*.xlsx"
           ],
           "excludes": [
               ".git",
               ".svn",
               "dgit.json"
           ]
       },
       "import": {
           "directory-mapping": {
               ".": ""
           }
       },
       "validate": {
           "metadata-validator": {},
           "regression-quality-validator": { 
              "files": ["*.txt"],
              "rules": ["*.json"]
            }
       },
       "dependencies": [ "pingali/simple-regression-rawdata" ],
       "metadata-management": {
           "servers": [
               "localhost:8000"
           ],
           "include-code-history": [
               "regression.py",
               "regression2.py"
           ],
           "include-preview": {
               "length": 512,
               "files": [
                   "*.txt",
                   "*.csv",
                   "*.tsv"
               ]
           },
           "include-data-history": true,
           "include-validation": true,
           "include-dependencies": true,
           "include-schema": [
               "*.csv",
               "*.tsv"
           ],
           "include-tab-diffs": [
               "*.csv",
               "*.tsv"
           ],
           "include-platform": true
       }
   }
   
