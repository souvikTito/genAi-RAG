import json
import os
from app.utils.util import logger
from app.models.dynamodb import read_from_dynamodb, paginate_dynamodb_request

# Load environment variables
# from dotenv import load_dotenv
# load_dotenv()

class ChatSummaryHandler:
    """
    Handler for chat summary operations - Middle logic for Chat History Page
    """
   
    def __init__(self):
        self.table_name = os.getenv("CHATS_TABLE_NAME")
        logger.info(f"Initialized ChatSummaryHandler with table: {self.table_name}")
   
    def handle_event(self, event):
        """
        Main entry point for chat summary operations
        """
        action = event.get("action")
        payload = event.get("payload", {})
       
        logger.info(f"Handling action: {action} with payload keys: {list(payload.keys())}")
       
        if action == "get_recent_summaries":
            return self.get_recent_chat_summaries(payload)
        elif action == "search_summaries":
            return self.search_chat_summaries(payload)
        elif action == "get_chat_details":
            return self.get_chat_details(payload)
        else:
            logger.warning(f"Unknown action received: {action}")
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown action: {action}"}
            }
   
    def get_recent_chat_summaries(self, payload):
        """
        Returns last 10 chat summary in descending order
        """
        user_PK = payload.get("user_PK")
        page_size = payload.get("pageSize", 10)
        page_index = payload.get("pageIndex", 1)
        # max_results = payload.get("maxResults", 10)
       
        if not user_PK:
            error_msg = "Missing user_PK"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Getting recent chat summaries for user: {user_PK}")
       
        try:
            # Fetch one page of chats from DynamoDB
            chats, total_count, total_pages = paginate_dynamodb_request(
                table_name=self.table_name,
                gsi_name="ChatsBySession",
                partition_key="user_PK",
                partition_value=user_PK,
                sort_key="auditLastUpdateDateTime",
                page_size=page_size,
                page_index=page_index
            )
           
            # Simple format response
            chat_summaries = []
            for chat in chats:
                summary = {
                    "chat_PK": chat.get("chat_PK"),
                    "title": chat.get("title", "Untitled Chat"),
                    "auditLastUpdateDateTime": chat.get("auditLastUpdateDateTime", ""),
                    "summary": chat.get("summary", ""),
                    "session_PK": chat.get("session_PK"),
                    "genai_feature": chat.get("genai_feature", ""),
                    "messageCount": len(chat.get("prompt_PK", [])),
                    "incidentDescription": chat.get("incidentDescription", "")
                }
                chat_summaries.append(summary)
           
            logger.info(f"Returning {len(chat_summaries)} recent chat summaries for user {user_PK}")


            return {
            "statusCode": 200,
            "body": {
            "chatSummaries": chat_summaries,
            "count": len(chat_summaries),
            "user_PK": user_PK,
            "pageSize": page_size,
            "pageIndex": page_index,
            "totalCount": total_count,
            "totalPages": total_pages
            }
        }
           
        except Exception as e:
            error_msg = f"Error getting recent chat summaries: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
           
            
   
    def search_chat_summaries(self, payload):
        """
        Function to return Chats Summary based on search Keyword/selection
        """
        user_PK = payload.get("user_PK")
        search_keyword = payload.get("searchKeyword", "").strip()
        # sessionid = payload.get("sessionid")
        # genai_feature = payload.get("genai_feature")
        max_results = payload.get("maxResults", 20)
       
        if not user_PK:
            error_msg = "Missing user_PK"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Searching chat summaries for user: {user_PK}, keyword: '{search_keyword}'")
       
        try:
            # Build filters dictionary
            filters = {"status": "active"}
            # if sessionid:
            #     filters["sessionid"] = sessionid
            # if genai_feature:
            #     filters["genai_feature"] = genai_feature
                
            # Fetch chats from DynamoDB
            chats = read_from_dynamodb(
            table_name=self.table_name,
            index_name="ChatsBySession",
            partition_key="user_PK",
            partition_value=user_PK,
            sort_key="auditLastUpdateDateTime",
            sort_desc=True,
            limit=max_results)

            if not chats:
                chats = []
                print('----------------',chats)
           
            # Apply search keyword filter if provided
            matching_chats = []
            if search_keyword:
                search_lower = search_keyword.lower()
                for chat in chats:
                    # Simple search across fields
                    if (search_lower in chat.get("title", "").lower() or
                        search_lower in chat.get("summary", "").lower() or
                        search_lower in chat.get("incidentDescription", "").lower()):
                        matching_chats.append(chat)
            else:
                matching_chats = chats
           
            # Sort by updatedAt descending
            matching_chats.sort(key=lambda x: x.get('auditLastUpdateDateTime', ''), reverse=True)
           
            # Limit results
            limited_chats = matching_chats[:max_results]
           
            # Simple format results
            search_results = []
            for chat in limited_chats:
                result = {
                    "chat_PK": chat.get("chat_PK"),
                    "title": chat.get("title", "Untitled Chat"),
                    "auditLastUpdateDateTime": chat.get("lastUpdated", chat.get("auditLastUpdateDateTime", "")),
                    "summary": chat.get("summary", ""),
                    "session_PK": chat.get("session_PK"),
                    "genai_feature": chat.get("genai_feature", ""),
                    "messageCount": len(chat.get("prompt_PK", [])),
                    "incidentDescription": chat.get("incidentDescription", "")
                }
                search_results.append(result)
           
            logger.info(f"Found {len(search_results)} chat summaries matching search criteria")
           
            return {
                "statusCode": 200,
                "body": {
                    "chatSummaries": search_results,
                    "count": len(search_results),
                    "search_criteria": {
                        "search_keyword": search_keyword
                    }
                }
            }
           
        except Exception as e:
            error_msg = f"Error searching chat summaries: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
   
    def get_chat_details(self, payload):
        """
        Links to history module to fetch detailed Chat conversation History
        """
        chat_PK = payload.get("chat_PK")
        user_PK = payload.get("user_PK")
        # session_id = payload.get("sessionId")
       
        if not chat_PK or not user_PK:
            error_msg = "Missing chat_PK or user_PK"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Getting detailed chat history for chat: {chat_PK}")
       
        try:
            chat_items  = read_from_dynamodb(
            table_name=self.table_name,
            index_name="chatPKindex",
            partition_key="chat_PK",
            partition_value=chat_PK,
            limit=1,  # Increase limit to avoid missing older chats
        ) or []
           
            if not isinstance(chat_items, list) or len(chat_items) == 0:
                error_msg = f"Chat not found with ID: {chat_PK}"
                logger.warning(error_msg)
                return {
                    "statusCode": 404,
                    "body": {"error": error_msg}
                }
            
            
            chat_details = chat_items[0]
            # Verify user access
            if chat_details.get("user_PK") != user_PK:
                error_msg = "User not authorized to access this chat"
                logger.warning(error_msg)
                return {
                    "statusCode": 403,
                    "body": {"error": error_msg}
                }
            
            prompt_ids = chat_details.get("prompt_PK", [])
            prompt_details = []

            try:
                # Fetch all prompts for the user once
                all_prompts = read_from_dynamodb(
                    table_name=os.getenv("PROMPTS_TABLE_NAME"),
                    index_name="PromptsByUser",
                    partition_key="user_PK",
                    partition_value=user_PK,
                    sort_key="auditCreateDateTime",
                    sort_desc=True,
                    limit = 1000
                ) or []

                # Match each promptId to its corresponding record
                for prompt_id in prompt_ids:
                    if not prompt_id or not isinstance(prompt_id, str):
                        logger.warning(f"Skipping invalid promptId: {prompt_id}")
                        continue

                    matched_prompt = next(
                        (item for item in all_prompts if item.get("prompt_PK") == prompt_id),
                        None)
                    
                    if matched_prompt:
                        reply_data = {}
                        raw_reply = matched_prompt.get("response")

                        if isinstance(raw_reply, str):
                            try:
                                parsed = json.loads(raw_reply)
                                if isinstance(parsed, dict):
                                    # Check if 'response' inside is also a stringified JSON
                                    inner_response = parsed.get("response")
                                    if isinstance(inner_response, str):
                                        try:
                                            parsed["description"] = json.loads(inner_response)
                                            del parsed["response"]

                                        except json.JSONDecodeError:
                                            logger.warning(f"Failed to parse inner 'response' field for prompt {prompt_id}")
                                    reply_data = parsed
                                else:
                                    logger.warning(f"Parsed reply is not a dict for prompt {prompt_id}")
                                    reply_data = {"error": "Unexpected reply format"}
                            except json.JSONDecodeError:
                                logger.warning(f"JSON decode failed for prompt {prompt_id}")
                                reply_data = {"error": "Failed to parse reply content"}
                        elif isinstance(raw_reply, dict):
                            reply_data = raw_reply
                            inner_response = reply_data.get("response")
                            if isinstance(inner_response, str):
                                try:
                                    reply_data["description"] = json.loads(inner_response)
                                    del reply_data["response"]
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse inner 'response' field for prompt {prompt_id}")
                        else:
                            logger.warning(f"Reply is neither string nor dict for prompt {prompt_id}")
                            reply_data = {"error": "Invalid reply type"}

                        prompt_details.append({
                            "prompt_PK": prompt_id,
                            "promptText": matched_prompt.get("promptText"),
                            "reply": reply_data,
                            "feedback": matched_prompt.get("feedback")
                        })
                    else:
                        logger.warning(f"No prompt found for ID {prompt_id} under user {user_PK}")


            except Exception as e:
                logger.warning(f"Failed to fetch prompts for user {user_PK}: {e}")

            # Document metadata enrichment
            document_ids = chat_details.get("document_PK", [])
            document_details = []

            try:
                all_documents = read_from_dynamodb(
                    table_name=os.getenv("DOCUMENTS_TABLE_NAME"),
                    index_name="DocumentsByUser",
                    partition_key="user_PK",
                    partition_value=user_PK,
                    sort_desc=True,
                    limit=1000
                ) or []

                for doc_id in document_ids:
                    if not doc_id or not isinstance(doc_id, str):
                        logger.warning(f"Skipping invalid documentId: {doc_id}")
                        continue

                    matched_doc = next(
                        (item for item in all_documents if item.get("document_PK") == doc_id),
                        None
                    )

                    if matched_doc:
                        document_details.append({
                            "document_PK": doc_id,
                            "fileName": matched_doc.get("fileName"),
                            "fileSize": matched_doc.get("fileSize")
                        })
                    else:
                        logger.warning(f"No document found for ID {doc_id} under user {user_PK}")

            except Exception as e:
                logger.warning(f"Failed to fetch documents for user {user_PK}: {e}")

                

            return {
                "statusCode": 200,
                "body": {
                    "chatDetails": chat_details,
                    "prompts": prompt_details,
                    "documents": document_details,
                    "message": "Chat details retrieved successfully"
                }
            }

            
        except Exception as e:
            error_msg = f"Error getting chat details: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }


# Lambda handler function
def handler(event, context):
    """
    AWS Lambda handler for chat summary operations
    """
    logger.info("Chat summary handler invoked")
    chat_summary_handler = ChatSummaryHandler()
    return chat_summary_handler.handle_event(event)
