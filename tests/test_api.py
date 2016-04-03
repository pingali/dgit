import os, sys, shutil, tempfile, json, stat
from nose import with_setup
from nose.tools import assert_raises
from unittest import TestCase

####################################################
# This file has (an incomplete) list of tests for the API. In
# particular it tests whether repos are being created correctly, and
# when we add files they do show up in all the right places. The list
# is not complete. This needs more work.
####################################################

# setup the test environment and then import dgitcore
thisdir = os.path.dirname(os.path.abspath(__file__))
os.environ['DGIT_INI'] = os.path.join(thisdir,
                                      'assets',
                                      'dgit-api.ini')
from dgitcore.exceptions import *
from dgitcore import api
from dgitcore.helper import cd

###########################################
# Setup and tear down
###########################################

def clean_workspace():
    """
    Clean the working space
    """
    config = api.get_config()
    workspace = config['Local']['workspace']
    default_workspace = os.path.expanduser("~/.dgit")
    if workspace != default_workspace and os.path.exists(workspace):
        print("Removing tree", workspace)
        shutil.rmtree(workspace)

def workspace_setup():
    print("setup")
    api.initialize()
    clean_workspace()

def workspace_teardown():
    print("teardown")
    clean_workspace()

def create_sample_repo_nooptions(username, reponame, setup):
    # Now try with options
    repo = api.init(username,
                    reponame,
                    setup=setup,
                    noinput=True
                )
    return repo

def create_sample_repo(username, reponame, setup):
    # Now try with options
    repo = api.init(username, reponame,
                    setup=setup,
                    options={
                        "title": "Simple",
                        "description": "Simple dataset"
                    },
                    noinput=True
                )
    return repo

def get_remote_path(result):
    # Extract the backend path
    remotes = result['message'].split("\n")
    fetch = [r for r in remotes if "(fetch)" in r][0]
    path = fetch.replace(" (fetch)","")
    backend_repodir = path.replace("origin\t","")
    return backend_repodir

repo_configurations = {
    'simple1': ['test1', 'testrepo1', None],
    'simple2': ['test2', 'testrepo2', None],
    's3': ['test_s3', 'testrepo_s3', 'git+s3']
}

def basic_repo_lookup(name):
    repo = api.lookup(repo_configurations[name][0],
                      repo_configurations[name][1])
    assert repo is not None
    return repo

def basic_result_check(result):
    assert isinstance(result, dict)
    assert result['status'] == 'success'

###########################################
# Group 1
# Simple checks
###########################################
@with_setup(workspace_setup,None)
def test_start_group0():
    """
    [Group0] Begin
    """
    pass

def test_missing_repo():
    """
    Lookup repo
    """
    with assert_raises(UnknownRepository):
        api.lookup(repo_configurations['simple1'][0],
                   repo_configurations['simple1'][1])

@with_setup(workspace_setup,None)
def test_end_group0():
    """
    [Group0] End
    """
    pass

###########################################
# Group 2
# Check creation process. Check the content
###########################################
@with_setup(workspace_setup,None)
def test_start_group1():
    """
    [Group1] Begin
    """
    pass


def test_create_repo():
    """
    Init repo
    """

    for name in repo_configurations:

        #  This should fail
        with assert_raises(IncompleteParameters):
            repo = create_sample_repo_nooptions(*repo_configurations[name])

        #  This should be successful
        repo = create_sample_repo(*repo_configurations[name])
        assert repo is not None

        # Check if all the files have been created
        rootdir = repo.rootdir
        for suffix in ["", '.git', '.gitignore', 'datapackage.json']:
            path = os.path.join(rootdir, suffix)
            assert os.path.exists(path)

    print("Completed create repo")


def test_sh_command():
    """
    Shell cmds
    """

    repo = basic_repo_lookup('simple1')

    output = api.shellcmd(repo, ['ls'])
    assert "datapackage.json" in output


def test_remote():
    """
    S3 hook configuration
    """
    repo = basic_repo_lookup('s3')

    result = api.remote(repo,['-v'])
    basic_result_check(result)
    assert result['message'] is not None

    # Basic check...
    backend_repodir = get_remote_path(result)
    assert os.path.exists(backend_repodir)

    # Is the post-receive hook there?
    path = os.path.join(backend_repodir, 'hooks', 'post-receive')
    assert os.path.exists(path)

    # Make sure that the post-receive hook has execute permissions
    st = os.stat(path)
    assert bool(st.st_mode & stat.S_IXUSR)

def test_check_package():
    """
    Metadata validity
    """
    repo = basic_repo_lookup('simple1')

    rootdir = repo.rootdir
    path = os.path.join(rootdir, 'datapackage.json')

    # Can the metadata be loaded to begin with?
    try:
        package = json.loads(open(path).read())
        valid = True
    except:
        valid = False
    assert valid

def test_repo_drop():
    """
    Drop repo
    """

    repos = api.list_repos()
    print(repos)
    assert len(repos) == 3

    repo = basic_repo_lookup('simple1')
    rootdir = repo.rootdir
    api.drop(repo)

    assert not os.path.exists(rootdir)

    repos = api.list_repos()
    print(repos)
    assert len(repos) == 2


@with_setup(None, workspace_teardown)
def test_end_group1():
    """
    [Group1] End
    """
    pass

###########################################
# Group 2
###########################################
@with_setup(workspace_setup,None)
def test_start_group2():
    """
    [Group2] Begin
    """
    pass


def test_simple_add_files():
    """
    Add simple files
    """

    repo = create_sample_repo(*repo_configurations['simple1'])

    # Create a temp file and add it
    (fd, filename) = tempfile.mkstemp()
    try:
        print("Adding ", filename) 
        api.add(repo, [filename], ".")

        # Check if the file exists in git
        rootdir = repo.rootdir
        basename = os.path.basename(filename)
        path = os.path.join(rootdir, basename)
        assert os.path.exists(path)

        # Check if the file shows up in the datapackage
        package = json.loads(open(os.path.join(rootdir, 'datapackage.json')).read())
        filenames = [r['relativepath'] for r in package['resources']]
        assert basename in filenames

        # TODO
        # Check SHA checksum...

        # Check if it is showing up in the status command.
        result = api.status(repo)
        basic_result_check(result)
        assert "new file" in result['message']

        # Check if it is showing up in the status command.
        result = api.commit(repo, ["-a", "-m", "Test file addition"])
        print("Commit result")
        print(result)
        basic_result_check(result)
        

        result = api.status(repo)
        basic_result_check(result)
        print(result)
        assert "new file" not in result['message']

        # Check whether the commit message shows the commit message
        result = api.log(repo)
        basic_result_check(result)
        assert "Test file addition" in result['message']

    except Exception as e:
        # Cleanup and throw the exception again
        os.unlink(filename)
        raise e

    # Cleanup
    os.unlink(filename)


@with_setup(None, workspace_teardown)
def test_end_group2():
    """
    [Group2] End
    """
    pass
