import boto3
import os
import json

apigw_management_api = boto3.client('apigatewaymanagementapi', endpoint_url=f"https://{os.environ['APIGW_DOMAIN']}/{os.environ['APIGW_STAGE']}")

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    body = json.loads(event['body'])
    action = body.get('action')
    message = body.get('message')

    if action == 'get_connection_id':
        # Respond with the connection ID
        apigw_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"connectionId": connection_id})
        )
    elif action == 'sendmessage' and message:
        # Echo the message back to the WebSocket client
        apigw_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"processed_message": message.upper()})
        )
    # You can add more actions here as needed

    return {'statusCode': 200}