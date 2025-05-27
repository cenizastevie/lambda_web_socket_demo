import boto3
import os

dynamodb = boto3.client('dynamodb')
table_name = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    dynamodb.put_item(
        TableName=table_name,
        Item={'connectionId': {'S': connection_id}}
    )
    return {'statusCode': 200}
