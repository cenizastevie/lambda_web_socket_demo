# app.py
import os
import json
import boto3
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- S3 Configuration ---
# Ensure BUCKET_NAME is set in your Zappa environment variables
# or directly in your zappa_settings.json as environment_variables
# For local testing, you might set it in your shell: export BUCKET_NAME="your-s3-bucket-name"
S3_BUCKET_NAME = os.environ.get('BUCKET_NAME')

# Initialize S3 client outside the route for efficiency (or within it if preferred)
s3_client = boto3.client('s3')

# --- CORS Headers (Flask Way) ---
# For handling CORS globally or per route
# You might want to use Flask-CORS extension for more robust handling
# pip install Flask-CORS
# from flask_cors import CORS
# CORS(app) # Enables CORS for all routes

@app.after_request
def add_cors_headers(response):
    """
    Adds CORS headers to every response.
    Consider using Flask-CORS extension for more robust handling.
    """
    response.headers['Access-Control-Allow-Origin'] = "*"  # Be specific in production!
    response.headers['Access-Control-Allow-Headers'] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
    response.headers['Access-Control-Allow-Methods'] = "OPTIONS,POST,GET" # Add GET if you have GET routes
    return response

@app.route('/')
def hello_world():
    return 'Hello, Zappa and Flask!'

@app.route('/generate-presigned-url', methods=['POST', 'OPTIONS'])
def generate_presigned_url_endpoint():
    # Handle OPTIONS requests for CORS preflight
    if request.method == 'OPTIONS':
        return '', 204 # No Content

    if not S3_BUCKET_NAME:
        return jsonify(error="S3_BUCKET_NAME environment variable not set."), 500

    try:
        # Flask's request.json handles parsing JSON body
        body = request.json
        if not body or 'filename' not in body:
            return jsonify(error='Missing filename in request body.'), 400
        filename = body['filename']
    except Exception as e:
        return jsonify(error=f'Invalid request body: {str(e)}'), 400

    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': filename, 'ContentType': 'text/csv'},
            ExpiresIn=3600
        )
    except Exception as e:
        # Log the actual error for debugging
        print(f"Error generating presigned URL: {e}")
        return jsonify(error=f'Could not generate presigned URL: {str(e)}'), 500

    return jsonify({'presigned_url': presigned_url, 'key': filename}), 200

if __name__ == '__main__':
    app.run(debug=True)