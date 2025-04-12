import os
import configparser
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

def load_aws_profiles():
    """Load AWS profiles from credentials and config files"""
    profiles = set()
    
    # Get home directory
    home = str(Path.home())
    
    # Load from credentials file
    creds_path = os.path.join(home, '.aws', 'credentials')
    if os.path.exists(creds_path):
        config = configparser.ConfigParser()
        config.read(creds_path)
        profiles.update(config.sections())
    
    # Load from config file
    config_path = os.path.join(home, '.aws', 'config')
    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        for section in config.sections():
            if section.startswith('profile '):
                profiles.add(section[8:])  # Remove 'profile ' prefix
    
    return sorted(list(profiles))

def create_aws_session(profile_name):
    """Create an AWS session with the given profile"""
    try:
        session = boto3.Session(profile_name=profile_name)
        return session
    except ClientError as e:
        raise Exception(f"Failed to create AWS session: {str(e)}")

def get_s3_client(session):
    """Get an S3 client from the session"""
    try:
        return session.client('s3')
    except ClientError as e:
        raise Exception(f"Failed to create S3 client: {str(e)}")

def list_buckets(s3_client):
    """List all S3 buckets"""
    try:
        response = s3_client.list_buckets()
        return response['Buckets']
    except ClientError as e:
        raise Exception(f"Failed to list buckets: {str(e)}")

def list_objects(s3_client, bucket, prefix='', delimiter='/'):
    """List objects in a bucket with the given prefix"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter=delimiter
        )
        return response
    except ClientError as e:
        raise Exception(f"Failed to list objects: {str(e)}")

def get_object_metadata(s3_client, bucket, key):
    """Get metadata for an S3 object"""
    try:
        response = s3_client.head_object(
            Bucket=bucket,
            Key=key
        )
        return response
    except ClientError as e:
        raise Exception(f"Failed to get object metadata: {str(e)}")

def download_file(s3_client, bucket, key, local_path):
    """Download a file from S3"""
    try:
        s3_client.download_file(bucket, key, local_path)
    except ClientError as e:
        raise Exception(f"Failed to download file: {str(e)}") 