"""
Test Document Ingestion Lambda
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

try:
    from scripts.doc_ingestion_lambda import doc_handler
    print(" Successfully imported doc_handler")
except ImportError as e:
    print(f" Import error: {e}")
    sys.exit(1)

# Mock context class for Lambda
class MockContext:
    def __init__(self):
        self.function_name = "doc-ingestion-lambda"
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:doc-ingestion-lambda"
        self.aws_request_id = "test-request-id-12345"

def test_doc_handler_success():
    """Test successful document handler execution"""
    print("\n--- Test: Successful Document Handler ---")
    
    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "mpg-dev-raw-documents"
                    },
                    "object": {
                        "key": "user-001/doc-12345/sample.pdf"
                    }
                }
            }
        ]
    }

    with patch('scripts.doc_ingestion_lambda.ingestion_handler') as mock_ingestion, \
         patch('scripts.doc_ingestion_lambda.configure_logger') as mock_logger, \
         patch('scripts.doc_ingestion_lambda.s3') as mock_s3, \
         patch('scripts.doc_ingestion_lambda.os.path.exists') as mock_exists, \
         patch('scripts.doc_ingestion_lambda.parse_s3_key') as mock_parse_s3, \
         patch('scripts.doc_ingestion_lambda.get_latest_session_for_user') as mock_get_session, \
         patch('scripts.doc_ingestion_lambda.logger_context') as mock_logger_context:

        # Mock dependencies
        mock_parse_s3.return_value = ("user-001", "doc-12345", "sample.pdf")
        mock_get_session.return_value = "session-12345"
        
        mock_ingestion.doc_ingestion.return_value = {
            "statusCode": 200,
            "body": {"preprocessing_complete": True}
        }
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_logger_instance.handlers = [MagicMock()]
        
        mock_exists.return_value = True
        
        context = MockContext()
        
        result = doc_handler(mock_event, context)
        
        assert result['statusCode'] == 200
        assert result['body']['preprocessing_complete'] == True
        
        print(" Test passed: Document handler executed successfully")

def test_doc_handler_ingestion_failure():
    """Test document handler when ingestion fails"""
    print("\n--- Test: Ingestion Handler Failure ---")
    
    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "mpg-dev-raw-documents"
                    },
                    "object": {
                        "key": "user-001/doc-99999/corrupted.pdf"
                    }
                }
            }
        ]
    }

    with patch('scripts.doc_ingestion_lambda.ingestion_handler') as mock_ingestion, \
         patch('scripts.doc_ingestion_lambda.configure_logger') as mock_logger, \
         patch('scripts.doc_ingestion_lambda.parse_s3_key') as mock_parse_s3:

        mock_parse_s3.return_value = ("user-001", "doc-99999", "corrupted.pdf")
        
        # Mock ingestion failure
        mock_ingestion.doc_ingestion.side_effect = Exception("Processing failed")
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        context = MockContext()
        
        result = doc_handler(mock_event, context)
        
        assert result['statusCode'] == 500
        assert 'error' in result['body']
        
        print(" Test passed: Ingestion failure handled correctly")

if __name__ == "__main__":
    print("=" * 80)
    print("Running Document Ingestion Lambda Tests")
    print("=" * 80)
    
    test_doc_handler_success()
    test_doc_handler_ingestion_failure()
    
    print("\n" + "=" * 80)
    print("All Lambda tests completed!")
    print("=" * 80)

