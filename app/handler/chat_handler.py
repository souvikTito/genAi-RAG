import json
import uuid
from app.services.chat_orchestrator import ChatOrchestrator
from app.models.chat import add_chat
from app.models.s3 import s3
from app.models.prompts import add_prompt
from app.models.dynamodb import dynamoDb, read_from_dynamodb, add_to_dynamodb
from app.utils.helpers import resolve_file_type
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key, Attr
from app.utils.util import logger, clean_dict, parse_claude_response, normalize_response_for_dynamo
import os
from app.models.dynamodb import dynamoDb
import time

doc_table_name = os.getenv("DOCUMENTS_TABLE_NAME")
doc_table = dynamoDb.Table(doc_table_name)

chat_table_name = os.getenv("CHATS_TABLE_NAME")

feedback_table_name = os.getenv("FEEDBACK_TABLE_NAME")
feedback_table = dynamoDb.Table(feedback_table_name)

prompt_table_name = os.getenv("PROMPTS_TABLE_NAME")
prompt_table = dynamoDb.Table(prompt_table_name)


write_lambda = os.getenv("DYNAMO_LAMBDA")

s3_logs_bucket = os.getenv("S3_LOGS")

orchestrator = ChatOrchestrator()

def chat_response(event, prompt_PK):
    start_time = time.time()
    try:
        1234
        logger.info("Received event for chat_response")
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event

        logger.info(f"Parsed request body: {body}")

        if not body.get("userQuery"):
            logger.warning("Missing required field: userQuery")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required field: userQuery"}),
                "headers": {"Content-Type": "application/json"}
            }
        
        chat_PK = body.get("chat_PK", "chat12345")
        session_PK = body.get("session_PK", "session12345")
        user_PK = body.get("user_PK", "user12345")
        prompt_PK = prompt_PK # str(uuid.uuid4())

        logger.info(f"Identifiers - chat_PK: {chat_PK}, prompt_PK: {prompt_PK}, session_PK: {session_PK}, user_PK: {user_PK}")
        print(f"Identifiers - chat_PK: {chat_PK}, prompt_PK: {prompt_PK}, session_PK: {session_PK}, user_PK: {user_PK}")

        userQuery = body["userQuery"]
        new_document_ids = body.get("document_PK", [])
        genai_feature = body.get("genai_feature","default")
        auditCreateDateTime = body.get("auditCreateDateTime")
        genAiParams = body.get("genAiParams",{})
        fileName = body.get("fileNames", [])
        promptTemplate_PK = body.get("promptTemplate_PK", '')

        file_type = ""
        if isinstance(fileName, list) and fileName:
            file_type = resolve_file_type("", fileName[0])

        if new_document_ids:
            logger.info(f"Updating chat_PK for documents: {new_document_ids}")
            for doc_id in new_document_ids:
                try:
                    doc_table.update_item(
                        Key={"document_PK": doc_id, "user_PK": user_PK},
                        UpdateExpression="SET chat_PK = :chat_PK",
                        ExpressionAttributeValues={":chat_PK": chat_PK}
                    )
                    logger.info(f"Updated document {doc_id} with chat_PK {chat_PK}")
                except Exception as e:
                    logger.error(f"Failed to update document {doc_id}: {e}")

        #Adding a buffer for write to complete
        time.sleep(0.5)

        document_PK = []
        try:
            logger.info(f"Querying documents by chat_PK: {chat_PK}")
            documents = read_from_dynamodb(
                table_name=doc_table_name,
                index_name="DocumentsByChatId",
                partition_key="chat_PK",
                partition_value=chat_PK
            )
            
            document_PK = [doc["document_PK"] for doc in documents if "document_PK" in doc]
            logger.info(f"Documents found for chat_PK {chat_PK}: {document_PK}")
            if not file_type:
                for doc in documents:
                    file_type = resolve_file_type(doc.get("contentType", ""), doc.get("fileName", ""))
                    if file_type:  # stop at first match
                        break

                logger.info(f"Resolved file_type from document metadata: {file_type}")
                
        except Exception as e:
            logger.error(f"Error querying documents by chat_PK: {e}")

        try:
            if file_type in ["csv", "image"]:
                logger.info("Calling orchestrator to process multimodel message")
                result = orchestrator.process_multimodal_message(
                    chat_id=chat_PK,
                    user_query=userQuery,
                    document_ids=document_PK,
                    session_id=session_PK,
                    user_id=user_PK,
                    feature=genai_feature,
                    prompt_id=prompt_PK,
                    genai_params = genAiParams,
                    file_type=file_type,
                    file_name=fileName
                )
            else:
                logger.info("Calling orchestrator to process message")
                print("Calling orchestrator to process message")
                result = orchestrator.process_message(
                    chat_id=chat_PK,
                    user_query=userQuery,
                    document_ids=document_PK,
                    file_type=file_type,
                    file_name=fileName,
                    session_id=session_PK,
                    user_id=user_PK,
                    feature=genai_feature,
                    prompt_id=prompt_PK,
                    genai_params=genAiParams
                )

            print(f"Orchestrator result: {result}") # for Lambda debug
            logger.info(f"Orchestrator result with Trace: {result}")

            # Validate result exists and has response
            if not result or not result.get("response") or not result["response"].get("response"):
                logger.error("Orchestrator returned invalid result")
                return {
                    'statusCode': 500,
                    'body': {
                            "promptId": prompt_PK,
                            "chatId": chat_PK,
                            "sessionId": session_PK,
                            "userId": user_PK,
                            "userQuery": userQuery,
                            "genai_feature": genai_feature,
                            "reply": {
                                "response": "Sorry, something went wrong (Response not in result from Bedrock). Please try again a bit later."
                            },
                            "metadata": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                            "errorCode": "CHAT_ORCHESTRATION_FAILURE - Invalid Result from Bedrock"
                        }
                }   
            
            # Parse response
            try:
                # Parse response using a custom nested parser function       
                response_data = parse_claude_response(result["response"].get("response"), userQuery)  

            except Exception as e:
                logger.error(f"Failed to parse response: {str(e)}, sessionId: {session_PK}, chat_PK: {chat_PK}")
                
                # safe fallback
                fallback_raw = result["response"] if isinstance(result,dict) and "response" in result else str(result)
                response_data = {
                        "response": fallback_raw or "Sorry, something went wrong during parsing or decode Bedrock response. Please try again a bit later."
                    }

            
            # Check if response is empty (handle both dict with 'response' key and direct string)
            if isinstance(response_data, dict):
                actual_content = response_data.get('response', '')
            else:
                actual_content = response_data

            if not actual_content or not str(actual_content).strip():
                logger.error(f"Bedrock returned empty response content, sessionId: {session_PK}, chat_PK: {chat_PK}", exc_info=True)
                print(f"Bedrock returned empty response content, sessionId: {session_PK}, chat_PK: {chat_PK}")
                response_data = {
                        "response": result.get("response", "Sorry, empty response from Bedrock. Please try again a bit later.")                        
                    }
                
        except Exception as e:
            logger.error(f"Chat Orchestration failed: {str(e)}, sessionId: {session_PK}, chat_PK: {chat_PK}", exc_info=True)
            print(f"Chat Orchestration failed: {str(e)}, sessionId: {session_PK}, chat_PK: {chat_PK}")
            return {
                'statusCode': 500,
                'body': {
                            "promptId": prompt_PK,
                            "chatId": chat_PK,
                            "sessionId": session_PK,
                            "userId": user_PK,
                            "userQuery": userQuery,
                            "genai_feature": genai_feature,
                            "reply": {
                                "response": "Sorry, something went wrong in the Chat Orchestration. Please reach out for Error logs."
                            },
                            "metadata": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                            "errorCode": "CHAT_ORCHESTRATION_FAILURE - Full Block Failed"
                        }
            }

        response_data = normalize_response_for_dynamo(response_data)

        title = response_data.get("title", "Chat") 
        chat_summary = response_data.get("chat_summary", "Conversation with Medpro LLM") 

        # Append promptId to promptIds array
        existing_prompt_ids = []
        try:
            chat_table = dynamoDb.Table(chat_table_name)
            chat_record = chat_table.get_item(Key={"chat_PK": chat_PK})
            if "Item" in chat_record:
                existing_prompt_ids = chat_record["Item"].get("prompt_PK", [])
        except Exception as e:
            logger.warning(f"Failed to fetch existing chat for promptIds update: {e}")
            print(f"Failed to fetch existing chat for promptIds update: {e}")

        # Normalize and deduplicate
        normalized_existing = [normalize(pid) for pid in existing_prompt_ids]
        normalized_prompt_id = normalize(prompt_PK)

        prompt_ids = list(dict.fromkeys(normalized_existing + [normalized_prompt_id]))

        chat_payload = {
            "chat_PK": chat_PK,
            "session_PK": session_PK,
            "user_PK": user_PK,
            "title":title,
            "summary": chat_summary,
            "prompt_PK": prompt_ids,
            "document_PK": document_PK,
            "promptTemplate_PK":promptTemplate_PK,
            "auditCreateDateTime": auditCreateDateTime,
            "genai_feature": genai_feature,
            "auditLastUpdateDateTime": result['timestamp']
        }

        end_time = time.time()
        gateway_response_time = round((end_time - start_time) * 1000, 2)  # ms

        prompt_payload = {
            "prompt_PK": prompt_PK,
            "session_PK": session_PK,
            "chat_PK": chat_PK,
            "user_PK": user_PK,
            "promptText": userQuery,
            "promptsStatus": "completed",
            "response": {
                "response": json.dumps(clean_dict(response_data)),
                "input_tokens": result["metadata"].get("input_tokens"),
                "output_tokens": result["metadata"].get("output_tokens"),
                "total_tokens": result["metadata"].get("total_tokens"),
                "response_time": result["metadata"].get("response_time"),
                "bedrock_response_time": result["metadata"].get("bedrock_response_time"),
            },
            "gateway_response_time": gateway_response_time,
            "guardrails": result["response"].get("trace", {}),
            "guardrailAction": result["response"].get("guardrail_action", {}),
            "feedback": body.get("feedback"),
            "auditCreateDateTime": result['timestamp']
        }

        logger.info("Writing chat and prompt records to DynamoDB")

        # Write to Dynamo via Lambda
        add_chat(chat_payload, write_lambda)
        add_prompt(prompt_payload, write_lambda)

        #update chatid in doc table
        logger.info("chat_response completed successfully")
        print("chat_response completed successfully")
        return {
            "statusCode": 200,
            "body": {
                "prompt_PK": prompt_PK,
                "chat_PK": chat_PK,
                "session_PK": session_PK,
                "user_PK": user_PK,
                "userQuery": userQuery,
                "genai_feature": genai_feature,
                "reply": clean_dict(response_data),
                "metadata": result["metadata"],
                "timestamp": result["timestamp"]
            }
        }

    except Exception as e:
        logger.error(f"Unexpected error in Chat Handler: {str(e)}", exc_info=True)
        print(f"Unexpected error in chat_response: {str(e)}")
        return {
                'statusCode': 500,
                'body': {    
                            "prompt_PK": prompt_PK,
                            "chat_PK": chat_PK,
                            "session_PK": session_PK,
                            "user_PK": user_PK,
                            "userQuery": userQuery,
                            "genai_feature": genai_feature,
                            "reply": {
                                "response": "Sorry, something went wrong in the Chat Handler. Please try again a bit later."
                            },
                            "metadata": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                            "errorCode": f"CHAT_HANDLER_FAILURE - Unexpected error in Handler, {str(e)}, Bedrock Response: {result}"
                        }
        }

    finally:
        try:
            bedrock_file_path = f"/tmp/bedrock/bedrock_{prompt_PK}.json"
            # any file inside above folder in lambda get path
            
            logger.info(f"Preparing to upload Bedrock Response Json Log: {bedrock_file_path}")
            print(f"Preparing to upload Bedrock Response Json Log: {bedrock_file_path}")
            if bedrock_file_path and os.path.exists(bedrock_file_path): 
                # Extract just the filename for the S3 key
                # read file name .. should be 1 file only
                filename = os.path.basename(bedrock_file_path)           
                s3.upload_file(
                    Filename=bedrock_file_path,
                    Bucket=s3_logs_bucket,
                    Key=f"bedrocklogs/bedrock_{prompt_PK}.json"
                )
                logger.info(f"Uploaded Bedrock Response Json Log to S3: bedrocklogs/{filename}")
                print(f"Uploaded Bedrock Response Json Log to S3: bedrocklogs/{filename}")

                # Delete the file after upload
                try:
                    if os.path.exists(bedrock_file_path):
                        os.remove(bedrock_file_path)
                        print(f"Bedrock Response file deleted: {bedrock_file_path}")
                    else:
                        print(f"Bedrock Response file not found for deletion: {bedrock_file_path}")
                except Exception as e:
                    print(f"Failed to delete Bedrock Response file: {str(e)}")   

            else:
                logger.warning(f"Bedrock Response Json Log not found at {bedrock_file_path}, skipping S3 upload.")
        
        except Exception as upload_error:
            logger.warning(f"Failed to Bedrock Response Json file to S3: {upload_error}")
            print(f"Failed to Bedrock Response Json file to S3: {upload_error}")

def normalize(pid):
    return str(pid).strip().lower()

def feedback(event):
    try:
        logger.info("Received event for feedback")
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event

        logger.info(f"Parsed request body: {body}")

        user_PK = body.get("user_PK")
        session_PK = body.get("session_PK")
        chat_PK = body.get("chat_PK")
        prompt_PK = body.get("prompt_PK")
        isLiked = body.get("isLiked")

        if not all([user_PK, session_PK, chat_PK, prompt_PK]):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required feedback fields"}),
                "headers": {"Content-Type": "application/json"}
            }
        
        #check if existing
        response = feedback_table.query(
                IndexName="FeedbackByPrompt",
                KeyConditionExpression=Key("prompt_PK").eq(prompt_PK) & Key("user_PK").eq(user_PK)
            )

        if response["Items"]:
            # Update existing feedback record
            existing_item = response["Items"][0]
            feedback_PK = existing_item["feedback_PK"]

            feedback_table.update_item(
                Key={"feedback_PK": feedback_PK, "user_PK": user_PK},
                UpdateExpression="SET isLiked = :isLiked, auditLastUpdateDateTime = :dt",
                ExpressionAttributeValues={
                    ":isLiked": isLiked,
                    ":dt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                }
            )
            message = f"Feedback updated successfully for promptId {prompt_PK}"

        else:
            feedback_payload = {
                "feedback_PK": str(uuid.uuid4()),
                "session_PK": session_PK,
                "user_PK": user_PK,
                "chat_PK": chat_PK,
                "prompt_PK": prompt_PK,
                "isLiked": isLiked,
                "auditCreateDateTime": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            }

            add_to_dynamodb(feedback_table_name,feedback_payload,write_lambda)
            message = f"Feedback submitted successfully: with ID {feedback_payload['feedback_PK']}"

        prompt_table.update_item(
                Key={"prompt_PK": prompt_PK,"session_PK": session_PK},
                UpdateExpression="SET feedback = :isLiked, auditLastUpdateDateTime = :dt",
                ExpressionAttributeValues={
                    ":isLiked": isLiked,
                    ":dt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                }
            )
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": message}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to submit feedback: {str(e)}"}),
            "headers": {"Content-Type": "application/json"}
        }
