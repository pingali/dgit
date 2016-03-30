import os, sys, shutil, tempfile, json 
from nose import with_setup
from nose.tools import assert_raises
from unittest import TestCase

# setup the test environment and then import dgitcore 
thisdir = os.path.dirname(os.path.abspath(__file__))
os.environ['DGIT_INI'] = os.path.join(thisdir, 
                                      'assets', 
                                      'dgit-1.ini')
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
    default_workspace = os.path.expanduser("~/.dgit.ini")
    if workspace != default_workspace and os.path.exists(workspace): 
        print("Removing tree", workspace) 
        shutil.rmtree(workspace) 
    
def workspace_setup(): 
    print("setup")
    clean_workspace() 
    api.initialize() 
    
def workspace_teardown(): 
    print("teardown")
    clean_workspace() 

def create_sample_repo(username, reponame): 
    # Now try with options 
    repo = api.init(username, reponame,
                    setup=None,
                    options={
                        "title": "Simple",
                        "description": "Simple dataset"
                    },
                    noinput=True
                )
    return repo 

def create_sample_s3_repo(username, reponame): 
    # Now try with options 
    repo = api.init(username, reponame,
                    setup='s3+git',
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
    's3': ['test_s3', 'testrepo_s3', 's3+git']
}

    
###########################################
# Group 1
# Simple checks
###########################################
@with_setup(workspace_setup, workspace_teardown)
def test_missing_repo():
    with assert_raises(UnknownRepository):
        api.lookup(repo_configurations['simple1'][0],
                   repo_configurations['simple1'][1])

###########################################
# Group 2 
# Check creation process. Check the content
###########################################
@with_setup(workspace_setup,None)
def test_start_group1():
    """
    Start group1 
    """
    pass 


def test_create_repo():
    """
    Create a repo
    """

    for name in repo_configurations: 
        
        #  This should fail
        with assert_raises(IncompleteParameters):
            repo = api.init(repo_configurations[name][0],
                            repo_configurations[name][1],
                            setup=repo_configurations[name][2],
                            noinput=True)

        #  This should be successful 
        repo = create_sample_repo(repo_configurations[name][0],
                                  repo_configurations[name][1])
        assert repo is not None 
    
        # Check if all the files have been created 
        rootdir = repo.rootdir 
        for suffix in ["", '.git', '.gitignore', 'datapackage.json']: 
            path = os.path.join(rootdir, suffix)
            assert os.path.exists(path)

    print("Completed create repo") 
    

def test_sh_command():
    """
    Test whether sh commands work
    """

    repo = api.lookup(repo_configurations['simple1'][0],
                      repo_configurations['simple1'][1])
                      
    assert repo is not None

    output = api.shellcmd(repo, ['ls'])
    assert "datapackage.json" in output


def test_remote(): 
    """
    Repo backend 
    """

    repo = api.lookup(repo_configurations['s3'][0],
                      repo_configurations['s3'][1])
    assert repo is not None 
    
    result = api.remote(repo,['-v'])
    assert result['status'] == 'success' 
    assert result['message'] is not None 

    backend_repodir = get_remote_path(result) 
    assert os.path.exists(backend_repodir) 
    
    
    
    

def test_check_package():
    """
    Check datapackage.json 
    """
    repo = api.lookup(repo_configurations['simple1'][0],
                      repo_configurations['simple1'][1])

    assert repo is not None 
        
    rootdir = repo.rootdir
    path = os.path.join(rootdir, 'datapackage.json')    
    package = json.loads(open(path).read())

def test_repo_drop():
    """
    Drop repo 
    """
    repo = api.lookup(repo_configurations['simple1'][0],
                      repo_configurations['simple1'][1])
    assert repo is not None 

@with_setup(None, workspace_teardown)
def test_end_group1():
    """
    End group1 
    """
    pass 

###########################################
# Group 2
###########################################
@with_setup(workspace_setup,None)
def test_start_group2():
    """
    Start group2 
    """
    pass 

def test_listing():
    """
    List repos
    """
    repo1 = create_sample_repo(repo_configurations['simple1'][0],
                               repo_configurations['simple1'][1])
    print(repo1)
    repos = api.list_repos()
    assert len(repos) == 1
    
    repo2 = create_sample_repo(repo_configurations['simple2'][0],
                               repo_configurations['simple2'][1])
    repos = api.list_repos()
    assert len(repos) == 2 
    
def test_simple_add_files():
    """
    Check simple file addition
    """    
    repo = api.lookup('test1', 'testrepo1') 
    assert repo is not None 
    
    rootdir = repo.rootdir 
        
    # Create a temp file and add it 
    (fd, filename) = tempfile.mkstemp()
    try: 
        api.add(repo, [filename], ".")
        basename = os.path.basename(filename)
        path = os.path.join(rootdir, basename) 
        print(path) 
        print(filename)
        assert os.path.exists(path)
    except Exception as e:
        # Cleanup and throw the exception again 
        os.unlink(filename) 
        raise e 

    # Cleanup 
    os.unlink(filename) 

def test_status():
    """
    Status command
    """    

    repo = api.lookup(repo_configurations['simple1'][0],
                      repo_configurations['simple1'][1])
    assert repo is not None 

    result = api.status(repo) 
    assert isinstance(result, dict) 
    assert result['status'] == 'success' 

@with_setup(None, workspace_teardown)
def test_end_group2():
    """
    End group2 
    """
    pass 
