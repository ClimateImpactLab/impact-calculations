import boto
import boto.s3.connection

access_key, secret_key = read_credentials('s3creds.txt')

bucket_name = 'put your bucket name here!'
gateway = 'griffin-objstore.opensciencedatacloud.org'

conn = boto.connect_s3(
        aws_access_key_id = access_key,
        aws_secret_access_key = secret_key,
        host = gateway,
        #is_secure=False,               # uncomment if you are not using ssl
        calling_format = boto.s3.connection.OrdinaryCallingFormat(),
        )

bucket = conn.create_bucket(bucket_name)

# upload file 
key = bucket.new_key(filename) 
key.set_contents_from_filename(filename)

# download file
key = bucket.get_key(filename) 
key.get_contents_to_filename('./filename') 
