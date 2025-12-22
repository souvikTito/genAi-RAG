"""
Test Chat Summary Handler - the main entry point for chat summary operations.
"""

from app.handlers.chat_summary_handler import ChatSummaryHandler
import json

print("=" * 80)
print("Testing ChatSummaryHandler")
print("=" * 80)

# Initialize handler
handler = ChatSummaryHandler()

# Test 1: Get Recent Chat Summaries
print("\n--- Test 1: Get Recent Chat Summaries ---")
result1 = handler.get_recent_chat_summaries({
    "user_id": "user-001",
    "maxResults": 5
})

if result1["statusCode"] == 200:
    print(f"Success!")
    body = result1['body']
    print(f"Total Summaries: {body['count']}")
    print(f"User ID: {body['user_id']}")
    
    if body['chatSummaries']:
        first_summary = body['chatSummaries'][0]
        print(f"First Chat ID: {first_summary.get('chatId')}")
        print(f"First Chat Title: {first_summary.get('title')}")
        print(f"Message Count: {first_summary.get('messageCount')}")
        print(f"Last Updated: {first_summary.get('lastUpdated')}")
else:
    print(f"Error: {result1['body'].get('error')}")

# Test 2: Get Recent Chat Summaries with Custom Limit
print("\n--- Test 2: Get Recent Chat Summaries with Custom Limit ---")
result2 = handler.get_recent_chat_summaries({
    "user_id": "user-002",
    "maxResults": 3
})

if result2["statusCode"] == 200:
    print(f"Success!")
    body = result2['body']
    print(f"Total Summaries: {body['count']}")
    print(f"Requested Limit: 3")
    
    for i, summary in enumerate(body['chatSummaries']):
        print(f"  {i+1}. {summary.get('title')} - {summary.get('chatId')}")
else:
    print(f"Error: {result2['body'].get('error')}")

# Test 3: Search Chat Summaries with Keyword
print("\n--- Test 3: Search Chat Summaries with Keyword ---")
result3 = handler.search_chat_summaries({
    "user_id": "user-001",
    "searchKeyword": "insurance",
    "maxResults": 10
})

if result3["statusCode"] == 200:
    print(f"Success!")
    body = result3['body']
    print(f"Search Results: {body['count']}")
    print(f"Search Keyword: '{body['search_criteria']['search_keyword']}'")
    
    if body['searchResults']:
        for i, result in enumerate(body['searchResults']):
            print(f"  {i+1}. {result.get('title')} - Messages: {result.get('messageCount')}")
    else:
        print("  No results found for the search keyword")
else:
    print(f"Error: {result3['body'].get('error')}")

# Test 4: Search Chat Summaries without Keyword (Returns All)
print("\n--- Test 4: Search Chat Summaries without Keyword ---")
result4 = handler.search_chat_summaries({
    "user_id": "user-001",
    "searchKeyword": "",
    "maxResults": 5
})

if result4["statusCode"] == 200:
    print(f"Success!")
    body = result4['body']
    print(f"Total Results: {body['count']}")
    print(f"Search was performed without keyword (returns all chats)")
else:
    print(f"Error: {result4['body'].get('error')}")

# Test 5: Get Chat Details
print("\n--- Test 5: Get Chat Details ---")
# First get a chat ID from recent summaries to use for details test
recent_result = handler.get_recent_chat_summaries({
    "user_id": "user-001",
    "maxResults": 1
})

if recent_result["statusCode"] == 200 and recent_result['body']['chatSummaries']:
    chat_id = recent_result['body']['chatSummaries'][0]['chatId']
    
    result5 = handler.get_chat_details({
        "chatId": chat_id,
        "user_id": "user-001"
    })
    
    if result5["statusCode"] == 200:
        print(f"Success!")
        body = result5['body']
        print(f"Chat ID: {chat_id}")
        print(f"Message: {body['message']}")
        
        chat_details = body['chatDetails']
        print(f"Title: {chat_details.get('title')}")
        print(f"Session ID: {chat_details.get('sessionId')}")
        print(f"Prompt Count: {len(chat_details.get('promptIds', []))}")
        print(f"Actual Prompts Fetched: {len(body['prompts'])}")
        
        if body['prompts']:
            first_prompt = body['prompts'][0]
            print(f"First Prompt ID: {first_prompt.get('promptId')}")
            print(f"Prompt Text Preview: {first_prompt.get('promptText', '')[:50]}...")
    else:
        print(f"Error: {result5['body'].get('error')}")
else:
    print("Could not get a chat ID for details test")

# Test 6: Get Chat Details with Invalid Chat ID
print("\n--- Test 6: Get Chat Details with Invalid Chat ID ---")
result6 = handler.get_chat_details({
    "chatId": "nonexistent-chat-123",
    "user_id": "user-001"
})

if result6["statusCode"] != 200:
    print(f"Expected error: {result6['body'].get('error')}")
else:
    print("Unexpected success - test should have failed")

# Test 7: Get Chat Details - Unauthorized User
print("\n--- Test 7: Get Chat Details - Unauthorized User ---")
# First get a chat ID
recent_result = handler.get_recent_chat_summaries({
    "user_id": "user-001",
    "maxResults": 1
})

if recent_result["statusCode"] == 200 and recent_result['body']['chatSummaries']:
    chat_id = recent_result['body']['chatSummaries'][0]['chatId']
    
    # Try to access with different user
    result7 = handler.get_chat_details({
        "chatId": chat_id,
        "user_id": "user-unauthorized-999"
    })
    
    if result7["statusCode"] != 200:
        print(f"Expected authorization error: {result7['body'].get('error')}")
    else:
        print("Unexpected success - test should have failed")
else:
    print("Could not get a chat ID for authorization test")

# Test 8: Missing User ID (Error Case)
print("\n--- Test 8: Missing User ID (Error Case) ---")
result8 = handler.get_recent_chat_summaries({
    "maxResults": 5
    # Missing user_id
})

if result8["statusCode"] != 200:
    print(f"Expected validation error: {result8['body'].get('error')}")
else:
    print("Unexpected success - test should have failed")

# Test 9: Search with Complex Keyword
print("\n--- Test 9: Search with Complex Keyword ---")
result9 = handler.search_chat_summaries({
    "user_id": "user-001",
    "searchKeyword": "claim processing 2024",
    "maxResults": 15
})

if result9["statusCode"] == 200:
    print(f"Success!")
    body = result9['body']
    print(f"Found {body['count']} results for complex search")
    print(f"Search: '{body['search_criteria']['search_keyword']}'")
else:
    print(f"Error: {result9['body'].get('error')}")

# Test 10: Get Recent Summaries with Large Limit
print("\n--- Test 10: Get Recent Summaries with Large Limit ---")
result10 = handler.get_recent_chat_summaries({
    "user_id": "user-001",
    "maxResults": 50
})

if result10["statusCode"] == 200:
    print(f"Success!")
    body = result10['body']
    print(f"Retrieved {body['count']} summaries with limit 50")
    
    # Show some statistics if we have data
    if body['chatSummaries']:
        titles = [s.get('title', 'Untitled') for s in body['chatSummaries']]
        message_counts = [s.get('messageCount', 0) for s in body['chatSummaries']]
        
        print(f"Title samples: {titles[:3]}")
        print(f"Average messages per chat: {sum(message_counts)/len(message_counts):.1f}")
else:
    print(f"Error: {result10['body'].get('error')}")

# Sample Lambda Handler Test
def test_lambda_handler():
    """
    Test the Lambda handler function with different actions
    """
    print("\n" + "=" * 80)
    print("Testing Lambda Handler")
    print("=" * 80)
    
    from app.handlers.chat_summary_handler import handler as lambda_handler
    
    # Test get_recent_summaries action
    recent_event = {
        "action": "get_recent_summaries",
        "payload": {
            "user_id": "user-lambda-001",
            "maxResults": 3
        }
    }
    
    print("\n--- Lambda Test: Get Recent Summaries ---")
    result = lambda_handler(recent_event, None)
    print(f"Status Code: {result['statusCode']}")
    if result['statusCode'] == 200:
        print(f"Success: Found {result['body']['count']} summaries")
    else:
        print(f"Error: {result['body'].get('error')}")
    
    # Test search_summaries action
    search_event = {
        "action": "search_summaries",
        "payload": {
            "user_id": "user-lambda-001",
            "searchKeyword": "test",
            "maxResults": 5
        }
    }
    
    print("\n--- Lambda Test: Search Summaries ---")
    result = lambda_handler(search_event, None)
    print(f"Status Code: {result['statusCode']}")
    if result['statusCode'] == 200:
        print(f"Success: Found {result['body']['count']} search results")
    else:
        print(f"Error: {result['body'].get('error')}")
    
    # Test get_chat_details action
    details_event = {
        "action": "get_chat_details",
        "payload": {
            "user_id": "user-lambda-001",
            "chatId": "chat-test-123"
        }
    }
    
    print("\n--- Lambda Test: Get Chat Details ---")
    result = lambda_handler(details_event, None)
    print(f"Status Code: {result['statusCode']}")
    if result['statusCode'] == 200:
        print(f"Success: {result['body']['message']}")
        print(f"Prompts found: {len(result['body']['prompts'])}")
    else:
        print(f"Error: {result['body'].get('error')}")
    
    # Test unknown action
    unknown_event = {
        "action": "unknown_action",
        "payload": {}
    }
    
    print("\n--- Lambda Test: Unknown Action ---")
    result = lambda_handler(unknown_event, None)
    print(f"Status Code: {result['statusCode']}")
    print(f"Error: {result['body'].get('error')}")

# Run lambda handler tests
test_lambda_handler()

print("\n" + "=" * 80)
print("All Chat Summary Tests Completed")
print("=" * 80)

