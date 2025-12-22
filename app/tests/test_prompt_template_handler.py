"""
Test Prompt Template Handler - the main entry point for prompt template CRUD operations.
"""

from app.handlers.prompt_template_handler import PromptTemplateHandler
import json

print("=" * 80)
print("Testing PromptTemplateHandler")
print("=" * 80)

# Initialize handler
handler = PromptTemplateHandler()

# Test 1: Create Prompt Template
print("\n--- Test 1: Create Prompt Template ---")
result1 = handler.create_prompt_template({
    "user_id": "user-001",
    "role": "ADMIN",
    "category": "Claims",
    "promptTitle": "Claims Processing Template",
    "promptDescription": "This is a template for processing insurance claims efficiently.",
    "global": "true"
})

if result1["statusCode"] == 200:
    print(f"Success!")
    print(f"Prompt Template ID: {result1['body']['promptTemplateId']}")
    print(f"Global: {result1['body']['global']}")
    print(f"Message: {result1['body']['message']}")
else:
    print(f"Error: {result1['body'].get('error')}")

# Test 2: Create User-Specific Template
print("\n--- Test 2: Create User-Specific Template ---")
result2 = handler.create_prompt_template({
    "user_id": "user-002",
    "role": "USER",
    "category": "Compliance",
    "promptTitle": "Compliance Check Template",
    "promptDescription": "Template for compliance verification checks.",
    "global": "false"
})

if result2["statusCode"] == 200:
    print(f"Success!")
    print(f"Prompt Template ID: {result2['body']['promptTemplateId']}")
    print(f"Global: {result2['body']['global']}")
    print(f"Message: {result2['body']['message']}")
else:
    print(f"Error: {result2['body'].get('error')}")

# Test 3: Get Prompt Template
print("\n--- Test 3: Get Prompt Template ---")
if result1["statusCode"] == 200:
    template_id = result1['body']['promptTemplateId']
    result3 = handler.get_prompt_template({
        "promptTemplateId": template_id,
        "user_id": "user-001"
    })
    
    if result3["statusCode"] == 200:
        print(f"Success!")
        template = result3['body']['template']
        print(f"Title: {template.get('title')}")
        print(f"Category: {template.get('category')}")
        print(f"Content: {template.get('content')[:100]}...")
        print(f"Versions: {len(template.get('versions', []))}")
    else:
        print(f"Error: {result3['body'].get('error')}")

# Test 4: Update Prompt Template
print("\n--- Test 4: Update Prompt Template ---")
if result1["statusCode"] == 200:
    template_id = result1['body']['promptTemplateId']
    result4 = handler.update_prompt_template({
        "promptTemplateId": template_id,
        "user_id": "user-001",
        "promptDescription": "Updated template for processing insurance claims with enhanced efficiency.",
        "category": "Claims Processing",
        "promptTitle": "Enhanced Claims Processing Template"
    })
    
    if result4["statusCode"] == 200:
        print(f"Success!")
        print(f"Version Number: {result4['body']['versionNumber']}")
        print(f"Message: {result4['body']['message']}")
    else:
        print(f"Error: {result4['body'].get('error')}")

# Test 5: List Prompt Templates - All
print("\n--- Test 5: List All Prompt Templates ---")
result5 = handler.list_prompt_templates({
    "user_id": "user-001",
    "options": ["All"],
    "categories": ["Claims", "Compliance"],
    "sortBy": "updatedAt",
    "sortOrder": "desc",
    "limit": 50
})

if result5["statusCode"] == 200:
    print(f"Success!")
    body = result5['body']
    print(f"Total Templates: {body['count']}")
    print(f"Global Templates: {body['global_count']}")
    print(f"User Templates: {body['user_count']}")
    print(f"Message: {body['message']}")
    
    if body['templates']:
        print(f"First template title: {body['templates'][0].get('title')}")
        print(f"First template category: {body['templates'][0].get('category')}")
else:
    print(f"Error: {result5['body'].get('error')}")

# Test 6: List Global Templates Only
print("\n--- Test 6: List Global Templates Only ---")
result6 = handler.list_prompt_templates({
    "user_id": "user-001",
    "options": ["Global"],
    "categories": ["Claims"],
    "sortBy": "title",
    "sortOrder": "asc",
    "limit": 10
})

if result6["statusCode"] == 200:
    print(f"Success!")
    body = result6['body']
    print(f"Total Templates: {body['count']}")
    print(f"Message: {body['message']}")
else:
    print(f"Error: {result6['body'].get('error')}")

# Test 7: List User Templates Only
print("\n--- Test 7: List User Templates Only ---")
result7 = handler.list_prompt_templates({
    "user_id": "user-002",
    "options": ["User"],
    "categories": ["Compliance"],
    "sortBy": "createdAt",
    "sortOrder": "desc",
    "limit": 10
})

if result7["statusCode"] == 200:
    print(f"Success!")
    body = result7['body']
    print(f"Total Templates: {body['count']}")
    print(f"Message: {body['message']}")
else:
    print(f"Error: {result7['body'].get('error')}")

# Test 8: List All Categories
print("\n--- Test 8: List All Categories ---")
result8 = handler.list_all_categories({
    "user_id": "user-001"
})

if result8["statusCode"] == 200:
    print(f"Success!")
    body = result8['body']
    print(f"Categories: {body['categories']}")
    print(f"Count: {body['count']}")
else:
    print(f"Error: {result8['body'].get('error')}")

# Test 9: Search Templates by Tags
print("\n--- Test 9: Search Templates by Tags ---")
result9 = handler.search_templates_by_tags({
    "user_id": "user-001",
    "tags": ["insurance", "claims"],
    "category": "Claims"
})

if result9["statusCode"] == 200:
    print(f"Success!")
    body = result9['body']
    print(f"Found {body['count']} templates matching tags: {body['search_tags']}")
    if body['templates']:
        print(f"First matching template: {body['templates'][0].get('title')}")
else:
    print(f"Error: {result9['body'].get('error')}")

# Test 10: Invalid Create (Missing Required Fields)
print("\n--- Test 10: Invalid Create (Missing Required Fields) ---")
result10 = handler.create_prompt_template({
    "user_id": "user-001",
    "category": "Claims"
    # Missing promptTitle and promptDescription
})

if result10["statusCode"] != 200:
    print(f"Expected error: {result10['body'].get('error')}")
else:
    print("Unexpected success - test should have failed")

# Test 11: Non-Admin Creating Global Template
print("\n--- Test 11: Non-Admin Creating Global Template ---")
result11 = handler.create_prompt_template({
    "user_id": "user-002",
    "role": "USER",  # Non-admin role
    "category": "Claims",
    "promptTitle": "Unauthorized Global Template",
    "promptDescription": "This should fail for non-admin users.",
    "global": "true"
})

if result11["statusCode"] != 200:
    print(f"Expected permission error: {result11['body'].get('error')}")
else:
    print("Unexpected success - test should have failed")

# Test 12: Get Non-Existent Template
print("\n--- Test 12: Get Non-Existent Template ---")
result12 = handler.get_prompt_template({
    "promptTemplateId": "pt-nonexistent-123",
    "user_id": "user-001"
})

if result12["statusCode"] != 200:
    print(f"Expected not found: {result12['body'].get('error')}")
else:
    print("Unexpected success - test should have failed")

# Sample Lambda Handler Test
def test_lambda_handler():
    """
    Test the Lambda handler function with different actions
    """
    print("\n" + "=" * 80)
    print("Testing Lambda Handler")
    print("=" * 80)
    
    from app.handlers.prompt_template_handler import handler as lambda_handler
    
    # Test create action
    create_event = {
        "action": "create",
        "payload": {
            "user_id": "user-lambda-001",
            "role": "ADMIN",
            "category": "Testing",
            "promptTitle": "Lambda Created Template",
            "promptDescription": "Template created via Lambda handler test.",
            "global": "false"
        }
    }
    
    print("\n--- Lambda Test: Create Action ---")
    result = lambda_handler(create_event, None)
    print(f"Status Code: {result['statusCode']}")
    if result['statusCode'] == 200:
        print(f"Success: {result['body']['message']}")
    else:
        print(f"Error: {result['body'].get('error')}")
    
    # Test list action
    list_event = {
        "action": "list",
        "payload": {
            "user_id": "user-lambda-001",
            "options": ["All"],
            "limit": 5
        }
    }
    
    print("\n--- Lambda Test: List Action ---")
    result = lambda_handler(list_event, None)
    print(f"Status Code: {result['statusCode']}")
    if result['statusCode'] == 200:
        print(f"Found {result['body']['count']} templates")
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
print("All Tests Completed")
print("=" * 80)
