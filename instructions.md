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

#
# ---
#

## How to Build and Deploy the S3/Lambda Web Template

1. **Build your application using the new template:**
   ```cmd
   sam build --template s3_lambda_web_template.yaml
   ```

2. **Deploy your application (guided):**
   ```cmd
   sam deploy --guided --template s3_lambda_web_template.yaml --capabilities CAPABILITY_NAMED_IAM
   ```
   - Follow the prompts to set stack name, region, and save configuration for future deploys.

3. **(Optional) Test locally:**
   ```cmd
   sam local invoke PresignUrlFunction --event events/presign.json --template s3_lambda_web_template.yaml
   sam local invoke DockerProcessFunction --event events/process.json --template s3_lambda_web_template.yaml
   ```
   - You can create test event files in an `events/` folder.

## Notes for the S3/Lambda Template
- Your AWS CLI credentials/config will be used by default.
- Make sure your `s3_lambda_web_template.yaml` uses `AWS::Serverless::Function` and `CodeUri` or `ImageUri` for each Lambda.
- For more info, see: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started.html

#
# ---

## How to Deploy Using AWS CloudFormation Directly

1. **Package your application (if using local code or Docker images):**
   ```cmd
   aws cloudformation package --template-file s3_lambda_web_template.yaml --s3-bucket <your-artifact-bucket> --output-template-file packaged-template.yaml
   ```
   - Replace `<your-artifact-bucket>` with an S3 bucket you own for deployment artifacts.

2. **Deploy the packaged template:**
   ```cmd
   aws cloudformation deploy --template-file s3_lambda_web_template.yaml --stack-name websocket-s3-demo --capabilities CAPABILITY_NAMED_IAM
   ```

3. **Monitor deployment:**
   - You can check status in the AWS Console or with:
     ```cmd
     aws cloudformation describe-stacks --stack-name websocket-s3-demo
     ```

## Notes for CloudFormation
- You must package the template if you use local Lambda code or Docker images.
- The AWS Console also supports uploading and deploying the template directly.
- For more info, see: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-cli-deploy.html

#
# ---

# One-line CloudFormation deploy command for Windows:
aws cloudformation deploy --template-file packaged-template.yaml --stack-name websocket-s3-demo --capabilities CAPABILITY_NAMED_IAM

#
# ---

## How to Deploy the Segregated Stacks

1. **Deploy S3 resources:**
   ```cmd
   aws cloudformation deploy --template-file s3_resources.yaml --stack-name websocket-s3-demo --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Deploy ECR resources:**
   ```cmd
   aws cloudformation deploy --template-file ecr_resources.yaml --stack-name websocket-ecr-demo --capabilities CAPABILITY_NAMED_IAM
   ```

3. **Build, tag, and push your Docker image to ECR:**
   - Get the ECR repository URI from the outputs of the ECR stack or AWS Console.
   - Authenticate Docker to ECR:
     ```cmd
     aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<your-region>.amazonaws.com
     ```
   - Build your Docker image:
     ```cmd
     docker build -t docker-process-handler-repo:latest ./docker_process_handler
     ```
   - Tag the image for ECR:
     ```cmd
     docker tag docker-process-handler-repo:latest <account-id>.dkr.ecr.<your-region>.amazonaws.com/docker-process-handler-repo:latest
     ```
   - Push the image to ECR:
     ```cmd
     docker push <account-id>.dkr.ecr.<your-region>.amazonaws.com/docker-process-handler-repo:latest
     ```

4. **Deploy Lambda functions:**
   ```cmd
   aws cloudformation deploy --template-file lambda_functions.yaml --stack-name websocket-s3-lambda --capabilities CAPABILITY_NAMED_IAM
   ```

- Make sure to deploy in this order: S3 → ECR → Docker image push → Lambda.
- If you update the Docker image, repeat step 3 before redeploying Lambda functions.

#
# ---