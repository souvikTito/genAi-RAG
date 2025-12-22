"""
MedPro API Gateway Test Runner - Complete Gen AI Features Testing
Tests all core chat endpoints including all Gen AI features with proper payload structure
"""


import requests
import json
import time
import os
import uuid
from datetime import datetime


class MedProAPITester:
    def __init__(self):
        self.base_urls = {
        # For Uat env


            # 'core': 'https://qeabpubxx7-vpce-0f414c0a7147a4fb1.execute-api.us-east-2.amazonaws.com/uat/mpg-core-lambda-handler',
            # 'helper': 'https://eruhfo2714-vpce-0f414c0a7147a4fb1.execute-api.us-east-2.amazonaws.com/uat/mpg-ui-helper-lambda',
            # 'presigned': 'https://qa9tg3tjsc-vpce-0f414c0a7147a4fb1.execute-api.us-east-2.amazonaws.com/uat/mpg-s3-presigned-url',
            # 'doc_status': 'https://m7ii44bgz3-vpce-0f414c0a7147a4fb1.execute-api.us-east-2.amazonaws.com/uat/mpg-document-processing-status/docStatus',
            # 'logout': 'https://wmh7jxlksj-vpce-0f414c0a7147a4fb1.execute-api.us-east-2.amazonaws.com/uat/mpg-user-logout'
       
        # For Dev env
       
            'core': 'https://oaz4f49ujl-vpce-0df819babc1ad3907.execute-api.us-east-2.amazonaws.com/dev/mpg-core-lambda-handler',
            'helper': 'https://4zqkj3pf4e-vpce-0df819babc1ad3907.execute-api.us-east-2.amazonaws.com/dev/mpg-ui-helper-lambda',
            'presigned': 'https://6jpezq4qec-vpce-0df819babc1ad3907.execute-api.us-east-2.amazonaws.com/dev/mpg-s3-presigned-url',
            'doc_status': 'https://ak43hsioqe-vpce-0df819babc1ad3907.execute-api.us-east-2.amazonaws.com/dev/mpg-document-processing-status/docStatus',
            'logout': 'https://70rjcvtrod-vpce-0df819babc1ad3907.execute-api.us-east-2.amazonaws.com/dev/mpg-user-logout'




        }
        self.results = []
        self.session = requests.Session()
        self.delay_between_requests = 2  # 2 seconds delay between API calls
  # For Dev env      
        # # Get common IDs from environment variables with fallbacks
        # self.test_user_id = os.getenv('MEDPRO_TEST_USER_ID', '013be5f0-70a1-7086-001f-380108980f31')
        # self.test_session_id = os.getenv('MEDPRO_TEST_SESSION_ID', 'f81a8024-9f6a-4e1c-8739-5e522d5a76fa')
        # self.test_prompt_template_id = os.getenv('MEDPRO_TEST_PROMPT_TEMPLATE_ID', 'pt316997d0-5680-4c54-8671-b966fd3291f4')
        # self.test_chat_id = os.getenv('MEDPRO_TEST_CHAT_ID', 'db80c225-d07d-41f0-9efa-cb08e4a4b22a')
        # self.test_document_id = os.getenv('MEDPRO_TEST_DOCUMENT_ID', '81e5efb9-7a4f-4d72-9d93-6a0a987f55f5')
        # self.test_prompt_pk = os.getenv('MEDPRO_TEST_PROMPT_PK', "b8399202-5f56-45fd-830f-04a13cd06b8c")


  # For Dev env
        # Get common IDs from environment variables with fallbacks
        self.test_user_id = os.getenv('MEDPRO_TEST_USER_ID', 'f13b9540-20b1-7004-a3e8-0c463e6e6b0c')
        self.test_session_id = os.getenv('MEDPRO_TEST_SESSION_ID', 'f90b1fff-c902-4994-83dc-d3bf6b4df1a3')
        self.test_prompt_template_id = os.getenv('MEDPRO_TEST_PROMPT_TEMPLATE_ID', 'pt80159493-47ee-4f6b-8c41-4ce3924648d7')
        self.test_chat_id = os.getenv('MEDPRO_TEST_CHAT_ID', '1af1fbdd-98b3-40ff-b8ed-39372874b5a9')
        self.test_document_id = os.getenv('MEDPRO_TEST_DOCUMENT_ID', '12b32218-1304-4cad-bb42-e77e176f4639')
        self.test_prompt_pk = os.getenv('MEDPRO_TEST_PROMPT_PK', "3a20c3be-4373-47b6-b6df-a919c71d4818")






       
        # Setup headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MedPro-API-Tester/1.0'
        }
        self.session.headers.update(headers)
       
        print(f"Configuration Loaded:")
        print(f"  User ID: {self.test_user_id}")
        print(f"  Session ID: {self.test_session_id}")
        print(f"  Prompt Template ID: {self.test_prompt_template_id}")
        print(f"  Chat ID: {self.test_chat_id}")
        print(f"  Document ID: {self.test_document_id}")


    def get_current_timestamp(self):
        """Generate current timestamp in the format: 2025-11-22T17:11:48.538277+00:00"""
        return datetime.now().isoformat()


    def add_delay(self, seconds=2):
        """Add delay between API calls to avoid rate limiting"""
        print(f"    Waiting {seconds} seconds before next request...")
        time.sleep(seconds)


    def generate_chat_id(self):
        """Generate dynamic chat ID"""
        return str(uuid.uuid4())


    def test_endpoint(self, name, method, url, payload=None, expected_status=200):
        """Test a single API endpoint and record results"""
        test_id = str(uuid.uuid4())
       
        print(f" Testing: {name}")
        print(f"    {method} {url}")
       
        start_time = time.time()
        result = {
            'id': test_id,
            'name': name,
            'method': method,
            'url': url,
            'timestamp': self.get_current_timestamp(),
            'request_payload': payload,
            'expected_status': expected_status
        }
       
        try:
            # Make API request
            if method.upper() == 'GET':
                response = self.session.get(url, params=payload)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=payload)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=payload)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
           
            response_time = round((time.time() - start_time) * 1000, 2)
           
            # Determine test status
            status = "SUCCESS" if response.status_code == expected_status else "FAILURE"
           
            # Parse response
            response_body = self._safe_json_parse(response.text)
           
            # Extract time metrics from response if available
            lambda_time = None
            bedrock_time = None
           
            if response_body:
                try:
                    if isinstance(response_body, dict):
                        # Check for nested structure
                        if 'body' in response_body and isinstance(response_body['body'], dict):
                            if 'metadata' in response_body['body']:
                                metadata = response_body['body']['metadata']
                                if isinstance(metadata, dict):
                                    lambda_time = metadata.get('response_time')
                                    bedrock_time = metadata.get('bedrock_response_time')
                        # Check direct metadata
                        elif 'metadata' in response_body:
                            metadata = response_body['metadata']
                            if isinstance(metadata, dict):
                                lambda_time = metadata.get('response_time')
                                bedrock_time = metadata.get('bedrock_response_time')
                except Exception:
                    pass
           
            # Update result with time metrics
            result.update({
                'status': status,
                'http_status': response.status_code,
                'response_time_ms': response_time,
                'response_headers': dict(response.headers),
                'response_body': response_body,
                'error': None,
                'lambda_time': lambda_time,
                'bedrock_time': bedrock_time
            })
           
            # CHANGED: Updated console output to show seconds instead of milliseconds
            print(f"    {status} (HTTP {response.status_code}) - {response_time/1000:.2f}s")
           
        except requests.exceptions.Timeout:
            response_time = round((time.time() - start_time) * 1000, 2)
            result.update({
                'status': "FAILURE",
                'http_status': 408,
                'response_time_ms': response_time,
                'response_headers': {},
                'response_body': None,
                'error': "Request timeout",
                'lambda_time': None,
                'bedrock_time': None
            })
            print(f"    FAILURE - Timeout")
           
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            result.update({
                'status': "FAILURE",
                'http_status': 0,
                'response_time_ms': response_time,
                'response_headers': {},
                'response_body': None,
                'error': str(e),
                'lambda_time': None,
                'bedrock_time': None
            })
            print(f"    FAILURE - Error: {str(e)}")
       
        print("   " + "-" * 40)
        self.results.append(result)
       
        # Add delay after each API call
        self.add_delay(self.delay_between_requests)
       
        return result


    def _safe_json_parse(self, text):
        """Safely parse JSON response"""
        try:
            return json.loads(text)
        except:
            return text


    def run_all_tests(self):
        """Run tests for all endpoints including all Gen AI features"""
        print(" Starting MedPro API Tests - All Gen AI Features")
        print("=" * 60)
        print(f" Testing all endpoints with {self.delay_between_requests}s delays")
        print("=" * 60)
       
        # Store chat IDs for later use in chat history tests
        created_chat_ids = []
       
        # Test Suite 1: Basic Chat Operations
        print("\n1. BASIC CHAT OPERATIONS TESTS")
        print("-" * 40)
       
        # Plain Chat
        plain_chat_id = self.generate_chat_id()
        created_chat_ids.append(plain_chat_id)
       
        plain_chat_result = self.test_endpoint(
            name="Plain Chat",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Which is the highest mountain in the world?",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": plain_chat_id
            },
            expected_status=200
        )
       
        # Test Suite 2: All Gen AI Features
        print("\n2. ALL GEN AI FEATURES TESTS")
        print("-" * 40)
       
        # Default Feature
        default_chat_id = self.generate_chat_id()
        created_chat_ids.append(default_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Default Feature",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Explain the process of photosynthesis in plants",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": default_chat_id,
                "genai_feature": "default",
                "genAiParams": {"style": "educational"}
            },
            expected_status=200
        )
       
        # QnA Feature
        qna_chat_id = self.generate_chat_id()
        created_chat_ids.append(qna_chat_id)
       
        self.test_endpoint(
            name="Gen AI - QnA Feature",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "What are the benefits of regular exercise for mental health?",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": qna_chat_id,
                "genai_feature": "qna"
            },
            expected_status=200
        )
       
        # Document Comparison Feature
        doc_comp_chat_id = self.generate_chat_id()
        created_chat_ids.append(doc_comp_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Document Comparison",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Compare these two insurance policies and highlight key differences",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": doc_comp_chat_id,
                "genai_feature": "docComparison",
                "genAiParams": {"style": "detailed"}
            },
            expected_status=200
        )
       
        # Search Feature
        search_chat_id = self.generate_chat_id()
        created_chat_ids.append(search_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Search",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Find information about machine learning algorithms and their applications",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": search_chat_id,
                "genai_feature": "search",
                "genAiParams": {"style": "comprehensive"}
            },
            expected_status=200
        )
       
        # Code Review Feature
        code_review_chat_id = self.generate_chat_id()
        created_chat_ids.append(code_review_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Code Review",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Review this Python function for efficiency and best practices:\n\ndef calculate_average(numbers):\n    total = 0\n    for num in numbers:\n        total += num\n    return total / len(numbers)",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": code_review_chat_id,
                "genai_feature": "codeReview",
                "genAiParams": {"style": "technical"}
            },
            expected_status=200
        )
       
        # Content Generation Feature
        content_gen_chat_id = self.generate_chat_id()
        created_chat_ids.append(content_gen_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Content Generation",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Write a blog post about artificial intelligence in healthcare",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": content_gen_chat_id,
                "genai_feature": "contentGeneration",
                "genAiParams": {"style": "professional"}
            },
            expected_status=200
        )
       
        # Text Summarization Feature
        text_summary_chat_id = self.generate_chat_id()
        created_chat_ids.append(text_summary_chat_id)
       
        self.test_endpoint(
            name="Gen AI - Text Summarization",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Summarize this long article about climate change and its impact on global ecosystems",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": text_summary_chat_id,
                "genai_feature": "textSummarisation",
                "genAiParams": {"style": "concise"}
            },
            expected_status=200
        )
       
        # Chat with Document Upload
        doc_chat_id = self.generate_chat_id()
        created_chat_ids.append(doc_chat_id)
       
        self.test_endpoint(
            name="Chat with Document Upload",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Please summarize the document",
                "session_PK": self.test_session_id,
                "user_PK": "newUser",
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": doc_chat_id,
                "document_PK": ["test"],
                "fileNames": ["test_McDonalds.pdf"]
            },
            expected_status=200
        )
       
        # Chat from Prompt Template
        prompt_template_chat_id = self.generate_chat_id()
        created_chat_ids.append(prompt_template_chat_id)
       
        self.test_endpoint(
            name="Chat from Prompt Template",
            method="POST",
            url=f"{self.base_urls['core']}/chat",
            payload={
                "userQuery": "Which is the highest mountain in the world?",
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "auditCreateDateTime": self.get_current_timestamp(),
                "chat_PK": prompt_template_chat_id,
                "promptTemplate_PK": self.test_prompt_template_id
            },
            expected_status=200
        )
       
        # Test Suite 3: Feedback
        print("\n3. FEEDBACK TESTS")
        print("-" * 40)
       
        self.test_endpoint(
            name="Submit Feedback",
            method="POST",
            url=f"{self.base_urls['core']}/feedback",
            payload={
                "session_PK": self.test_session_id,
                "user_PK": self.test_user_id,
                "chat_PK": plain_chat_id,  # Use existing chat ID
                "prompt_PK": self.test_prompt_pk,
                "isLiked": True,
                "auditCreateDateTime": self.get_current_timestamp()
            },
            expected_status=200
        )
       
        # Test Suite 4: Prompt Template Management
        print("\n4. PROMPT TEMPLATE MANAGEMENT TESTS")
        print("-" * 40)
       
        # Create Prompt
        self.test_endpoint(
            name="Create Prompt Template",
            method="POST",
            url=f"{self.base_urls['core']}/prompt-template",
            payload={
                "action": "create",
                "payload": {
                    "user_PK": self.test_user_id,
                    "role": "USER",
                    "category": "Actuary",
                    "promptDescription": "Write a message for someone starting a new job.",
                    "promptTitle": "Finding Job"
                }
            },
            expected_status=200
        )
       
        # Update Prompt
        self.test_endpoint(
            name="Update Prompt Template",
            method="POST",
            url=f"{self.base_urls['core']}/prompt-template",
            payload={
                "action": "update",
                "payload": {
                    "promptTemplate_PK": self.test_prompt_template_id,
                    "user_PK": self.test_user_id,
                    "promptDescription": "Updated version of the prompt with clearer structure and motivational tone.",
                    "category": "Personal",
                    "promptTitle": "Encouragement for New Job Role"
                }
            },
            expected_status=200
        )
       
        # List Prompt templates by filters
        self.test_endpoint(
            name="List Prompt Templates",
            method="POST",
            url=f"{self.base_urls['core']}/prompt-template",
            payload={
                "action": "list",
                "payload": {
                    "user_PK": self.test_user_id,
                    "category": ["Default"],
                    "options": ["User"],
                    "sortBy": "auditLastUpdateDateTime",
                    "sortOrder": "desc",
                    "limit": 10,
                    "pageIndex": 1
                }
            },
            expected_status=200
        )
       
        # List Categories
        self.test_endpoint(
            name="List Categories",
            method="POST",
            url=f"{self.base_urls['core']}/prompt-template",
            payload={
                "action": "list_categories",
                "payload": {
                    "user_PK": self.test_user_id
                }
            },
            expected_status=200
        )
       
        # Prompt Search
        self.test_endpoint(
            name="Search Prompts by Tags",
            method="POST",
            url=f"{self.base_urls['core']}/prompt-template",
            payload={
                "action": "search_by_tags",
                "payload": {
                    "user_PK": self.test_user_id,
                    "tags": ["career", "new"],
                    "category": "Motivation"
                }
            },
            expected_status=200
        )
       
        # Test Suite 5: Chat History Summary
        print("\n5. CHAT HISTORY SUMMARY TESTS")
        print("-" * 40)
       
        # Get Chat History Summary
        self.test_endpoint(
            name="Get Recent Chat Summaries",
            method="POST",
            url=f"{self.base_urls['core']}/chat-history-summary",
            payload={
                "action": "get_recent_summaries",
                "payload": {
                    "user_PK": self.test_user_id,
                    "pageIndex": 1,
                    "pageSize": 10
                }
            },
            expected_status=200
        )
       
        # Search Chat by Tags
        self.test_endpoint(
            name="Search Chat Summaries",
            method="POST",
            url=f"{self.base_urls['core']}/chat-history-summary",
            payload={
                "action": "search_summaries",
                "payload": {
                    "user_PK": "testUserID",
                    "searchKeyword": "User"
                }
            },
            expected_status=200
        )
       
        # Get Chat Details by chatId - Use a real chatId we created
        if created_chat_ids:
            real_chat_id = created_chat_ids[0]
            self.test_endpoint(
                name="Get Chat Details",
                method="POST",
                url=f"{self.base_urls['core']}/chat-history-summary",
                payload={
                    "action": "get_chat_details",
                    "payload": {
                        "chat_PK": real_chat_id,
                        "user_PK": self.test_user_id
                    }
                },
                expected_status=200
            )
        else:
            # Fallback to environment variable
            self.test_endpoint(
                name="Get Chat Details (Fallback)",
                method="POST",
                url=f"{self.base_urls['core']}/chat-history-summary",
                payload={
                    "action": "get_chat_details",
                    "payload": {
                        "chat_PK": self.test_chat_id,
                        "user_PK": self.test_user_id
                    }
                },
                expected_status=200
            )
       
        # Test Suite 6: Helper Functions
        print("\n6. HELPER FUNCTIONS TESTS")
        print("-" * 40)
       
        # Submit Help
        self.test_endpoint(
            name="Submit Help Request",
            method="POST",
            url=self.base_urls['helper'],
            payload={
                "action": "submitHelp",
                "payload": {
                    "user_PK": "user123",
                    "session_PK": "session456",
                    "description": "User requested help with login issue"
                }
            },
            expected_status=200
        )
       
        # Send Notification
        self.test_endpoint(
            name="Send Notification",
            method="POST",
            url=self.base_urls['helper'],
            payload={
                "action": "sendNotification"
            },
            expected_status=200
        )
       
        # User Logout
        self.test_endpoint(
            name="User Logout",
            method="POST",
            url=self.base_urls['logout'],
            payload={
                "user_PK": self.test_user_id,
                "session_PK": self.test_session_id,
                "status": "LOGOUT"
            },
            expected_status=200
        )
       
        # Test Suite 7: S3 Presigned URL
        print("\n7. S3 PRESIGNED URL TESTS")
        print("-" * 40)
       
        self.test_endpoint(
            name="Get S3 Presigned URL",
            method="POST",
            url=self.base_urls['presigned'],
            payload={
                "user_PK": "test_user",
                "filename": "new.pdf"
            },
            expected_status=200
        )
       
        # Test Suite 8: Document Processing Status
        print("\n8. DOCUMENT PROCESSING STATUS TESTS")
        print("-" * 40)
       
        self.test_endpoint(
            name="Get Document Status",
            method="POST",
            url=self.base_urls['doc_status'],
            payload={
                "document_PK": self.test_document_id
            },
            expected_status=200
        )
       
        print("=" * 60)
        print(" All endpoint tests completed!")
        return self.results


    def generate_html_report(self, filename="medpro_api_test_report.html"):
        """Generate beautiful HTML report with all test results"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['status'] == 'SUCCESS')
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
       
        # NEW: Calculate average times
        api_times = [r['response_time_ms'] / 1000 for r in self.results]
        avg_api_time = sum(api_times) / len(api_times) if api_times else 0
       
        # Calculate average Lambda time (only for tests that have it)
        lambda_times = [r['lambda_time'] for r in self.results if r['lambda_time'] is not None]
        avg_lambda_time = sum(lambda_times) / len(lambda_times) if lambda_times else None
       
        # Calculate average Bedrock time (only for tests that have it)
        bedrock_times = [r['bedrock_time'] for r in self.results if r['bedrock_time'] is not None]
        avg_bedrock_time = sum(bedrock_times) / len(bedrock_times) if bedrock_times else None
       
        # Count tests with Lambda and Bedrock times
        lambda_tests_count = len(lambda_times)
        bedrock_tests_count = len(bedrock_times)
       
        # Group results by category for better organization
        categories = {
            "Basic Chat": [],
            "Gen AI Features": [],
            "Feedback": [],
            "Prompt Templates": [],
            "Chat History": [],
            "Helper Functions": [],
            "S3 & Documents": []
        }
       
        for result in self.results:
            name = result['name']
            if "Gen AI" in name:
                categories["Gen AI Features"].append(result)
            elif "Feedback" in name:
                categories["Feedback"].append(result)
            elif "Prompt" in name:
                categories["Prompt Templates"].append(result)
            elif "Chat" in name and ("Summary" in name or "History" in name):
                categories["Chat History"].append(result)
            elif "Help" in name or "Notification" in name or "Logout" in name:
                categories["Helper Functions"].append(result)
            elif "S3" in name or "Document" in name:
                categories["S3 & Documents"].append(result)
            else:
                categories["Basic Chat"].append(result)
       
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MedPro API Test Report - All Gen AI Features</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f8f9fa; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; text-align: center; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .summary-card {{ background: white; padding: 1.5rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .summary-card.total {{ border-top: 4px solid #3498db; }}
        .summary-card.passed {{ border-top: 4px solid #2ecc71; }}
        .summary-card.failed {{ border-top: 4px solid #e74c3c; }}
        .summary-card.rate {{ border-top: 4px solid #f39c12; }}
        .category-section {{ margin-bottom: 2rem; }}
        .category-header {{ background: #2c3e50; color: white; padding: 1rem; border-radius: 8px 8px 0 0; margin-bottom: 0; }}
        .test-result {{ background: white; margin-bottom: 3px; border-radius: 0; box-shadow: none; overflow: hidden; border-left: 5px solid #ccc; }}
        .test-success {{ border-left-color: #2ecc71; }}
        .test-failure {{ border-left-color: #e74c3c; }}
        .test-header {{ padding: 1rem; display: flex; justify-content: space-between; align-items: center; cursor: pointer; background: white; }}
        .test-name {{ font-weight: bold; font-size: 1rem; }}
        .test-status {{ padding: 0.3rem 0.8rem; border-radius: 20px; color: white; font-size: 0.8rem; font-weight: bold; }}
        .status-success {{ background: #2ecc71; }}
        .status-failure {{ background: #e74c3c; }}
        .test-details {{ padding: 1rem; background: #f8f9fa; border-top: 1px solid #eee; display: none; }}
        .test-meta {{ display: flex; gap: 1rem; font-size: 0.8rem; color: #666; margin-top: 0.3rem; flex-wrap: wrap; }}
        .code-block {{ background: #2d3748; color: #e2e8f0; padding: 1rem; border-radius: 5px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 0.75rem; margin: 0.5rem 0; max-height: 300px; overflow-y: auto; }}
        .toggle-btn {{ background: #3498db; color: white; border: none; padding: 0.3rem 0.8rem; border-radius: 3px; cursor: pointer; margin-top: 0.5rem; font-size: 0.8rem; }}
        .response-time {{ color: #666; }}
        .url-display {{ font-size: 0.75rem; color: #555; word-break: break-all; margin-top: 0.3rem; }}
        .feature-badge {{ background: #9b59b6; color: white; padding: 0.2rem 0.5rem; border-radius: 10px; font-size: 0.7rem; margin-left: 0.5rem; }}
        .config-info {{ background: #e8f4fd; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #3498db; }}
        .test-gap {{ margin-bottom: 3px; }}
        /* CHANGED: Removed colored badges and made them simple text spans */
        .time-badge {{ background: #f0f0f0; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; margin-left: 0.3rem; border: 1px solid #ddd; }}
        /* NEW: Style for average time metrics */
        .avg-time {{ display: inline-block; background: #f8f9fa; padding: 0.3rem 0.6rem; border-radius: 4px; border: 1px solid #dee2e6; margin-left: 0.3rem; font-size: 0.85rem; }}
        .avg-time-label {{ font-weight: bold; color: #495057; }}
        .avg-time-value {{ font-weight: bold; color: #212529; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MedPro API Test Report - All Gen AI Features</h1>
            <p>Comprehensive Testing of All API Endpoints Including All 7 Gen AI Features</p>
            <p><strong>Generated:</strong> {self.get_current_timestamp()} | <strong>Total Endpoints:</strong> {total_tests}</p>
        </div>
       
        <div class="config-info">
            <h3>Test Configuration</h3>
            <p><strong>Delay Between Requests:</strong> {self.delay_between_requests} seconds</p>
            <p><strong>Request Timeout:</strong> No timeout set</p>
            <!-- NEW: Added average time metrics -->
            <p><strong>Total Testing Time:</strong> Approximately {total_tests * (self.delay_between_requests + 1)} seconds</p>
            <p><strong>Average API Time:</strong> <span class="avg-time"><span class="avg-time-label">API Time:</span> <span class="avg-time-value">{avg_api_time:.2f}s</span></span> (across {total_tests} tests)</p>
            {f'<p><strong>Average Lambda Time:</strong> <span class="avg-time"><span class="avg-time-label">Lambda Time:</span> <span class="avg-time-value">{avg_lambda_time:.2f}s</span></span> (across {lambda_tests_count} tests)</p>' if avg_lambda_time is not None else '<p><strong>Average Lambda Time:</strong> Not available (no Lambda time data)</p>'}
            {f'<p><strong>Average Bedrock Time:</strong> <span class="avg-time"><span class="avg-time-label">Bedrock Time:</span> <span class="avg-time-value">{avg_bedrock_time:.2f}s</span></span> (across {bedrock_tests_count} tests)</p>' if avg_bedrock_time is not None else '<p><strong>Average Bedrock Time:</strong> Not available (no Bedrock time data)</p>'}
            <p><strong>Timestamp Format:</strong> ISO 8601 with microseconds {self.get_current_timestamp()}</p>
        </div>
       
        <div class="summary">
            <div class="summary-card total">
                <h3>Total Tests</h3>
                <div style="font-size: 2rem; font-weight: bold;">{total_tests}</div>
            </div>
            <div class="summary-card passed">
                <h3>Passed</h3>
                <div style="font-size: 2rem; font-weight: bold;">{passed_tests}</div>
            </div>
            <div class="summary-card failed">
                <h3>Failed</h3>
                <div style="font-size: 2rem; font-weight: bold;">{failed_tests}</div>
            </div>
            <div class="summary-card rate">
                <h3>Success Rate</h3>
                <div style="font-size: 2rem; font-weight: bold;">{success_rate:.1f}%</div>
            </div>
        </div>
       
        <h2>Detailed Test Results by Category</h2>
"""
       
        # Generate HTML for each category
        for category_name, category_results in categories.items():
            if category_results:
                html += f"""
        <div class="category-section">
            <h3 class="category-header">{category_name} ({len(category_results)} tests)</h3>
"""
               
                for i, result in enumerate(category_results):
                    status_class = 'test-success' if result['status'] == 'SUCCESS' else 'test-failure'
                    status_badge_class = 'status-success' if result['status'] == 'SUCCESS' else 'status-failure'
                   
                    # Convert response time from ms to seconds
                    total_time_seconds = result['response_time_ms'] / 1000
                   
                    # Extract feature type for badge
                    feature_badge = ""
                    if "Gen AI -" in result['name']:
                        feature_name = result['name'].replace("Gen AI - ", "")
                        feature_badge = f'<span class="feature-badge">{feature_name}</span>'
                   
                    # CHANGED: Extract and rename time metrics from response body
                    lambda_time_badge = ""
                    bedrock_time_badge = ""
                   
                    if result['lambda_time'] is not None:
                        lambda_time_badge = f'<span class="time-badge" title="Lambda Processing Time">Lambda Time: {result["lambda_time"]}s</span>'
                   
                    if result['bedrock_time'] is not None:
                        bedrock_time_badge = f'<span class="time-badge" title="Bedrock Model Processing Time">Bedrock Time: {result["bedrock_time"]}s</span>'
                   
                    # Format payloads for display
                    request_json = json.dumps(result['request_payload'], indent=2) if result['request_payload'] else 'No payload'
                    response_json = result['response_body']
                    if isinstance(response_json, (dict, list)):
                        response_json = json.dumps(response_json, indent=2)
                   
                    # CHANGED: Updated time display with new naming
                    html += f"""
            <div class="test-result {status_class} test-gap">
                <div class="test-header" onclick="toggleDetails('{result['id']}')">
                    <div style="flex: 1;">
                        <div class="test-name">{result['name']}{feature_badge}</div>
                        <div class="test-meta">
                            <span><strong>Method:</strong> {result['method']}</span>
                            <span><strong>Status:</strong> {result['http_status']} (Expected: {result['expected_status']})</span>
                            <!-- CHANGED: Total Time renamed to API Time -->
                            <span class="response-time"><strong>API Time:</strong> {total_time_seconds:.2f}s {lambda_time_badge}{bedrock_time_badge}</span>
                            <span><strong>Timestamp:</strong> {result['timestamp']}</span>
                        </div>
                        <div class="url-display"><strong>URL:</strong> {result['url']}</div>
                    </div>
                    <span class="test-status {status_badge_class}">{result['status']}</span>
                </div>
                <div id="details-{result['id']}" class="test-details">
                    <div><strong>Request Payload:</strong></div>
                    <div class="code-block">{request_json}</div>
                   
                    <div><strong>Response Body:</strong></div>
                    <div class="code-block">{response_json}</div>
                   
                    {f'<div><strong>Error:</strong></div><div class="code-block">{result["error"]}</div>' if result['error'] else ''}
                   
                    <button class="toggle-btn" onclick="toggleDetails('{result['id']}')">Toggle Details</button>
                </div>
            </div>
"""


                html += "        </div>\n"


        html += """
    </div>
   
    <script>
        function toggleDetails(id) {
            const element = document.getElementById('details-' + id);
            element.style.display = element.style.display === 'block' ? 'none' : 'block';
        }
       
        // Auto-expand failed tests
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.test-failure .test-header').forEach(header => {
                header.click();
            });
        });
    </script>
</body>
</html>
"""
       
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
       
        print(f"HTML report generated: {filename}")
        return filename


    def print_summary(self):
        """Print console summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'SUCCESS')
       
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"Failed: {total-passed}/{total} ({(total-passed)/total*100:.1f}%)")
        print(f"Total Tests: {total}")
       
        # Calculate total testing time
        total_testing_time = sum(r['response_time_ms'] for r in self.results) / 1000
        total_delay_time = total * self.delay_between_requests
        total_elapsed_time = total_testing_time + total_delay_time
       
        print(f"Total Testing Time: {total_elapsed_time:.1f}s (API calls: {total_testing_time:.1f}s + Delays: {total_delay_time}s)")
       
        # NEW: Print average times in console
        api_times = [r['response_time_ms'] / 1000 for r in self.results]
        avg_api_time = sum(api_times) / len(api_times) if api_times else 0
       
        lambda_times = [r['lambda_time'] for r in self.results if r['lambda_time'] is not None]
        avg_lambda_time = sum(lambda_times) / len(lambda_times) if lambda_times else None
       
        bedrock_times = [r['bedrock_time'] for r in self.results if r['bedrock_time'] is not None]
        avg_bedrock_time = sum(bedrock_times) / len(bedrock_times) if bedrock_times else None
       
        print(f"\nAverage Time Metrics:")
        print(f"  • Average API Time: {avg_api_time:.2f}s (across {total} tests)")
        if avg_lambda_time is not None:
            print(f"  • Average Lambda Time: {avg_lambda_time:.2f}s (across {len(lambda_times)} tests)")
        else:
            print(f"  • Average Lambda Time: Not available")
       
        if avg_bedrock_time is not None:
            print(f"  • Average Bedrock Time: {avg_bedrock_time:.2f}s (across {len(bedrock_times)} tests)")
        else:
            print(f"  • Average Bedrock Time: Not available")
       
        print(f"Timestamp Format: ISO 8601 with microseconds")
       
        # Show failed tests
        failures = [r for r in self.results if r['status'] == 'FAILURE']
        if failures:
            print(f"\nFailed Tests:")
            for fail in failures:
                error_msg = f" - {fail['error']}" if fail['error'] else ""
                print(f"  • {fail['name']} (HTTP {fail['http_status']}){error_msg}")


def main():
    """Main execution function"""
    print("MedPro API Gateway Test Runner - All Gen AI Features")
    print("=" * 60)
    print("Testing all endpoints including all 7 Gen AI features:")
    print("  • default, qna, docComparison, search, codeReview, contentGeneration, textSummarisation")
    print("  • JSON output format with HTML formatting")
    print("  • Environment variable configuration")
    print("  • ISO 8601 timestamp format with microseconds")
    print("  • 2-second delay between each API call")
    print("=" * 60)
   
    # Initialize and run tests
    tester = MedProAPITester()
    results = tester.run_all_tests()
   
    # Generate reports
    html_report = tester.generate_html_report()
    tester.print_summary()
   
    # Save raw results
    with open('medpro_api_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
   
    print(f"\nReports Generated:")
    print(f"  • HTML Report: {html_report}")
    print(f"  • Raw Data: medpro_api_test_results.json")
    print(f"\nOpen {html_report} in your browser to view the comprehensive report!")


if __name__ == "__main__":
    main()





