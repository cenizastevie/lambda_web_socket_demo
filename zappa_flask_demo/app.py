import os
import json
import boto3
from flask import Flask, request, jsonify
from zappa.asynchronous import task, AsyncException # AsyncException is still needed for error handling within Zappa's task system, even if not for .result chaining in this specific simplified flow
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import traceback # Added for better error logging

if os.environ.get('LAMBDA_TASK_ROOT') is None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    except Exception as e:
        pass

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
    return plot_public_url

def send_websocket_message(connection_id, message_data):
    if not apigw_management_client:
        print("WebSocket API endpoint not configured, cannot send message.")
        return

    try:
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message_data).encode('utf-8')
        )
    except apigw_management_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone.")
        pass # Client disconnected
    except Exception as e:
        print(f"Error sending WebSocket message to {connection_id}: {e}")
        print(traceback.format_exc()) # Print full traceback for websocket errors

@task
def process_csv_and_scatter_plot(csv_key, connection_id):
    plot_type = "scatter"
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

            send_websocket_message(connection_id, {
                "status": f"{plot_type}_plot_complete",
                "filename": csv_key,
                "plot_url": plot_public_url,
                "message": f"Successfully generated {plot_type} plot."
            })
        else:
            error_message = f"CSV '{csv_key}' is missing 'x_data' or 'y_data' columns for {plot_type} plot."
            print(error_message)
            send_websocket_message(connection_id, {
                "status": f"{plot_type}_plot_failed",
                "filename": csv_key,
                "message": error_message
            })
    except Exception as e:
        error_message = f"Error generating {plot_type} plot for {csv_key}: {str(e)}"
        print(error_message)
        print(traceback.format_exc()) # Print full traceback for debugging
        send_websocket_message(connection_id, {
            "status": f"{plot_type}_plot_failed",
            "filename": csv_key,
            "message": error_message
        })

@task
def process_csv_and_bar_plot(csv_key, connection_id):
    plot_type = "bar"
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

            send_websocket_message(connection_id, {
                "status": f"{plot_type}_plot_complete",
                "filename": csv_key,
                "plot_url": plot_public_url,
                "message": f"Successfully generated {plot_type} plot."
            })
        else:
            error_message = f"CSV '{csv_key}' is missing 'category' or 'value' columns for {plot_type} plot."
            print(error_message)
            send_websocket_message(connection_id, {
                "status": f"{plot_type}_plot_failed",
                "filename": csv_key,
                "message": error_message
            })
    except Exception as e:
        error_message = f"Error generating {plot_type} plot for {csv_key}: {str(e)}"
        print(error_message)
        print(traceback.format_exc()) # Print full traceback for debugging
        send_websocket_message(connection_id, {
            "status": f"{plot_type}_plot_failed",
            "filename": csv_key,
            "message": error_message
        })

# Removed assemble_plots_and_notify task as it's no longer needed for direct chaining

@task
def start_plot_generation_workflow(csv_key, connection_id):
    try:
        send_websocket_message(connection_id, {
            "status": "workflow_initiated",
            "filename": csv_key,
            "message": "CSV plot generation tasks initiated. Updates for each plot will follow."
        })

        # Directly dispatch the plot generation tasks
        process_csv_and_scatter_plot(csv_key, connection_id)
        process_csv_and_bar_plot(csv_key, connection_id)

        # No need to return anything specific here, as results are sent via WS by individual tasks
        return {"status": "success", "message": "Plot generation tasks dispatched"}
    except Exception as e:
        error_msg = f"An error occurred during workflow initiation: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        send_websocket_message(connection_id, {
            "status": "workflow_error",
            "filename": csv_key,
            "message": error_msg
        })
        return {"status": "error", "message": error_msg}

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
        # start_plot_generation_workflow is now responsible for dispatching individual plot tasks
        # and it will handle initial WebSocket notification.
        start_plot_generation_workflow(csv_key, connection_id)

        return jsonify({
            "message": "Plot generation workflow dispatched. Updates will be sent via WebSocket.",
            "csv_key": csv_key,
            "connection_id": connection_id
        }), 202
    except Exception as e:
        return jsonify(error=f'Failed to submit plot generation workflow: {str(e)}'), 500

if __name__ == '__main__':
    app.run(debug=True)