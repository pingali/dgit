#!/usr/bin/env python
"""Implements the s3-based storage service for the repositories. Uses a
command line tool such as aws cli and s3cmd instead of boto3 library
for simplicity.

[S3] section:

* enable: Enable this storage service
* client: s3cmd or aws cli
* s3cfg: Optional configuration file to be specified is s3cmd is the client
* bucket: s3 bucket to store the repositories
* prefix: Prefix within the bucket

"""
import os, sys, stat, subprocess
import boto3
import getpass
from dgitcore.plugins.backend import BackendBase
from dgitcore.config import get_config, ChoiceValidator, NonEmptyValidator
from dgitcore.helper import cd

postreceive_template="""#!/bin/bash
CMD="%(client)s"

repo=$(basename "$PWD")
username=$(basename $(dirname "$PWD"))

if [ "$CMD" == "aws" ]; then
    aws s3 sync --delete ./ s3://%(bucket)s/%(prefix)s/$username/$repo/
elif [ "$CMD" == "aws" ]; then
    s3cmd -c /home/pingali/.s3cfg sync --delete ./ s3://%(bucket)s/%(prefix)s/$username/$repo/
fi"""


class S3Backend(BackendBase):
    """
    S3 backend for the datasets.

    Parameters
    ----------
    Configuration (s3 enable,access, secret, bucket, prefix)
    """
    def __init__(self):
        self.enable = False
        self.client = None
        self.s3cfg  = None
        self.bucket = None
        self.prefix = None
        super(S3Backend,self).__init__('s3', 'v0', "S3 backend")


    def url(self, username, reponame):
        return "s3://%(bucket)s/%(prefix)s/%(username)s/%(reponame)s.git" % {
            'bucket': self.bucket,
            'prefix': self.prefix,
            'username': username,
            'reponame': reponame
            }

    def run(self, cmd):
        cmd = " ".join(cmd)
        output = subprocess.check_output(cmd,
                                         stderr=subprocess.STDOUT,
                                         shell=True)
        output = output.decode('utf-8')
        return output

    def config(self, what='get', params=None):

        if what == 'get':
            return {
                'name': 'S3',
                'nature': 'backend',
                'variables': ['enable',
                              'client', 's3cfg',
                              'bucket', 'prefix'],
                'defaults': {
                    'enable': {
                        'value': "y",
                        "description": "Enable S3 backend?",
                        'validator': ChoiceValidator(['y', 'n'])
                    },
                    'client': {
                        'value': 'aws',
                        'description': 'Command line tool to use for repo backup (aws|s3cmd)',
                        'validator': NonEmptyValidator()
                    },
                    "s3cfg": {
                        'value': os.path.join(os.environ.get('HOME',"."), '.s3cfg'),
                        'description': 's3cfg configuration file if s3cmd is chosen. Otherwise ignore',
                        'validator': NonEmptyValidator()
                    },
                    'bucket': {
                        'value': "",
                        'description': "Bucket into which the datasets are stored",
                        'validator': NonEmptyValidator()
                    },
                    'prefix': {
                        "value": "git",
                        "description": "Prefix within bucket to backup the repos",
                        'validator': NonEmptyValidator()
                    },
                }
            }
        elif what == 'validate':
            valid = True
            s3 = params['S3']
            if params['s3']['enable'] == 'y':
                if params['s3']['bucket'] in ['', None]:
                    print("Bucket cannot be empty")
                    valid = False
                if params['s3']['prefix'] in ['', None]:
                    print("Prefix within bucket cannot be empty")
                    valid = False
            return valid
        else:
            s3 = params['S3']
            self.enable     = s3['enable']
            self.client     = s3.get('client', 'aws')
            self.s3cfg      = s3.get('s3cfg',
                                     os.path.join(os.environ.get('HOME',"."), '.s3cfg'))
            self.bucket     = s3.get('bucket', None)
            self.prefix     = s3.get('prefix', None)

        return True

    def make_hook_executable(self, filename):

        # Set the execute permissions
        st = os.stat(filename)
        os.chmod(filename, st.st_mode | stat.S_IEXEC)

    def init_repo(self, gitdir):
        """
        Insert hook into the repo
        """

        hooksdir = os.path.join(gitdir, 'hooks')
        content = postreceive_template % {
            'client': self.client,
            'bucket': self.bucket,
            's3cfg': self.s3cfg,
            'prefix': self.prefix
            }

        postrecv_filename =os.path.join(hooksdir, 'post-receive')
        with open(postrecv_filename,'w') as fd:
            fd.write(content)

        self.make_hook_executable(postrecv_filename)
        print("Wrote to", postrecv_filename)


    def url_is_valid(self, url):

        if self.client == 'aws':
            cmd = ["aws", "s3", "ls", url ]
        else:
            cmd = ["s3cmd", "-c", self.s3cfg, "ls", url]

        output = self.run(cmd)
        if len(output) == 0:
            return False

        return True

    def clone_repo(self, url, gitdir):

        if not self.url_is_valid(url):
            raise Exception("Invalid URL")

        try:
            os.makedirs(gitdir)
        except:
            pass


        print("Syncing into local directory", gitdir)
        with cd(gitdir):
            if self.client == 'aws':
                cmd = ["aws", "s3", "sync", '--delete', url + "/", "."]
            else:
                cmd = ["s3cmd", "-c", self.s3cfg, "sync", url + "/", "."]
            # print("CMD", cmd)
            output = self.run(cmd)
            #print(output)
            print("Sync'd dataset with s3")


        # Make sure that hook is has correct permissions
        hooksdir = os.path.join(gitdir, 'hooks')
        postrecv_filename =os.path.join(hooksdir, 'post-receive')
        if os.path.exists(postrecv_filename):
            self.make_hook_executable(postrecv_filename)
        else:
            self.init_repo(gitdir)


def setup(mgr):

    obj = S3Backend()
    mgr.register('backend', obj)

