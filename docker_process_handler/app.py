import os
import boto3
import pandas as pd
import io
import json
from PIL import Image, ImageDraw, ImageFont

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    input_bucket = os.environ['INPUT_BUCKET']
    output_bucket = os.environ['OUTPUT_BUCKET']
    apigw_url = os.environ.get('APIGW_MANAGEMENT_API')

    # Parse event for S3 key and connection id
    try:
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        key = body['key']
        connection_id = body['connection_id']
    except Exception as e:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing key or connection_id'})}

    # Download CSV from S3
    csv_obj = s3.get_object(Bucket=input_bucket, Key=key)
    df = pd.read_csv(csv_obj['Body'])

    # Generate image from CSV (simple text image for demo)
    img = Image.new('RGB', (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    text = df.to_string(index=False)
    d.text((10, 10), text, fill=(0, 0, 0), font=font)

    # Save image to buffer
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    output_key = key.rsplit('.', 1)[0] + '.png'

    # Upload image to output bucket
    s3.put_object(Bucket=output_bucket, Key=output_key, Body=img_buffer, ContentType='image/png', ACL='public-read')
    output_url = f'https://{output_bucket}.s3.amazonaws.com/{output_key}'

    # Send result URL back via WebSocket
    if apigw_url and connection_id:
        apigw = boto3.client('apigatewaymanagementapi', endpoint_url=apigw_url)
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'result_url': output_url})
        )

    return {'statusCode': 200, 'body': json.dumps({'result_url': output_url})}
