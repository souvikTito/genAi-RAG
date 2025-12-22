import boto3
import os, json
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, ClientError
from app.utils.util import logger

# Load environment variables
load_dotenv()

try: 
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', "")
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', "")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN", "")
    aws_region = os.getenv('AWS_REGION', 'us-east-2')
except:
    logger.info("AWS Credentials not in env file")

# Log credential status
logger.info("Initializing S3 client")
logger.debug(f"AWS Access Key loaded: {'Yes' if aws_access_key_id else 'No'}")
logger.debug(f"AWS Secret Key loaded: {'Yes' if aws_secret_access_key else 'No'}")
logger.debug(f"AWS Session Token loaded: {'Yes' if aws_session_token.strip() else 'No'}")
logger.debug(f"AWS Region: {aws_region if aws_region else ' '}")


# Initialize S3 client
try:
    s3 = boto3.client(
        service_name="s3",
        region_name=aws_region
    )
except Exception as e:
    logger.exception("Failed to initialize S3 client")
    raise

# List files in a bucket path
def list_files(bucket, prefix, limit=5):
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        if not contents:
            logger.warning(f"No files found in s3://{bucket}/{prefix}")
        else:
            for obj in contents[:limit]:
                logger.info(f"Found file: {obj['Key']}")
    except ClientError as e:
        logger.error(f"AWS ClientError: {e.response['Error']['Message']}")
    except BotoCoreError as e:
        logger.error(f"BotoCoreError: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during S3 listing")

# Read a JSON file from S3
def read_json_from_s3(bucket, key):
    try:
        logger.info(f"Trying to read JSON from s3://{bucket}/{key}")
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        logger.info(f"Successfully read JSON from s3://{bucket}/{key}")
        return data
    except ClientError as e:
        logger.error(f"AWS ClientError: {e.response['Error']['Message']}")
    except BotoCoreError as e:
        logger.error(f"BotoCoreError: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during S3 JSON read")
    return None

# Example usage
if __name__ == "__main__":
    list_files("mpg-dev-ai-raw-data-bucket", "seniorcare/")
