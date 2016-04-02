import os, sys, shutil, tempfile, json, stat
from nose import with_setup
from nose.tools import assert_raises
from unittest import TestCase
from click.testing import CliRunner
import imp

runner = CliRunner()

####################################################
# This file has (an incomplete) list of tests for the command line. In
# particular it tests whether repos are being created correctly, and
# when we add files they do show up in all the right places. The list
# is not complete. This needs more work.
#####################################################

##########################################################
# Load the command line and set the config file..
##########################################################
thisdir = os.path.abspath(os.path.dirname(__file__))
os.environ['DGIT_INI'] = os.path.join(thisdir,
                                      'assets',
                                      'dgit-cli.ini')

# Load the dgit command file...
dgitfile = os.path.join(thisdir, "..", "bin", "dgit")
dgitmod = imp.load_source('dgit', dgitfile)

##########################################################
# Setup and clean workspace
##########################################################
def clean_workspace():
    """
    Clean the working space
    """

    # Run the dgit config show to the workspace directory
    result = runner.invoke(dgitmod.profile, ['show'])
    output = result.output
    output = output.split("\n")
    workspaces = [o.strip() for o in output if "workspace :" in o]
    if len(workspaces) > 0:
        workspace = workspaces[0]
        workspace = workspace.replace("workspace : ","")
    else:
        workspace = os.path.join(os.getcwd(), 'workspace')

    default_workspace = os.path.expanduser("~/.dgit")
    if ((workspace != default_workspace) and
        os.path.exists(workspace)):
        print("Removing tree", workspace)
        shutil.rmtree(workspace)

def workspace_setup():
    print("Setup")
    dgitmod.setup()
    clean_workspace()

def workspace_teardown():
    print("teardown")
    clean_workspace()
    dgitmod.teardown()

repo_configurations = {
    'simple1': ['test1', 'testrepo1', None],
    'simple2': ['test2', 'testrepo2', None],
    's3': ['test_s3', 'testrepo_s3', 'git+s3']
}

@with_setup(workspace_setup, workspace_teardown)
def test_list():
    """
    List repos
    """
    result = runner.invoke(dgitmod.list_repos)
    assert "Found 0 repos" in result.output


@with_setup(workspace_setup, workspace_teardown)
def test_init():
    """
    Init repo
    """
    result = runner.invoke(dgitmod.init,
                           [ "{}/{}".format(repo_configurations['simple1'][0],
                                            repo_configurations['simple1'][1]),
                             '--setup', 'git',
                         ],
                           input="Hello\ntest")

    result = runner.invoke(dgitmod.list_repos)
    assert "Found 1 repos" in result.output
