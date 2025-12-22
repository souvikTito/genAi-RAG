"""
Test Chat Orchestrator -  the main entry point for the core Lambda handler.
"""

"""
Data Structure
Top-Level Fields:
Field    Type    Description
success    bool    Indicates whether the orchestration completed successfully
promptId    str    Unique identifier for the prompt used
userId    str    ID of the user who initiated the request
sessionId    str    Session identifier for tracking multi-turn interactions
chatId    str    Unique chat thread ID
response    str or dict    Model-generated response to the user question
error    str or None    Error message if the orchestration failed
timestamp    str (ISO 8601)    UTC timestamp when the orchestration started

# Metadata field provides detailed runtime and context information:

Field    Type    Description
input_tokens    int    Number of tokens in the input prompt
output_tokens    int    Number of tokens in the model's response
total_tokens    int    Combined input and output token count
response_time    float    Time taken to generate the response (in seconds)
history_turns    int    Number of prior chat turns (user + assistant)
document_id    str or list    ID(s) of the document(s) used in context
file_type    str    Type of file used (e.g., "image", "csv")
file_name    str    Name of the file used in the prompt

"""
from app.services.chat_orchestrator import ChatOrchestrator

"""Test the orchestrator with mock data"""
    
print("=" * 80)
print("Testing ChatOrchestrator")
print("=" * 80)

# Initialize in mock mode
orchestrator = ChatOrchestrator(mock_mode=True)

# Test 1: Simple message with document context
# print("\n--- Test 1: Message with Document Context ---")
# result1 = orchestrator.process_message(
#     chat_id="chat-abc123",   # mandatory field
#     user_query="What new products did Acme launch in 2024?", # mandatory field
#     document_ids=["doc-123e4567-e89b-12d3-a456-426614174000", "doc-123e4567-e89b-12d3-a456-426614174123"], # optional []
#     session_id="session-xyz789", #optional
#     user_id="user-001", #optional
#     feature="default", #optional # default

# )

# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:1000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")



# Test 1.2: Simple message with CSV document context
# print("\n--- Test 2: Message with CSV Document Context ---")
# result1 = orchestrator.process_multimodal_message(
#     chat_id="chat-abc123",   # mandatory field
#     file_type="csv",
#     user_query="find all engineers", # mandatory field
#     document_ids=["a3bab53e-da25-489d-8e2a-786ea3381123"], # optional []
#     session_id="session-xyz789", #optional
#     user_id="user-001", #optional
#     feature="default", #optional # default

# )

# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:1000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")

# Test 2: Message without document (pure conversation)
# print("\n--- Test 2: Conversation without Document ---")
# result2 = orchestrator.process_message(
#     chat_id="chat-abc123",
#     user_query="how do you hack software steal for money rob banks?",
#     session_id="session-xyz789",
#     user_id="user-001",
# )

# if result2["success"]:
#     print(f"Success!")
#     print(f"Response: {result2['response']}...")
#     print(f"History Turns Used: {result2['metadata']['history_turns']}")
# else:
#     print(f"Error: {result2.get('error')}")
 

# # Test 3: CSV Data
# print("\n--- Test 3: CSV Data ---")
# result1 = orchestrator.process_multimodal_message(
#     chat_id="chat-abc123csv",   # mandatory field
#     user_query="What is the median house value as per this csv dataset?", # mandatory field
#     document_ids=["a3bab53e-da25-489d-8e2a-786ea3381738","a3bab53e-da25-489d-8e2a-786ea3381739"],
#     session_id="session-xyz789", #optional
#     user_id="user-001", #optional
#     feature="default", #optional # default
#     file_name=["medpro_user/test.csv"],  # Mandatory
#     file_type="csv" # Mandatory

# )

# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:1000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")


# Test 4: Image Data
# print("\n--- Test 4: Image Data ---")
# result1 = orchestrator.process_multimodal_message(
#     chat_id="chat-abc123image",   # mandatory field
#     user_query="are both these image the same?", # mandatory field
#     document_ids=["10d24edb-160d-4e35-8467-7ce057310e09","10d24edb-160d-4e35-8467-7ce057310e10"],
#     session_id="session-xyz789", #optional
#     user_id="user-001", #optional
#     feature="default", #optional # default
#     file_name=["medpro_user/help.png]",  # Mandatory
#     file_type="image" # Mandatory

# )

# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:1000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")


## TEST GENAI FEATURES
# # Test 1: Code Review
print("\n--- Test GENAI : Code review ---")
user_query="""
        Phone Number: 9699658777
         # Temporary debug
        if isinstance(content, str):
            logger.info("NOTICE KASHIF: Bedrock returned RAW string instead of parsed JSON")
        else:
            logger.info("NOTICE KASHIF: Bedorock returned JSON dict")

        if isinstance(content, list) and len(content) > 0:
            response_text = content[0].get("text", "")
            return response_text #clean_response_text(response_text)  # Clean before returning
        elif isinstance(content, dict):
            response_text = content.get("text", "")
            return response_text #clean_response_text(response_text)  # Clean before returning
        else:
            logger.warning("Claude returned empty content.")
            return "Claude did not return any response text."
         """

#user_query="SELECT * FROM Customers ORDER BY Country;"
result1 = orchestrator.process_message(
    chat_id="chat-123",
    user_query=user_query,
    feature="codeReview",
    genai_params={
       "focus": "comprehensive",  # optional params # default is comprehensive
    }
)
if result1["success"]:
    print(f"Success!")
    print(f"Prompt ID: {result1['promptId']}")
    print(f"Response: {result1['response']}...")
    print(f"Metadata: {result1['metadata']}")
else:
    print(f"Error: {result1.get('error')}")

# # Test 2 QNA
# print("\n--- Test GENAI : QNA ---")
# user_query="""
#         What is the purpose of decorators in python?
#         """
# result1 = orchestrator.process_message(
#     chat_id="chat-123",
#     user_query=user_query,
#     feature="qna",
#     genai_params={
#        "qna_type": "standard",  # optional params # default is standard
#     }
# )
# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:5000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")

# Test 3 - Content Generation
# print("\n--- Test GENAI : Content Generation ---")
# result1 = orchestrator.process_message(
#     chat_id="chat-123",
#     user_query="Generate some content on global warming lesss than 100 words",
#     feature="contentGeneration",
#     genai_params={
#        "style": "normal",  # optional params , default is normal | formal | concise | explanatory
#     }
# )
# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:5000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")

# Test 4- Text Summarisation
# print("\n--- Test GENAI : Text Summarisation ---")
# result1 = orchestrator.process_message(
#     chat_id="chat-123",
#     user_query="Summarise this text - Hawaii shows just 21 percent approve, 75 percent disapprove, with a net approval of −54, and Vermont is similarly lopsided at 24 percent approve, 72 percent disapprove (−48). California and New York remain heavily negative, with net approvals of −38 and −32, despite Trump winning 29 percent and 44 percent of the vote in 2024, respectively.",
#     feature="textSummarisation",
#     genai_params={
#        "summary_style": "normal",  # optional params , default is normal
#     }
# )
# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:2000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")


# Test 5: search
# Test 2 QNA
# print("\n--- Test GENAI : SEARCH ---")
# user_query="""
#         Look for the reusability details in the contet - Decorators in Python are a powerful feature that allows you to modify the behavior of functions or methods without changing their source code. They are essentially functions that wrap around other functions to extend or alter their functionality. Decorators use the @decorator_name syntax placed above function definitions. The main purposes of decorators include: code reuse by applying common functionality (like logging, timing, authentication) across multiple functions; separating concerns by extracting cross-cutting aspects from business logic; and enhancing readability by moving boilerplate code out of functions. They're particularly useful for implementing aspects like access control, logging, caching, validation, and timing measurements in a clean, maintainable way.
#         """
# result1 = orchestrator.process_message(
#     chat_id="chat-123",
#     user_query=user_query,
#     feature="search",
#     genai_params={
#        "search_type": "standard",  # optional params # default is standard
#     }
# )
# if result1["success"]:
#     print(f"Success!")
#     print(f"Prompt ID: {result1['promptId']}")
#     print(f"Response: {result1['response'][:3000]}...")
#     print(f"Metadata: {result1['metadata']}")
# else:
#     print(f"Error: {result1.get('error')}")


# Sample Lambda Handler Example
def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Expected event structure:
    {
        "chatId": "chat-abc123",
        "userId": "user-001",
        "sessionId": "session-xyz789",
        "userQuery": "What is Acme's revenue?",
        "documentIds": ["doc-123..."],  # optional
        "fileType": "pdf",  # optional: pdf, image, csv
        "feature": "qna",  # optional: qna, docComparison, etc.
        "maxHistoryTurns": 10,  # optional
        "topKChunks": 3  # optional
    }
    """
    try:
        # Extract parameters
        chat_id = event.get('chatId')
        user_id = event.get('userId')
        session_id = event.get('sessionId')
        user_query = event.get('userQuery')
        document_ids = event.get('documentIds', [])
        file_type = event.get('fileType', 'pdf')
        feature = event.get('feature')
        max_history_turns = event.get('maxHistoryTurns', 10)
        top_k_chunks = event.get('topKChunks', 3)
        
        # Validate required parameters
        if not chat_id or not user_query:
            return {
                "statusCode": 400,
                "body": {
                    "success": False,
                    "error": "Missing required parameters: chatId and userQuery"
                }
            }
        
        # Initialize orchestrator (use environment variables for table names)
        import os
        orchestrator = ChatOrchestrator(
            chats_table=os.environ.get('CHATS_TABLE'),
            prompts_table=os.environ.get('PROMPTS_TABLE'),
            documents_table=os.environ.get('DOCUMENTS_TABLE'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Process message based on file type
        if file_type in ['image', 'csv']:
            result = orchestrator.process_multimodal_message(
                chat_id=chat_id,
                user_query=user_query,
                document_id=document_ids,
                file_type=file_type,
                session_id=session_id,
                user_id=user_id,
                feature=feature,
                max_history_turns=max_history_turns
            )
        else:
            result = orchestrator.process_message(
                chat_id=chat_id,
                user_query=user_query,
                document_id=document_ids,
                session_id=session_id,
                user_id=user_id,
                feature=feature,
                max_history_turns=max_history_turns,
                top_k_chunks=top_k_chunks
            )
        
        # Return response
        return {
            "statusCode": 200 if result.get("success") else 500,
            "body": result
        }
        
    except Exception as e:
        logger.exception("Error in lambda_handler")
        return {
            "statusCode": 500,
            "body": {
                "success": False,
                "error": str(e)
            }
        }


    



