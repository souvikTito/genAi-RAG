
"""
Chat Orchestrator - Integrates history, retrieval, and chat engine.
This is the main entry point for the core Chat Lambda handler.
"""

from typing import Dict, Optional
import os
from datetime import datetime, timezone
import base64
from app.services.history import ConversationHistory
from app.services.retrieval import DocumentRetriever
from app.services.chat_engine import ChatEngine
from app.utils.util import logger, get_mock_data_path, get_mock_history_path, prepare_csv_for_llm

try: 
    mock_history_path = get_mock_history_path()
    mock_document_path = get_mock_data_path()
    logger.info(f"Running orchestration on Dev mode: Mock Data Found at {mock_history_path}")
except:
    logger.info("Running orchestration on Prod mode")

class ChatOrchestrator:
    """
    Orchestrates the complete chat flow:
    1. Fetch conversation history
    2. Retrieve relevant document context
    3. Invoke chat engine
    4. Save new prompt
    """
    
    def __init__(self, 
                 chats_table: str = None,
                 prompts_table: str = None,
                 documents_table: str = None,
                 s3_documents_bucket: str = None,
                 region_name: str = "us-east-2",
                 mock_mode: bool = False,
                 mock_history_path=mock_history_path, mock_document_path=mock_document_path):
        """
        Initialize the chat orchestrator.
        
        Args:
            chats_table: DynamoDB chats table name
            prompts_table: DynamoDB prompts table name
            documents_table: DynamoDB documents table name
            region_name: AWS region
            mock_mode: Use mock data for testing
        """
        self.mock_mode = mock_mode
        
        # Get table names from env if not provided
        if chats_table is None:
            chats_table = os.getenv('CHATS_TABLE_NAME')
        if prompts_table is None:
            prompts_table = os.getenv('PROMPTS_TABLE_NAME')
        if documents_table is None:
            documents_table = os.getenv('DOCUMENTS_TABLE_NAME') 
        if s3_documents_bucket is None:
            s3_documents_bucket = os.getenv('S3_DOCUMENTS_BUCKET') 

        # Initialize components
        if mock_mode:
            self.history_manager = ConversationHistory(mock_data_path=mock_history_path)
            self.retriever = DocumentRetriever(mock_data_path=mock_document_path)
        else:
            self.history_manager = ConversationHistory(
                chats_table_name=chats_table,
                prompts_table_name=prompts_table
            )
            self.retriever = DocumentRetriever(
                table_name=documents_table,
                s3_documents_bucket=s3_documents_bucket,
                #region_name=region_name
            )
        
        self.chat_engine = ChatEngine()
        
        logger.info(f"ChatOrchestrator initialized (mock_mode={mock_mode})")
    
    def process_message(self,
                       chat_id: str, 
                       user_query: str,
                       document_ids: Optional[list[str]] = None,
                       session_id: Optional[str] = "session12345",
                       user_id: Optional[str] = "user12345",
                       feature: Optional[str] = None,
                       genai_params: Optional[Dict[str, any]] = None,
                       file_type: Optional[str] = "",
                       file_name: Optional[list[str]] = None,
                       max_history_turns: int = 30,
                       top_k_per_doc: int = 8,
                       prompt_id: str = "promptid123") -> Dict:
        """
        Process a user message with full context (history + document retrieval).
        
        Args:
            chat_id: Current chat identifier
            user_query: User's current question
            document_ids: Documents to retrieve context from (optional)
            session_id: Session identifier
            user_id: User identifier
            feature: GenAI feature to use (e.g., 'qna', 'docComparison')
            genai_params: Dict of GenAI parameters like:
                    {'style': 'concise', 'tone': 'formal' etc}
            max_history_turns: Maximum conversation turns to include
            top_k_per_doc: Most Number of document chunks to retrieve per document
            prompt_id: Unique promptId
            
        Returns:
            Dict with response, metadata, and prompt_id
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Processing Chat Service for chat_PK {chat_id}, prompt_PK {prompt_id}: with {len(document_ids or [])} documents")
        
        # Temp: save user query is a safe logeable format
        safe_user_query = user_query.encode('ascii', 'replace').decode()
        logger.info(f"User Query: {safe_user_query[:600]}...'")

        # Step 1: Fetch conversation history
        chat_history = self.history_manager.get_history(
            chat_id=chat_id, session_id=session_id,
            max_turns=max_history_turns,
            include_current=True  # Make it false in case we save current user query in Database before Chat engine invocation
        )
        
        # Step 2: Retrieve document context (if document_id provided)
        context = None
        if document_ids and len(document_ids)>0 :
            logger.info(f"Beginning Document Context Retrieval")
            if len(document_ids)==1:
                    # Single Document
                    context = self.retriever.retrieve(
                        document_id=document_ids[0],
                        user_query=user_query,
                        top_k=top_k_per_doc,
                        include_summary=True
                    )
                    logger.info(f"Retrieved context from document {document_ids[0]}: {len(context)} chars")
            else:
                # Multiple documents    
                context = self.retriever.retrieve_multi_document(
                document_ids=document_ids,
                user_query=user_query,
                top_k_per_doc=top_k_per_doc
                )
                logger.info(f"Retrieved context from {len(document_ids)} document(s): {len(context)} chars")

        # Step 3: Invoke chat engine
        result = self.chat_engine.invoke(
            user_query=user_query,
            feature=feature,
            genai_params=genai_params,
            chat_history=chat_history,
            context=context,
            prompt_id=prompt_id
        )
        
        end_time = datetime.now(timezone.utc)
        total_invocation_time = end_time-start_time
        logger.info(f"Chat orchestration completed in {total_invocation_time.total_seconds():.2f} seconds")

        # Step 5: Return complete response
        return {
            "success": result.get("success"),
            "promptId": prompt_id,
            "userId": user_id,
            "sessionId": session_id,
            "chatId": chat_id,
            "response": result.get("response"),
            "error": result.get("error"),
            "metadata": {
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "total_tokens": result.get("total_tokens"),
                "response_time": round(total_invocation_time.total_seconds(), 2),
                "bedrock_response_time": round(result.get("bedrock_response_time"), 2),
                "history_turns": len(chat_history) // 2,
                "document_id": document_ids,
                "file_type": file_type,
                "file_name": file_name
            },
            "timestamp": start_time.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        }

    def process_multimodal_message(self,
                                chat_id: str,
                                user_query: str,
                                file_type: str,    
                                document_ids: Optional[list[str]],
                                file_name: Optional[list[str]] = None,
                                session_id: Optional[str] = "session1234",
                                user_id: Optional[str] = "user12345",
                                feature: Optional[str] = "default",
                                genai_params: Optional[Dict[str, any]] = None,
                                max_history_turns: int = 30,  # to and from conversations count
                                prompt_id: str = "promptid123") -> Dict:
        """ 
        Process a message with image or CSV content.
        
        Args:
            chat_id: Current chat identifier
            user_query: User's question
            document_Ids: Document ID containing image/CSV data
            file_type: 'image' or 'csv'
            session_id: Session identifier
            user_id: User identifier
            feature: GenAI feature to use
            genai_params: Dict of GenAI parameters like:
                    {'style': 'concise', 'tone': 'formal' etc}
            max_history_turns: Maximum conversation turns
            prompt_id: Unique promptId
            
        Returns:
            Dict with response and metadata
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Processing multimodal message ({file_type}) for chat {chat_id} with {len(document_ids)} documents")
        
        # Temp: save user query is a safe logeable format
        safe_user_query = user_query.encode('ascii', 'replace').decode()
        logger.info(f"User Query: {safe_user_query[:600]}...'")
        
        # Step 1: Fetch conversation history
        chat_history = self.history_manager.get_history(
            chat_id=chat_id, session_id=session_id,
            max_turns=max_history_turns,
            include_current=False
        )
        
        # Step 2: Fetch ALL documents and extract content
        content_list = []
        
        logger.info(f"Document IDs requested: {document_ids}")
        for doc_id in document_ids:
            document = self.retriever._fetch_document(doc_id)
            
            if not document:
                logger.warning(f"Document {doc_id} not found, skipping")
                continue
            
            # Extract content based on file type
            if file_type == "image":
                content = document.get('imageData')
                upload_date = document.get('createdAt', 'Unknown date')
                logger.info(f"Date detected for Document by Chat Orchestrator: {upload_date}")
                summary = document.get('summary')
                if not content:
                    logger.warning(f"No image data in document {doc_id}")
                    continue
                
                # CHECK: If imageData is base64 string, decode it
                if isinstance(content, str):
                    logger.info(f"Image data is base64 string, decoding...")
    
                    try:
                        content = base64.b64decode(content)
                        logger.info(f"Decoded base64 image: {len(content)} bytes")  
                    except Exception as e:
                        logger.error(f"Failed to decode base64 image: {e}")
                        continue
                
                # Validate
                if not isinstance(content, bytes):
                    logger.error(f"Image content is not bytes: {type(content)}")
                    continue

                logger.info(f"Image loaded successfully: {len(content)} bytes")

                # Add to Images Content list
                content_list.append({
                    'content': content,
                    'file_name': document.get('fileName', f'file_{doc_id}.jpg'),
                    'summary': summary,
                    'upload_date': upload_date
                })

            elif file_type == "csv":
                content = document.get('csvContent')
                upload_date = document.get('createdAt', 'Unknown date')
                logger.info(f"Date detected for Document by Chat Orchestrator: {upload_date}")
                summary = document.get('summary')


                # Debug inspection goes here
                logger.info(f"Document {doc_id} csvContent type: {type(content)}")

                if not content:
                    logger.warning(f"No CSV content in document {doc_id}")
                    continue
                
                if not isinstance(content, list):
                    logger.warning(f"CSV content for document {doc_id} is not a list")
                    continue         
                
                # NEW: Prepare CSV with smart filtering
                prepared_csv = prepare_csv_for_llm(content, user_query, summary)
    
                if prepared_csv:
                    logger.info(f"Prepared CSV: {prepared_csv['total_rows']} total rows, "
                    f"sending {len(prepared_csv.get('rows', []))} rows or "
                    f"{len(prepared_csv.get('sample_rows', []))} sample + "
                    f"{len(prepared_csv.get('relevant_rows', []))} relevant rows")

                content_list.append({
                    'content': prepared_csv,  # Now a dict with structured data
                    'file_name': document.get('fileName', f'file_{doc_id}.csv'),
                    'summary': summary,
                    'upload_date': upload_date
                })


            else:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_type}",
                    "chatId": chat_id
                }
    
        if not content_list:
            return {
                "success": False,
                "error": "No valid image/CSV content found in provided documents",
                "chatId": chat_id
            }
        
        logger.info(f"Loaded {len(content_list)} {file_type} files for processing")
        
        # Step 3: Invoke chat engine with multimodal content
        result = self.chat_engine.invoke_multimodal(
            file_type=file_type,
            content_list=content_list,
            file_name=file_name if file_name else "",
            user_query=user_query,
            feature=feature,
            genai_params=genai_params,
            chat_history=chat_history,
            prompt_id=prompt_id
        )
        
        end_time = datetime.now(timezone.utc)
        total_invocation_time = end_time-start_time
        logger.info(f"Chat orchestration completed in {total_invocation_time.total_seconds():.2f} seconds")

        return {
            "success": result.get("success"),
            "promptId": prompt_id,
            "chatId": chat_id,
            'sessionId': session_id,
            "user_id": user_id,
            "response": result.get("response"),
            "error": result.get("error"),
            "metadata": {
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "total_tokens": result.get("total_tokens"),
                "response_time": round(total_invocation_time.total_seconds(), 2),
                "bedrock_response_time": round(result.get("bedrock_response_time"), 2),
                "history_turns": len(chat_history) // 2,
                "document_id": document_ids,
                "file_type": file_type,
                "file_name": file_name if file_name else None
            },
            "timestamp": start_time.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        }
    

if __name__ == "__main__":
    """Test the orchestrator with mock data"""
    print("=" * 80)
    print("Testing ChatOrchestrator")
    print("=" * 80)
    
    # Initialize in mock mode
    orchestrator = ChatOrchestrator(mock_mode=True)
    
    # Test 1: Simple message with document context
    print("\n--- Test 1: Message with Document Context ---")
    result1 = orchestrator.process_message(
        chat_id="chat-abc123",
        user_query="What new products did Acme launch in 2024?",
        document_ids=["doc-123e4567-e89b-12d3-a456-426614174000"],
        session_id="session-xyz789", # optional
        user_id="user-001", #optional
        #feature="qna",  # optional , else default
        max_history_turns=10,
        top_k_per_doc=5
    )
    
    if result1["success"]:
        print(f"Success!")
        print(f"Prompt ID: {result1['promptId']}")
        print(f"Response: {result1['response'][:1000]}...")
        print(f"Metadata: {result1['metadata']}")
    else:
        print(f"Error: {result1.get('error')}")


    ## Summary of Chat orchestrator 
    # chat_orchestrator.process_multimodal_message()/process_message()
    #     ↓
    # Fetches documents from DynamoDB
    #     ↓
    # Builds content_list = [{content, file_name}, ...]
    #     ↓
    # Calls chat_engine.invoke_multimodal(content_list=...)/.invoke_chat_engine()
    #     ↓
    # chat_engine calls _MultimodalPromptBuilder(content_list=...)/retrieval engine
    #     ↓
    # Invokes Bedrock
