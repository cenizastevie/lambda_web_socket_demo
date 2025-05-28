import os
import json
import boto3
from flask import Flask, request, jsonify
from zappa.asynchronous import task, AsyncException
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

if os.environ.get('LAMBDA_TASK_ROOT') is None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("INFO: .env file loaded for local development.")
    except ImportError:
        print("WARNING: python-dotenv not installed. Environment variables must be set manually for local testing.")
    except Exception as e:
        print(f"WARNING: Could not load .env file: {e}")

app = Flask(__name__)

S3_INPUT_BUCKET_NAME = os.environ.get('INPUT_BUCKET_NAME')
S3_OUTPUT_BUCKET_NAME = os.environ.get('OUTPUT_BUCKET_NAME')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

s3_client = boto3.client('s3')
apigw_management_client = None
if WEBSOCKET_API_ENDPOINT:
    apigw_management_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=WEBSOCKET_API_ENDPOINT
    )

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Headers'] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
    response.headers['Access-Control-Allow-Methods'] = "OPTIONS,POST,GET"
    return response

@app.route('/')
def hello_world():
    return 'Hello, Zappa and Flask!'

@app.route('/generate-presigned-url', methods=['POST', 'OPTIONS'])
def generate_presigned_url_endpoint():
    if request.method == 'OPTIONS':
        return '', 204
    if not S3_INPUT_BUCKET_NAME:
        return jsonify(error="INPUT_BUCKET_NAME environment variable not set."), 500
    try:
        body = request.json
        if not body or 'filename' not in body:
            return jsonify(error='Missing filename in request body.'), 400
        filename = body['filename']
    except Exception as e:
        return jsonify(error=f'Invalid request body: {str(e)}'), 400
    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_INPUT_BUCKET_NAME, 'Key': filename, 'ContentType': 'text/csv'},
            ExpiresIn=3600
        )
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return jsonify(error=f'Could not generate presigned URL: {str(e)}'), 500
    return jsonify({'presigned_url': presigned_url, 'key': filename}), 200

def upload_plot_to_s3(plot_data_bytes, plot_filename):
    if not S3_OUTPUT_BUCKET_NAME:
        raise ValueError("OUTPUT_BUCKET_NAME environment variable not set for S3 upload.")
    s3_client.put_object(
        Bucket=S3_OUTPUT_BUCKET_NAME,
        Key=plot_filename,
        Body=plot_data_bytes,
        ContentType='image/png'
    )
    plot_public_url = f"https://{S3_OUTPUT_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{plot_filename}"
    print(f"Uploaded {plot_filename} to {S3_OUTPUT_BUCKET_NAME}. Public URL: {plot_public_url}")
    return plot_public_url

def send_websocket_message(connection_id, message_data):
    if not apigw_management_client:
        print("Warning: WebSocket API Gateway Management Client not initialized. Cannot send message.")
        return
    try:
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message_data).encode('utf-8')
        )
        print(f"Message sent to connection {connection_id}: {message_data.get('status', 'unknown status')}")
    except apigw_management_client.exceptions.GoneException:
        print(f"Connection {connection_id} no longer exists. Skipping message.")
    except Exception as e:
        print(f"Error sending message to connection {connection_id}: {e}")

@task
def process_csv_and_scatter_plot(csv_key, connection_id):
    print(f"Starting scatter plot task for {csv_key}")
    try:
        obj = s3_client.get_object(Bucket=S3_INPUT_BUCKET_NAME, Key=csv_key)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        if 'x_data' in df.columns and 'y_data' in df.columns:
            plt.figure(figsize=(10, 6))
            plt.scatter(df['x_data'], df['y_data'])
            plt.title(f'Scatter Plot for {csv_key}')
            plt.xlabel('X Data')
            plt.ylabel('Y Data')
            plt.grid(True)
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            plot_filename = f"scatter_plot_{os.path.basename(csv_key).replace('.csv', '.png')}"
            plot_public_url = upload_plot_to_s3(buf.getvalue(), plot_filename)
            print(f"Scatter plot task completed for {csv_key}")
            return plot_public_url
        else:
            print(f"CSV {csv_key} missing 'x_data' or 'y_data' columns for scatter plot.")
            return None
    except Exception as e:
        print(f"Error in scatter plot task for {csv_key}: {e}")
        return None

@task
def process_csv_and_bar_plot(csv_key, connection_id):
    print(f"Starting bar plot task for {csv_key}")
    try:
        obj = s3_client.get_object(Bucket=S3_INPUT_BUCKET_NAME, Key=csv_key)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        if 'category' in df.columns and 'value' in df.columns:
            plt.figure(figsize=(10, 6))
            plt.bar(df['category'], df['value'])
            plt.title(f'Bar Plot for {csv_key}')
            plt.xlabel('Category')
            plt.ylabel('Value')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            plot_filename = f"bar_plot_{os.path.basename(csv_key).replace('.csv', '.png')}"
            plot_public_url = upload_plot_to_s3(buf.getvalue(), plot_filename)
            print(f"Bar plot task completed for {csv_key}")
            return plot_public_url
        else:
            print(f"CSV {csv_key} missing 'category' or 'value' columns for bar plot.")
            return None
    except Exception as e:
        print(f"Error in bar plot task for {csv_key}: {e}")
        return None

@task
def assemble_plots_and_notify(csv_key, connection_id, scatter_task_id, bar_task_id):
    print(f"Starting assemble_plots_and_notify for {csv_key}, connection_id: {connection_id}")
    send_websocket_message(connection_id, {
        "status": "assembling_plots",
        "filename": csv_key,
        "message": "Collecting plot results..."
    })
    scatter_plot_url = None
    bar_plot_url = None
    errors = []
    try:
        scatter_plot_url = AsyncException(process_csv_and_scatter_plot, scatter_task_id).result
        if scatter_plot_url is None:
            errors.append("Scatter plot generation failed.")
            print(f"Failed to get scatter plot URL for {csv_key}")
    except Exception as e:
        errors.append(f"Error retrieving scatter plot result: {e}")
        print(f"Error retrieving scatter plot result for {csv_key}: {e}")
    try:
        bar_plot_url = AsyncException(process_csv_and_bar_plot, bar_task_id).result
        if bar_plot_url is None:
            errors.append("Bar plot generation failed.")
            print(f"Failed to get bar plot URL for {csv_key}")
    except Exception as e:
        errors.append(f"Error retrieving bar plot result: {e}")
        print(f"Error retrieving bar plot result for {csv_key}: {e}")
    if errors:
        send_websocket_message(connection_id, {
            "status": "processing_failed",
            "filename": csv_key,
            "message": "Some plots could not be generated.",
            "errors": errors
        })
        print(f"Assemble plots failed for {csv_key} with errors: {errors}")
        return
    send_websocket_message(connection_id, {
        "status": "processing_complete",
        "filename": csv_key,
        "message": "All plots generated and uploaded!",
        "scatter_plot_url": scatter_plot_url,
        "bar_plot_url": bar_plot_url
    })
    print(f"All plots assembled and notification sent for {csv_key}.")

@app.route('/process-csv', methods=['POST', 'OPTIONS'])
def process_csv_endpoint():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        body = request.json
        if not body or 'csv_filename' not in body or 'connection_id' not in body:
            return jsonify(error='Missing csv_filename or connection_id in request body.'), 400
        csv_key = body['csv_filename']
        connection_id = body['connection_id']
    except Exception as e:
        return jsonify(error=f'Invalid request body: {str(e)}'), 400
    try:
        send_websocket_message(connection_id, {
            "status": "initiated",
            "filename": csv_key,
            "message": "CSV processing tasks initiated. You will receive updates via WebSocket."
        })
        scatter_task_id = process_csv_and_scatter_plot(csv_key, connection_id)
        bar_task_id = process_csv_and_bar_plot(csv_key, connection_id)
        assemble_plots_and_notify(csv_key, connection_id, scatter_task_id, bar_task_id)
        return jsonify({
            "message": "CSV processing tasks initiated. Final notification will be via WebSocket.",
            "csv_key": csv_key,
            "connection_id": connection_id,
            "scatter_task_id": str(scatter_task_id),
            "bar_task_id": str(bar_task_id)
        }), 202
    except Exception as e:
        print(f"Error initiating tasks: {e}")
        if connection_id:
             send_websocket_message(connection_id, {
                "status": "error_initiation",
                "filename": csv_key,
                "message": f"Could not initiate processing tasks: {str(e)}"
            })
        return jsonify(error=f'Could not initiate processing tasks: {str(e)}'), 500

if __name__ == '__main__':
    app.run(debug=True)