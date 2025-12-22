FROM public.ecr.aws/lambda/python:3.12

# Set PYTHONPATH so 'app' is importable
ENV PYTHONPATH="/var/task/genai"

# Install dependencies
COPY genai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Lambda function code
COPY genai/ ./genai/

# Set the Lambda handler
CMD ["genai.scripts.core_lambda.lambda_handler"]

