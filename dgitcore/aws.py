#!/usr/bin/env 

import os, sys
import boto3 
from .config import get_config 

def get_session():
    config = get_config() 
    session = boto3.Session(aws_access_key_id=config['aws']['access'],
                            aws_secret_access_key=config['aws']['secret'],
                            region_name='us-east-1')

    return session


def list_objects(s3, bucket, prefix, maxkeys=1000): 
    objs = s3.meta.client.list_objects(Bucket=bucket,
                                       Prefix=prefix,
                                       Delimiter="/",
                                       MaxKeys=maxkeys
                                   )
    return objs 

def download_directory(s3, state, day, 
                       bucket, prefix, 
                       downloaddir): 

    """
    Find all the files that have to be downloaded...
    """
    try: 
        os.makedirs(downloaddir)
    except:
        pass 

    # Download the list of files...
    allfiles = list_objects(s3, bucket, prefix, maxkeys=10000) 
    allfiles = allfiles['Contents']
    
    # Check against existing list of files...
    donefiles = state['days'][day]['files']
    donefile_keys = [d['Key'] for d in donefiles] 

    toprocess = []
    for c in allfiles: 

        # Check whether we already processed this file. We may have
        # downloaded but not processed.
        s3path = c['Key']
        if s3path in donefile_keys and c.get("_Status",None) == 'processed': 
            print("We have already downloaded and processed this file", s3path)
            continue

        # Where should we store the file...? 
        localpath = os.path.join(downloaddir, os.path.basename(s3path))

        # Gather some housekeeping information
        # {'LastModified': datetime.datetime(2015, 9, 14, 15, 7, 33, tzinfo=tzutc()), 'StorageClass': 'STANDARD', 'Owner': {'ID': 'cfe4a849b93a18684bf4a8ad851941b63eaffcb7ee189a6bb3c9d9bb2e0abb31', 'DisplayName': 'ivolo'}, 'ETag': '"8d55502db975b37f7bac43d6b917cf80"', 'Key': 'segment-logs/mctPe02Qp3/1442188800000/1442242971838.7cbb4f5f0e83.1.10.5.ca7ee991-e4bf-497e-9aa3-2dd6c9e472d6.gz', 'Size': 1116737}
        c['_LocalFile'] = localpath 
        c['_Status'] = "downloaded"

        # Fix the format...
        c['LastModified'] = c['LastModified'].isoformat()

        # Add to the list that must be appended to the full list
        if s3path not in donefile_keys: 
            toprocess.append(c) 

        # => Download the file if needed..
        if os.path.exists(localpath): 
            statinfo = os.stat(localpath)
            if statinfo.st_size != c['Size']: 
                # File size doesnt match...
                os.remove(localpath)
            else: 
                print("File already exists. Skipping", localpath)
                continue

        print("Downloading", s3path, "=>", localpath)
        result = s3.meta.client.download_file(bucket, s3path, localpath)
        print("Completed download", s3path)


    print("To process", len(toprocess))
    return toprocess 
