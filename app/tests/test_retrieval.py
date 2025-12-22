from app.services.retrieval import DocumentRetriever
from app.services.chat_engine import ChatEngine
from app.utils.util import get_mock_data_path
import json

# Test with mock data

mock_data_path = get_mock_data_path()
retriever = DocumentRetriever(mock_data_path=mock_data_path) #table_name="documentTable"  # Optional Name of the dynamoDB Table for documents
engine = ChatEngine()

# Retrieve context
context = retriever.retrieve(
    document_id="doc-123e4567-e89b-12d3-a456-426614174000",
    user_query="What is Acme Corporation's revenue and how has it changed?"
)

print("Retrieved Context:")
print(context[:2000] + "... <Truncated>" if len(context) > 2000 else context)
#print (context)
print("\n" + "-" * 80)

# Use with ChatEngine
""" result = engine.invoke(
    user_query="What is Acme Corporation's revenue and how has it changed?",
    feature="qna",
    context=context
)

print(f"Success: {result['success']}")
if result['success']:
    print(f"Response: {result['response']}")
    print(f"Tokens - Input: {result['input_tokens']}, Output: {result['output_tokens']}, Total: {result['total_tokens']}")
    print(f"Response Time: {result['response_time']:.2f}s")
else:
    print(f"Error: {result['error']}") """


# print ("Retrieval with Metadata")
# result = retriever.retrieve_with_metadata(
#     document_id="doc-123e4567-e89b-12d3-a456-426614174000",
#     user_query="What is Acme Corporation's revenue and how has it changed?"
# )


# # Pretty-print the entire result dictionary
# print(json.dumps(result, indent=2))

# Get both context and metadata
#context = result["context"]
#chunks = result["chunks"]
#retrieval_time = result["retrieval_time"]
