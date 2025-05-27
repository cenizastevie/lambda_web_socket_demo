FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum install -y gcc libjpeg-turbo-devel zlib-devel

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy function code
COPY app.py ./

# Set the CMD to your handler
CMD ["app.lambda_handler"]
