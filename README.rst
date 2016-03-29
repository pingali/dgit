dgit - Lightweight "Git Wrapper for Datasets"
=============================================

*Note: Code is still pre-alpha. It is being cleanedup and stabilized. Not yet ready for daily use.*

dgit is an application on top of git. 

A lot of data-scientists' time goes towards generating, shaping, and
using datasets. dgit enables organizing and using datasets with
minimal effort. 

dgit uses git for version management but structures the repository
content, and interface to suit data management tasks. 

dgit is agnostic to form and content of the datasets and
post-processing scripts. It tries to be sync with `best available
dataset standards <http://dataprotocols.org>`_ (WIP)

Read `documentation <https://dgit.readthedocs.org>`_ 

Slides on a `Scaling Data Science with dgit <http://www.slideshare.net/pingali/r-meetup-talk-scaling-data-science-with-dgit>`_ at R Data Science Meetup, Bangalore

Contents:

* Usage
    1. `Setup`_
    2. `Tutorial`_
    3. `Usage`_
    4. `Available Plugins`_
    5. `Security and Privacy`_
* Background
    1. `Dataset Management Problem`_ 
    2. `Usecase`_


Setup
--------

Note that only Python 3 and ubuntu are supported for now. 
::
   
    # Dependencies (Ubuntu commands for lxml dependency) 
    $ sudo apt-get install libxml2-dev libxslt1-dev python-dev

    # Prepare the environment
    virtualenv -p /usr/bin/python3 env
    . env/bin/activate
        
    # Install dgit 
    $ pip install dgit 
    $ pip install dgit-extensions 

    # Generate overall configuration file 
    $ dgit config init 
    ...

Tutorial
--------

We show how to create a simple dataset that is a git repo with s3 as
the backend. 

dgit has an *auto* mode in which it tries to do as much work as
possible using a combination of configuration and intelligent
defaults. When you run it first time, it asks a few questions that it
uses to generate a configuration file. The latter is editable any
time. When we run dgit auto, it uses the configuration to determine 
what to do. 

::

   # One command to rule them all!    
   $ dgit auto 

dgit scans the working directory for changes and automatically commits
them to the dataset.

1. Clone/create a model directory (may contain scripts and other files)    
::


   $ git clone https://gitlab.com/pingali/simple-regression.git
   $ cd simple-regression

2. Create a dgit configuration file 

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

3. Bootstrap the dataset. It will capture any files that match the
   include pattern

::

   $ dgit auto 
   Repo doesnt exist. Should I create one? [yN]y
   Adding: datapackage.json
   Adding: .gitignore

4. Run the model and update dataset

::

   $ ./model.py 
   $ ls
   dgit.json  model.py  model-results.txt

   $ dgit auto
   Adding: model-results.txt
   Quick summary of changes? One run of the model

5. If a dataset metadata server is enabled, then previous command will
   post to the server. 

::

   ...
   Collecting all the required metadata to post
   Adding preview for  model-results.txt
   Add commit data for model.py
   Added platform information
   Adding validation information
   No dependencies
   Computing diffs
   Posting to http://<server> 
    
5. Explicit push to s3/backend. This can be enabled automatically through dgit.json if needed. 

::

   ...
   remote: upload: hooks/post-update.sample to s3://appsloka/git/pingali/simple-regression.git/hooks/post-update.sample
   remote: upload: refs/heads/master to s3://appsloka/git/pingali/simple-regression.git/refs/heads/master
   remote: upload: ./config to s3://appsloka/git/pingali/simple-regression.git/config
   To /home/pingali/.dgit/git/pingali/simple-regression.git
     * [new branch]      master -> master


Usage
-----

::

    $ dgit 
    Usage: dgit [OPTIONS] COMMAND [ARGS]...
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      add-files  Add files to the repo
      auto       Auto mode of operation
      clone      Clone a git URL
      commit     Commit repo data
      config     Create configuration file (~/.dgit.ini)
      diff       Show the diff between two commits
      drop       Drop dataset
      generate   Materialize queries
      init       Bootstrap a new dataset (a git repo+s3...
      list       List datasets
      log        Gather the log details
      plugins    Plugin management
      post       Post metadata (only) to thirdparty server
      push       Gather the log details
      remote     Manage remote
      rm         Delete files from repo
      sh         Run generic shell commands in repo
      show       Show details of commit
      stash      Trash all the changes in the dataset
      status     Status of the repo
      validate   Validate the content of the repository
    
Available Plugins
-----------------

This is the base set of plugins supported by the default dgit
repo. More extensions are part of `dgit-extensions
<https://github.com/pingali/dgit-extensions>`_.

::

   $ dgit plugins list 
   dgit plugins list
   ========
   backend
   ========
   local (v0) : Local Filesystem Backend
   s3 (v0) : S3 backend
   
   ========
   repomanager
   ========
   git (v0) : Git-based Repository Manager
   
   ========
   metadata
   ========
   basic-metadata (v0) : Basic metadata server
   
   ========
   validator
   ========
   regression-quality-validator (v0) : Check R2 of regression model
   metadata-validator (v0) : Validate integrity of the dataset metadata
   
   ========
   generator
   ========
   mysql-generator (v0) : Materialize queries in dataset
   
   ========
   instrumentation
   ========
   content (v0) : Basic content analysis
   executable (v0) : Executable analysis
   platform (v0) : Execution platform information
   

Security and Privacy
--------------------

Some basic principles adhered to by dgit: 

1. dgit code is opensource to enable auditing if needed. 

2. No data ever leaves organizational premises (or even local machine)
   without explicit actions.

3. When pushing data repo to a backend such as s3, it is done using
   credentials stored on the local machine. Nobody outside the
   organization can access the repo.

4. When metadata is posted to any server to enable search, lineage
   computation etc. the parameters are controlled - what is posted,
   when and where. 

5. When data leaves premises (e.g., dgit post), it is only metadata by
   default (filenames, timestamps etc). There is an ability to add
   previews/schemas etc but that information must be explicitly
   added. All metadata being posted is stored in a standard location
   (datapackage.json) within the data repo. Posting rawdata is not
   supported by design.


Background
==========

Dataset Management Problem
---------------------------

Some persistent problems of datascientists include: 

* Tracking which dataset was used to generate a result? 
* How did we get to the dataset to begin with? 
* Finding analysis that will be impacted by change in version of a dataset? 

Datascience domain needs a tool that is no more complex than git to
manage these problems that:

* Is simple to deploy and use, and does not impose a certain way of doing
  things.
* Does not require coordination with people if there is only one user,
  but does not prevent coordination and collaboration
* Addresses the needs of dataset versioning including metadata content
  and representation and use of third party versioning or storage
  services such as s3 and instabase.


Usecase
-------

* A single code repo may generate many datasets, each of which may have
  one or more files,  during many runs  
* There are usually large number of small files 
* Datasets are used by non-technical teams including business teams 
* Datasets may be generated outside git repos (e.g., acquisition from
  third party, software such as simulators)
* Datasets may be rawdata or data generator scripts 
* Files may be added to datasets over time
* Datasets may not be able to leave premises 
* Data analysis projects tend to have relatively short duration (1 day
  to few months) and executed by relatively isolated teams (one
  individual to a few). 
* Auditability and shareability is required but sharing is not as
  extensive as software development. People tend to work on different
  business problems.

We could force express these into a one or more git repos, run a git
server locally, and/or use github LFS/gitlab annex. We felt that the
usecase is slightly different from software repos


License 
-------

MIT license. 

Copyright (c) 2016, Venkata Pingali
All rights reserved.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Contibutors
-----------

`Venkata Pingali <https://github.com/pingali/>`_ (pingali@gmail.com) 
