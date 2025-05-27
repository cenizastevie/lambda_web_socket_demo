# AWS SAM Deployment Instructions

## Prerequisites
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured with your credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- Python 3.11 installed (for local builds/tests)

## Project Structure Example
```
/your-project-root/
  web_socket_formation.yaml         # Your SAM template file
  /connect_handler/
    index.py                        # Lambda code for $connect
  /disconnect_handler/
    index.py                        # Lambda code for $disconnect
  /send_message_handler/
    index.py                        # Lambda code for sendmessage
```

## How to Build and Deploy

1. **Build your application using your specific template:**
   ```cmd
   sam build --template web_socket_formation.yaml
   ```

2. **Deploy your application (guided):**
   ```cmd
   sam deploy --guided --template web_socket_formation.yaml --capabilities CAPABILITY_NAMED_IAM
   ```
   - Follow the prompts to set stack name, region, and save configuration for future deploys.

3. **(Optional) Test locally:**
   ```cmd
   sam local invoke WebSocketConnectFunction --event events/connect.json --template web_socket_formation.yaml
   ```
   - You can create test event files in an `events/` folder.

## Notes
- Your AWS CLI credentials/config will be used by default.
- Make sure your `web_socket_formation.yaml` uses `AWS::Serverless::Function` and `CodeUri` for each Lambda.
- For more info, see: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started.html