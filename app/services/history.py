"""
History module for fetching and managing conversation history from DynamoDB.
Integrates with chat_engine.py for conversational context.
"""

import json, os
import time
from typing import List, Dict, Optional, Tuple
from app.models.dynamodb import dynamoDb
#from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone

from app.utils.util import logger, get_mock_history_path

class ConversationHistory:
    """
    Manages conversation history retrieval and formatting for RAG-enabled chat.
    """
    
    def __init__(self, 
                 chats_table_name: str = None,
                 prompts_table_name: str = None,
                 mock_data_path: str = None):
        """
        Initialize the conversation history manager.
        
        Args:
            chats_table_name: Name of the Chats DynamoDB table
            prompts_table_name: Name of the Prompts DynamoDB table
            mock_data_path: Path to JSON file for local testing (optional)
        """
        self.chats_table_name =  chats_table_name or os.getenv("CHATS_TABLE_NAME")
        self.prompts_table_name = prompts_table_name or os.getenv("PROMPTS_TABLE_NAME")
        self.mock_data_path = mock_data_path
        self.mock_data = None

        if mock_data_path:
            # Load mock data for local testing
            try:
                with open(mock_data_path, 'r') as f:
                    self.mock_data = json.load(f)
                logger.info(f"Loaded mock history from: {mock_data_path}")
            except Exception as e:
                logger.error(f"Error loading mock history: {e}")
                self.mock_data = {"chats": [], "prompts": []}
        else:
            # Initialize DynamoDB connections
            self.dynamodb = dynamoDb
            # Get from env if not provided
            if chats_table_name is None:
                chats_table_name = os.getenv('CHATS_TABLE_NAME')
            if prompts_table_name is None:
                prompts_table_name = os.getenv('PROMPTS_TABLE_NAME')
            
            # Validate before using
            if not chats_table_name:
                raise ValueError("CHATS_TABLE_NAME must be provided or set in environment")
            self.chats_table = self.dynamodb.Table(chats_table_name)
            self.prompts_table = self.dynamodb.Table(prompts_table_name)
            logger.info(f"ConversationHistory initialized for tables: {chats_table_name}, {prompts_table_name}")
    
    def _fetch_chat(self, chat_id: str) -> Optional[Dict]:
        """
        Fetch chat metadata from DynamoDB or mock data.
        
        Args:
            chat_id: Chat identifier
            
        Returns:
            Chat dictionary with metadata
        """
        logger.info(f"Looking for chat_id: '{chat_id}'")
        try:
            if self.mock_data:
                # Search in mock data
                for chat in self.mock_data.get("chats", []):
                    if chat.get("chatId") == chat_id:
                        logger.info(f"Found chat_PK in mock data: {chat_id}")
                        return chat
                logger.warning(f"chat_PK not found in mock data: {chat_id}")
                return None
            else:
                # Query DynamoDB using GSI
                response = self.chats_table.query(
                    IndexName='chatPKindex',
                    KeyConditionExpression='chat_PK = :chat_PK',
                    ExpressionAttributeValues={':chat_PK': chat_id}
                )
                items = response.get('Items', [])
                
                if items:
                    logger.info(f"Retrieved chat from DynamoDB: {chat_id}")
                    return items[0]  # Will always be exactly one item
                else:
                    logger.warning(f"Chat not found in DynamoDB: {chat_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching chat: {e}")
            return None
    
    def _fetch_prompts(self, prompt_ids: List[str], session_id: str = "session1234", chat_id: str = "chat1234") -> List[Dict]:
        """
        Fetch multiple prompts from DynamoDB or mock data.
        
        Args:
            prompt_ids: List of prompt identifiers
            
        Returns:
            List of prompt dictionaries sorted by createdAt
        """

        logger.info(f"Fetching Prompts from PromptTable by chat_PK: {chat_id}")
        prompts = []
        
        try:
            if self.mock_data:
                # Search in mock data
                mock_prompts = self.mock_data.get("prompts", [])
                #for prompt_id in prompt_ids:
                #    for prompt in mock_prompts:
                #        if prompt.get("promptId") == prompt_id:
                #            prompts.append(prompt)
                #            break
                prompts = [p for p in mock_prompts if p.get("chatId") == chat_id]
                logger.info(f"Retrieved {len(prompts)} prompts from mock data")
            else:
                # Batch get from DynamoDB
                #keys = [{'promptId': pid, 'sessionId': session_id} for pid in prompt_ids]
                
                #response = self.dynamodb.batch_get_item(
                #    RequestItems={
                #        self.prompts_table_name: {'Keys': keys}
                #    }
                #)
                #prompts = response.get('Responses', {}).get(self.prompts_table_name, [])
                response = self.prompts_table.query(
                    IndexName='PromptByChat_PK',
                    KeyConditionExpression='chat_PK = :chat_PK',
                    ExpressionAttributeValues={
                        ':chat_PK': chat_id
                    }
                )

                prompts = response.get('Items', []) # for query operation on dynamo

                logger.info(f"Retrieved {len(prompts)} prompts from DynamoDB")
            
            # Sort by createdAt timestamp
            prompts.sort(key=lambda x: x.get('auditCreateDateTime', ''))
            
            return prompts
            
        except Exception as e:
            logger.error(f"Error fetching prompts: {e}")
            return []
    
    def _format_for_chat_engine(self, prompts: List[Dict]) -> List[Dict]:
        """
        Format prompts into chat_engine compatible format.
        Include document_ids as metadata    
        
        Args:
            prompts: List of prompt dictionaries from database
            
        Returns:
            List in format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        formatted_history = []
        
        for prompt in prompts:
            # Add user message
            prompt_text = prompt.get('promptText', '')
            if prompt_text:
                user_message = {
                    "role": "user",
                    "content": prompt_text
                }

                # Store document IDs as metadata
                user_message["_metadata"] = {
                    #"document_ids": prompt.get('documentIds', []),
                    "prompt_id": prompt.get('prompt_PK')
                }
                formatted_history.append(user_message)
                            
            # Add assistant response
            response_data = prompt.get('response', {})
            if isinstance(response_data, str):
                # If response is stored as JSON string
                try:
                    response_data = json.loads(response_data)
                except:
                    pass
            
            response_text = ""
            if isinstance(response_data, dict):
                response_text = response_data.get('response', response_data.get('text', ''))
            elif isinstance(response_data, str):
                response_text = response_data
            
            if response_text:
                formatted_history.append({
                    "role": "assistant",
                    "content": response_text
                })

        # Debug Statement
        logger.info("FORMATTED HISTORY:")
        logger.info(formatted_history)
        logger.debug(f"Formatted {len(formatted_history)} messages for chat engine")
        return formatted_history
    
    def get_history(self, 
                   chat_id: str, session_id:str,
                   max_turns: int = 12,
                   include_current: bool = True) -> List[Dict]:
        """
        Get conversation history formatted for chat_engine.invoke().
        
        Args:
            chat_id: Chat identifier
            max_turns: Maximum number of conversation turns to include
            include_current: Whether to include the current prompt (usually False)
            
        Returns:
            List of formatted messages ready for ChatEngine
        """
        start_time = time.time()
        logger.info(f"Fetching history for chat: {chat_id}, max_turns: {max_turns}")
        
        # Fetch chat metadata
        chat = self._fetch_chat(chat_id)
        
        if not chat:
            logger.warning(f"No chat found for {chat_id}, returning empty history")
            return []
        
        # Get prompt IDs
        prompt_ids = chat.get('prompt_PK', [])
        
        if not prompt_ids:
            logger.info(f"No prompts found for chat {chat_id}")
            return []
        
        # Optionally exclude the last prompt (current one)
        if not include_current and len(prompt_ids) > 0:
            prompt_ids = prompt_ids[:-1]
        
        # Limit to max_turns (each turn = 1 user + 1 assistant message)
        if len(prompt_ids) > max_turns:
            prompt_ids = prompt_ids[-max_turns:]
        
        # Fetch prompts
        prompts = self._fetch_prompts(prompt_ids, session_id=session_id, chat_id=chat_id)
        logger.info(f"Successfully fetched {len(prompts)} prompts")

        # Format for chat engine
        formatted_history = self._format_for_chat_engine(prompts)
        
        duration = time.time() - start_time
        logger.info(f"Retrieved {len(formatted_history)/2} Chat Messages in {duration:.2f}s")
        
        return formatted_history
    
    def get_full_history(self, chat_id: str) -> Dict:
        """
        Get complete conversation history with full metadata.
        
        Args:
            chat_id: Chat identifier
            
        Returns:
            Dict with chat metadata and detailed prompt history
        """
        start_time = time.time()
        
        # Fetch chat
        chat = self._fetch_chat(chat_id)
        
        if not chat:
            return {
                "success": False,
                "error": f"Chat {chat_id} not found",
                "chat": {},
                "prompts": []
            }
        
        # Fetch all prompts
        prompt_ids = chat.get('prompt_PK', [])
        prompts = self._fetch_prompts(prompt_ids)
        
        # Build detailed history
        detailed_history = []
        for prompt in prompts:
            detailed_history.append({
                "promptId": prompt.get('prompt_PK'),
                "chatId": prompt.get('chat_PK'),
                "user_query": prompt.get('promptText'),
                "response": prompt.get('response'),
                "status": prompt.get('status'),
                "guardrails": prompt.get('guardrails'),
                "feedback": prompt.get('feedback'),
                "createdAt": prompt.get('createdAt')
            })
        
        duration = time.time() - start_time
        
        return {
            "success": True,
            "chat": {
                "chatId": chat.get('chat_PK'),
                "sessionId": chat.get('session_PK'),
                "user_id": chat.get('user_PK'),
                "documentIds": chat.get('document_PK', []),
                "title": chat.get('title'),
                "summary": chat.get('summary'),
                "createdAt": chat.get('auditCreateDateTime'),
                "updatedAt": chat.get('auditLastUpdateDateTime')
            },
            "prompts": detailed_history,
            "total_prompts": len(detailed_history),
            "retrieval_time": duration
        }
    
    def save_prompt_UNUSED(self, 
                   prompt_data: Dict,
                   update_chat: bool = True) -> bool:
        """
        Save a new prompt to DynamoDB and update chat.
        
        Args:
            prompt_data: Dict with promptId, chatId, promptText, response, etc.
            update_chat: Whether to update the chat's promptId list
            
        Returns:
            Success boolean
        """
        try:
            if self.mock_data:
                logger.info("Mock mode: Would save prompt to database")
                return True
            
            # Save prompt
            prompt_item = {
                'promptId': prompt_data['promptId'],
                'chatId': prompt_data['chatId'],
                'sessionId': prompt_data.get('sessionId'),
                'user_id': prompt_data.get('user_id'),
                'promptText': prompt_data['promptText'],
                'status': prompt_data.get('status', 'completed'),
                'response': json.dumps(prompt_data.get('response', {})),
                'guardrails': json.dumps(prompt_data.get('guardrails', {})),
                'feedback': prompt_data.get('feedback'),
                'createdAt': prompt_data.get('createdAt', datetime.now(timezone.utc).isoformat())
            }
            
            self.prompts_table.put_item(Item=prompt_item)
            logger.info(f"Saved prompt: {prompt_data['promptId']}")
            
            # Update chat's promptId list
            if update_chat:
                chat_id = prompt_data['chatId']
                self.chats_table.update_item(
                    Key={'chatId': chat_id},
                    UpdateExpression="SET promptId = list_append(if_not_exists(promptId, :empty_list), :new_prompt), updatedAt = :timestamp",
                    ExpressionAttributeValues={
                        ':new_prompt': [prompt_data['promptId']],
                        ':empty_list': [],
                        ':timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
                logger.info(f"Updated chat {chat_id} with new prompt")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving prompt: {e}")
            return False


# Convenience function
def get_chat_history(chat_id: str, 
                    max_turns: int = 10,
                    table_names: Dict[str, str] = None,
                    mock_data_path: str = None) -> List[Dict]:
    """
    Simple function to get chat history.
    
    Args:
        chat_id: Chat identifier
        max_turns: Maximum conversation turns
        table_names: Dict with 'chats' and 'prompts' table names
        mock_data_path: Path to mock JSON file (optional)
        
    Returns:
        Formatted history for ChatEngine
    """
    if table_names:
        history_manager = ConversationHistory(
            chats_table_name=table_names.get('chats'),
            prompts_table_name=table_names.get('prompts'),
            mock_data_path=mock_data_path
        )
    else:
        history_manager = ConversationHistory(mock_data_path=mock_data_path)
    
    return history_manager.get_history(chat_id, max_turns)


if __name__ == "__main__":
    # """Test the history module with mock data"""
    # print("=" * 80)
    # print("Testing ConversationHistory")
    # print("=" * 80)
    
    # # Get mock data path for local testing
    mock_history_path = get_mock_history_path()

    # # Initialize with mock data
    history_manager = ConversationHistory(mock_data_path=mock_history_path)
    
    # # Test: Get history
    test_chat_id = "chat-abc123"
    print(f"\nFetching history for chat: {test_chat_id}")
    print("-" * 80)
    
    history = history_manager.get_history(test_chat_id, max_turns=10)
    
    print(f"Retrieved {len(history)} messages:")
    for i, msg in enumerate(history, 1):
        role = msg['role'].upper()
        content = msg['content'][:600] + "..." if len(msg['content']) > 600 else msg['content']
        metadata = msg.get('_metadata', {})
        print(f"{i}. [{role}]: {content}| {metadata}")
    
    # print("\n" + "-" * 80)
    
    # Test: Get full history with metadata
    # full_history = history_manager.get_full_history(test_chat_id)
    
    # if full_history["success"]:
    #     print(f"\nFull History Retrieved:")
    #     print(f"Chat Title: {full_history['chat'].get('title')}")
    #     print(f"Chat Summary: {full_history['chat'].get('summary')}")
    #     print(f"Total Prompts: {full_history['total_prompts']}")
    #     print(f"Retrieval Time: {full_history['retrieval_time']:.2f}s")
    # else:
    #     print(f"Error: {full_history['error']}")
