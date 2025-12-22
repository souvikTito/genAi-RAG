from app.handlers import chat_handler
from app.handlers.prompt_template_handler import PromptTemplateHandler
from app.handlers.chat_summary_handler import ChatSummaryHandler
from app.utils import logger_context
from app.utils.util import configure_logger
from app.utils.helpers import get_latest_session_for_user
import json
import os
from app.models.s3 import s3
import uuid

s3_logs_bucket = os.getenv("S3_LOGS")

def lambda_handler(event, context):
    print(f"Incoming event: {json.dumps(event, default=str)}")

    # Parse body (handle API Gateway vs direct invocation)
    if "body" in event:
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Invalid JSON: {str(e)}"}),
                "headers": {"Content-Type": "application/json"}
            }
    else:
        body = event

    print(f"Parsed Body: {json.dumps(body, default=str)}")

    # Extract user_PK - check both locations
    user_PK = None
    session_PK =  None
    chat_PK = None
    action = body.get("action")
    
    # Check if user_PK is directly in body (like /chat)
    if "user_PK" in body:
        user_PK = body.get("user_PK")
        session_PK = body.get("session_PK")
        chat_PK = body.get("chat_PK")
        prompt_PK = str(uuid.uuid4()) # Generate unique Prompt ID
        # Set logger
        logger = configure_logger(request_id=session_PK, chat_id=chat_PK, prompt_id=prompt_PK)
    
    # Or check if it's nested in payload (like get_recent_summaries)
    elif "payload" in body:
        payload = body.get("payload", {})
        user_PK = payload.get("user_PK")

        # Configure logger
        session_PK = get_latest_session_for_user(user_PK)
        logger = configure_logger(request_id=session_PK)
    
    if not user_PK:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "user_PK is required"}),
            "headers": {"Content-Type": "application/json"}
        }

    
    logger.info(f"Lambda Started for user_PK: {user_PK}, session_PK: {session_PK}, chat_PK: {chat_PK}")
    
    try:
        path = event.get("path", "") 

        if path.endswith("/chat"):
            logger.info("Routing to chat_handler.chat_response")
            response_body = chat_handler.chat_response(event, prompt_PK)
            print('THE RETURNED RESPONSE BODY IS:',response_body)
    
        elif path.endswith("/feedback"):
            logger.info("Routing to feedback")
            response_body = chat_handler.feedback(event)
                
        elif path.endswith("/prompt-template"): 
            logger.info("Routing to PromptTemplateHandler")
            handler = PromptTemplateHandler() 
            response_body = handler.handle_event(body)

        elif path.endswith("/chat-history-summary"):
            logger.info("Routing to ChatSummaryHandler")
            handler = ChatSummaryHandler()
            response_body = handler.handle_event(body)

        elif path.endswith("/mpg-core-lambda-handler"):
            logger.info("Health check route hit")
            response_body = {
                "statusCode": 200,
                "message": "Lambda is working fine",
                "path": path,
                "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT"}
            }

        else: 
            logger.warning(f"Route not found for path: {path}")
            return { 
                "statusCode": 404, 
                "body": json.dumps({"error": "Route not found"}), 
                "headers": {"Content-Type": "application/json"} 
                }

        logger.info("Handler executed successfully")

        return {
            "statusCode": response_body.get("statusCode", 200),
            "body": json.dumps(response_body, default=str),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT"
            }
        }

    except Exception as e:
        logger.error(f"Unhandled error in lambda: {str(e)}")
        return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Sorry, something went wrong. Check the error exception.",
                    "details": str(e)
                }),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT"
                }
        }

    finally:
        try:
            log_file_path = getattr(logger_context, "log_file_path", None)
            logger.info(f"Preparing to upload log file: {log_file_path}")

            if log_file_path and os.path.exists(log_file_path):
                for handler in logger.handlers: 
                    handler.flush()
                
                # Extract just the filename for the S3 key
                filename = os.path.basename(log_file_path)           
                s3.upload_file(
                    Filename=log_file_path,
                    Bucket=s3_logs_bucket,
                    Key=f"corelogs/{filename}"
                )
                print (f"Uploaded log file to S3: corelogs/{filename}")
                logger.info(f"Uploaded log file to S3: corelogs/{filename}")

                # Delete the file after upload
                try:
                    os.remove(log_file_path)
                    logger.info(f"Log file deleted: {log_file_path}")
                except Exception as e:
                    print(f"Failed to delete Log file: {str(e)}") 
                    logger.info(f"Failed to delete Log file: {str(e)}")  
            else:
                print(f"Log file not found at {log_file_path}, skipping S3 upload.")
                logger.error(f"Log file not found at {log_file_path}, skipping S3 upload.")
                
        except Exception as upload_error:
            print(f"Failed to upload log file to S3: {upload_error}")
            logger.error(f"Failed to upload log file to S3: {upload_error}")



