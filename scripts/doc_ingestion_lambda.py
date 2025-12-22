# This lambda is linked to the s3 ingestion event
from app.handlers import ingestion_handler
from app.utils.helpers import parse_s3_key, get_latest_session_for_user
from app.utils.util import configure_logger
from app.utils import logger_context
from app.models.s3 import s3
import os

s3_logs_bucket = os.getenv("S3_LOGS_BUCKET")

def doc_handler(event,context):

    #Extract documentId
    try:
        record = event["Records"][0]
        key = record["s3"]["object"]["key"]
        user_PK, document_PK, filename = parse_s3_key(key)
    except Exception as e:
        print(f"Failed to parse S3 key: {str(e)}")
        document_PK = "document123"

    session_PK = get_latest_session_for_user(user_PK)
    logger_context.request_id = document_PK
    logger = configure_logger(request_id=document_PK)
    logger.info(f"Document ingestion triggered for document_PK: {document_PK}, user_PK: {user_PK}, session_PK: {session_PK}")

    try:
        return ingestion_handler.doc_ingestion(event)
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }
    
    finally:
        try:
            log_file_path = getattr(logger_context, "log_file_path", None)
            logger.info(f"Preparing to upload log file: {log_file_path}")

            if log_file_path and os.path.exists(log_file_path):
                for handler in logger.handlers: 
                    handler.flush()
                
               # Extract just the filename for the S3 key
                file_name = os.path.basename(log_file_path)           
                s3.upload_file(
                    Filename=log_file_path,
                    Bucket=s3_logs_bucket,
                    Key=f"doclogs/{file_name}"
                )
                logger.info(f"Uploaded log file to S3: doclogs/{file_name}")
            else:
                logger.warning(f"Log file not found at {log_file_path}, skipping S3 upload.")
                
        except Exception as upload_error:
            logger.warning(f"Failed to upload log file to S3: {upload_error}")

    

# if __name__ == "__main__":
#     # Simulated event
#     event = {
#         "httpMethod": "POST",
#         "body": '{"document": "Sample text for ingestion"}',
#         "headers": {
#             "Content-Type": "application/json"
#         }
#     }

#     # Simulated context
#     class Context:
#         def __init__(self):
#             self.function_name = "docIngestionTest"
#             self.memory_limit_in_mb = 128
#             self.invoked_function_arn = "arn:aws:lambda:local"
#             self.aws_request_id = "localRequestId"

#     context = Context()

#     # Run the handler
#     response = doc_handler(event, context)
#     print("Lambda response:", response)
# Output is Document processing completed flag notification to Frontend

