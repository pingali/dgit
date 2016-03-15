Auto Mode
----------

- username : Name of the user (string)
- reponame : Name of the dataset (unique for a given user) 
- remoteurl : Path to the archive of the repo
    - git@github.com:pingali/dgit.git 
    - https://github.com:pingali/dgit.git 
    - s3://mybucket/git/pingali/dgit.git 
- working-directory : Directory that must be searched for updated 
- tracking : Dictionary specifying files to include and exclude 

    - includes : list of patterns that should be used to include files
    - excludes : list of patterns that should be used to exclude files 

        - Example: .git 
