.\venv\Scripts\activate

zappa deploy dev

zappa update dev

curl -X POST -H "Content-Type: application/json" -d "{\"filename\": \"test_upload_local.csv\"}" http://127.0.0.1:5000/generate-presigned-url


curl -X POST -H "Content-Type: application/json" -d "{\"filename\": \"test_upload_local.csv\"}" https://d87zdfaob0.execute-api.us-east-1.amazonaws.com/dev/generate-presigned-url