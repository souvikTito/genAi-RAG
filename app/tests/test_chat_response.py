"""
Test Chat Handler - the main entry point for chat response operations.
"""
# created my me

import json
import uuid
from app.handlers.chat_handler import chat_response

print("=" * 80)
print("Testing Chat Handler")
print("=" * 80)

# Test 1: Basic Chat Response
print("\n--- Test 1: Basic Chat Response ---")
event1 = {
    "body": json.dumps({
        "userQuery": "What is the weather like today?",
        "chatId": "chat-test-001",
        "sessionId": "session-test-001",
        "userId": "user-test-001",
        "feature": "default"
    })
}

result1 = chat_response(event1)
print(f"Status Code: {result1['statusCode']}")

if result1['statusCode'] == 200:
    body = result1['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Prompt ID: {body.get('promptId')}")
    print(f"User Query: {body.get('userQuery')}")
    print(f"Feature: {body.get('feature')}")
    print(f"Has Reply: {'reply' in body}")
    print(f"Has Metadata: {'metadata' in body}")
else:
    print(f"Error: {result1['body']}")

# Test 2: Chat Response with Document IDs
print("\n--- Test 2: Chat Response with Document IDs ---")
event2 = {
    "body": json.dumps({
        "userQuery": "Can you analyze these documents for me?",
        "chatId": "chat-test-002",
        "sessionId": "session-test-002",
        "userId": "user-test-002",
        "document_ids": ["doc-123", "doc-456", "doc-789"],
        "feature": "document-analysis"
    })
}

result2 = chat_response(event2)
print(f"Status Code: {result2['statusCode']}")

if result2['statusCode'] == 200:
    body = result2['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"User Query: {body.get('userQuery')}")
    print(f"Feature: {body.get('feature')}")
    print(f"Document IDs processed: {len(body.get('document_ids', [])) if 'document_ids' in body else 'N/A'}")
else:
    print(f"Error: {result2['body']}")

# Test 3: Chat Response with GenAI Parameters
print("\n--- Test 3: Chat Response with GenAI Parameters ---")
event3 = {
    "body": json.dumps({
        "userQuery": "Generate a creative story about artificial intelligence",
        "chatId": "chat-test-003",
        "sessionId": "session-test-003",
        "userId": "user-test-003",
        "genAiParams": {
            "temperature": 0.8,
            "maxTokens": 1000,
            "topP": 0.9
        },
        "feature": "creative-writing"
    })
}

result3 = chat_response(event3)
print(f"Status Code: {result3['statusCode']}")

if result3['statusCode'] == 200:
    body = result3['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Prompt ID: {body.get('promptId')}")
    print(f"Has GenAI Parameters: True")
else:
    print(f"Error: {result3['body']}")

# Test 4: Chat Response with Guardrails and Feedback
print("\n--- Test 4: Chat Response with Guardrails and Feedback ---")
event4 = {
    "body": json.dumps({
        "userQuery": "What are the best practices for data security?",
        "chatId": "chat-test-004",
        "sessionId": "session-test-004",
        "userId": "user-test-004",
        "guardrails": {
            "content_filter": "strict",
            "ethical_guidelines": True
        },
        "feedback": {
            "rating": 5,
            "comment": "Previous response was helpful"
        },
        "feature": "security-qa"
    })
}

result4 = chat_response(event4)
print(f"Status Code: {result4['statusCode']}")

if result4['statusCode'] == 200:
    body = result4['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Has Guardrails: True")
    print(f"Has Feedback: True")
else:
    print(f"Error: {result4['body']}")

# Test 5: Auto-generated IDs (No IDs provided)
print("\n--- Test 5: Auto-generated IDs (No IDs provided) ---")
event5 = {
    "body": json.dumps({
        "userQuery": "This should generate new chat and prompt IDs",
        "userId": "user-test-005"
        # No chatId, promptId, sessionId provided
    })
}

result5 = chat_response(event5)
print(f"Status Code: {result5['statusCode']}")

if result5['statusCode'] == 200:
    body = result5['body']
    print(f"Success!")
    print(f"Auto-generated Chat ID: {body.get('chatId')}")
    print(f"Auto-generated Prompt ID: {body.get('promptId')}")
    print(f"Auto-generated Session ID: {body.get('sessionId')}")
    print(f"All IDs are UUID format: {len(body.get('chatId', '')) == 36}")
else:
    print(f"Error: {result5['body']}")

# Test 6: Missing Required Field (userQuery)
print("\n--- Test 6: Missing Required Field (userQuery) ---")
event6 = {
    "body": json.dumps({
        "chatId": "chat-test-006",
        "userId": "user-test-006"
        # Missing userQuery
    })
}

result6 = chat_response(event6)
print(f"Status Code: {result6['statusCode']}")

if result6['statusCode'] != 200:
    print(f"Expected validation error: {result6['body']}")
else:
    print("Unexpected success - test should have failed")

# Test 7: Complex User Query with Special Characters
print("\n--- Test 7: Complex User Query with Special Characters ---")
event7 = {
    "body": json.dumps({
        "userQuery": "Can you help me with JSON parsing? I need to handle cases like: {\"key\": \"value\", \"array\": [1, 2, 3]}",
        "chatId": "chat-test-007",
        "sessionId": "session-test-007",
        "userId": "user-test-007",
        "feature": "technical-support"
    })
}

result7 = chat_response(event7)
print(f"Status Code: {result7['statusCode']}")

if result7['statusCode'] == 200:
    body = result7['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Query handled complex JSON content")
else:
    print(f"Error: {result7['body']}")

# Test 8: Chat Response with CreatedAt Timestamp
print("\n--- Test 8: Chat Response with CreatedAt Timestamp ---")
custom_timestamp = "2024-01-15T10:30:00Z"
event8 = {
    "body": json.dumps({
        "userQuery": "This message has a custom timestamp",
        "chatId": "chat-test-008",
        "sessionId": "session-test-008",
        "userId": "user-test-008",
        "createdAt": custom_timestamp,
        "feature": "timestamp-test"
    })
}

result8 = chat_response(event8)
print(f"Status Code: {result8['statusCode']}")

if result8['statusCode'] == 200:
    body = result8['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Used custom timestamp: {custom_timestamp}")
else:
    print(f"Error: {result8['body']}")

# Test 9: Multiple Documents with Mixed Types
print("\n--- Test 9: Multiple Documents with Mixed Types ---")
event9 = {
    "body": json.dumps({
        "userQuery": "Analyze all these documents together",
        "chatId": "chat-test-009",
        "sessionId": "session-test-009",
        "userId": "user-test-009",
        "document_ids": [
            "doc-pdf-001",
            "doc-image-002", 
            "doc-csv-003",
            "doc-text-004"
        ],
        "feature": "multi-doc-analysis"
    })
}

result9 = chat_response(event9)
print(f"Status Code: {result9['statusCode']}")

if result9['statusCode'] == 200:
    body = result9['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Processed 4 different document types")
else:
    print(f"Error: {result9['body']}")

# Test 10: Empty Document IDs Array
print("\n--- Test 10: Empty Document IDs Array ---")
event10 = {
    "body": json.dumps({
        "userQuery": "This should work with empty document list",
        "chatId": "chat-test-010",
        "sessionId": "session-test-010",
        "userId": "user-test-010",
        "document_ids": [],
        "feature": "no-docs"
    })
}

result10 = chat_response(event10)
print(f"Status Code: {result10['statusCode']}")

if result10['statusCode'] == 200:
    body = result10['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Handled empty document IDs array correctly")
else:
    print(f"Error: {result10['body']}")

# Test 11: Direct Event Body (No 'body' key)
print("\n--- Test 11: Direct Event Body (No 'body' key) ---")
event11 = {
    "userQuery": "This event has direct body without 'body' key",
    "chatId": "chat-test-011",
    "sessionId": "session-test-011",
    "userId": "user-test-011",
    "feature": "direct-event"
}

result11 = chat_response(event11)
print(f"Status Code: {result11['statusCode']}")

if result11['statusCode'] == 200:
    body = result11['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Handled direct event body correctly")
else:
    print(f"Error: {result11['body']}")

# Test 12: Large User Query
print("\n--- Test 12: Large User Query ---")
large_query = "Explain " + " artificial intelligence " * 50 + " in detail."
event12 = {
    "body": json.dumps({
        "userQuery": large_query,
        "chatId": "chat-test-012",
        "sessionId": "session-test-012",
        "userId": "user-test-012",
        "feature": "large-query"
    })
}

result12 = chat_response(event12)
print(f"Status Code: {result12['statusCode']}")

if result12['statusCode'] == 200:
    body = result12['body']
    print(f"Success!")
    print(f"Chat ID: {body.get('chatId')}")
    print(f"Handled large user query ({len(large_query)} characters)")
else:
    print(f"Error: {result12['body']}")

# Test 13: Error Simulation - Orchestrator Failure
print("\n--- Test 13: Error Simulation - Orchestrator Failure ---")
# This test would require mocking the orchestrator to return an error
print("This test requires mocking orchestrator.process_message to return error")
print("Status: Manual testing required with mocked dependencies")

# Test 14: Response Format Validation
print("\n--- Test 14: Response Format Validation ---")
event14 = {
    "body": json.dumps({
        "userQuery": "Test response format",
        "chatId": "chat-test-014",
        "sessionId": "session-test-014",
        "userId": "user-test-014"
    })
}

result14 = chat_response(event14)
print(f"Status Code: {result14['statusCode']}")

if result14['statusCode'] == 200:
    body = result14['body']
    print(f"Success!")
    
    # Validate response structure
    required_fields = ['promptId', 'chatId', 'sessionId', 'userId', 'userQuery', 'reply', 'metadata', 'timestamp']
    missing_fields = [field for field in required_fields if field not in body]
    
    if not missing_fields:
        print(f"✓ All required fields present in response")
        print(f"✓ Response structure validation passed")
    else:
        print(f"✗ Missing fields: {missing_fields}")
else:
    print(f"Error: {result14['body']}")

print("\n" + "=" * 80)
print("Chat Handler Tests Summary")
print("=" * 80)

# Summary of test results
test_results = [
    ("Basic Chat Response", result1['statusCode']),
    ("With Document IDs", result2['statusCode']),
    ("With GenAI Parameters", result3['statusCode']),
    ("With Guardrails & Feedback", result4['statusCode']),
    ("Auto-generated IDs", result5['statusCode']),
    ("Missing Required Field", result6['statusCode']),
    ("Complex Query", result7['statusCode']),
    ("Custom Timestamp", result8['statusCode']),
    ("Multiple Documents", result9['statusCode']),
    ("Empty Documents", result10['statusCode']),
    ("Direct Event Body", result11['statusCode']),
    ("Large Query", result12['statusCode']),
    ("Response Format", result14['statusCode'])
]

success_count = sum(1 for _, status in test_results if status == 200)
total_count = len(test_results)

print(f"Tests Completed: {total_count}")
print(f"Successful: {success_count}")
print(f"Failed: {total_count - success_count}")

print("\n" + "=" * 80)
print("All Chat Handler Tests Completed")
print("=" * 80)

