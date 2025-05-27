import os
import json
import boto3
import urllib.parse

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket = os.environ['BUCKET_NAME']
    # Parse filename from event (assume JSON body with 'filename')
    try:
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        filename = body['filename']
    except Exception as e:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing filename'})}

    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket, 'Key': filename},
        ExpiresIn=3600
    )
    return {
        'statusCode': 200,
        'body': json.dumps({'presigned_url': presigned_url, 'key': filename})
    }
