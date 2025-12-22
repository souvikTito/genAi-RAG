"""
Test Ingestion Handler
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

try:
    # Try importing the handler
    from app.handlers.ingestion_handler import doc_ingestion
    print(" Successfully imported doc_ingestion")
except ImportError as e:
    print(f" Import error: {e}")
    print("Trying to find the correct module...")
    
    # List Python files to debug
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file == 'ingestion_handler.py':
                print(f"Found: {os.path.join(root, file)}")
    
    sys.exit(1)

def test_doc_ingestion_basic():
    """Test basic document ingestion"""
    print("\n--- Test: Basic PDF Document Ingestion ---")
    
    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "test-raw-bucket"
                    },
                    "object": {
                        "key": "user-001/doc-12345/sample.pdf"
                    }
                }
            }
        ]
    }

    # Mock all dependencies
    with patch('app.handlers.ingestion_handler.s3') as mock_s3, \
         patch('app.handlers.ingestion_handler.document_processing') as mock_doc_processing, \
         patch('app.handlers.ingestion_handler.add_to_doc_table') as mock_add_doc_table, \
         patch('app.handlers.ingestion_handler.add_to_s3') as mock_add_s3, \
         patch('app.handlers.ingestion_handler.lambda_client') as mock_lambda_client, \
         patch('app.handlers.ingestion_handler.os.remove') as mock_os_remove, \
         patch('app.handlers.ingestion_handler.parse_s3_key') as mock_parse_s3, \
         patch('builtins.open') as mock_open:

        # Mock S3 key parsing
        mock_parse_s3.return_value = ("user-001", "doc-12345", "sample.pdf")
        
        # Mock S3 download
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=b"PDF file content"))
        }
        
        # Mock file processing
        mock_doc_processing.process_file.return_value = {
            "content": "This is processed document content",
            "pages": 5,
            "file_type": "pdf",
            "processing_time": 2.5
        }
        
        # Mock async functions
        mock_add_doc_table.return_value = {
            "documentId": "doc-12345",
            "userId": "user-001",
            "filename": "sample.pdf",
            "fileType": "pdf",
            "fileSize": 1024,
            "s3RawBucket": "test-raw-bucket",
            "s3ProcessedBucket": "mpg-dev-documents-processing",
            "processingStatus": "Completed"
        }
        
        mock_add_s3.return_value = {
            "s3_key": "processed/user-001/doc-12345/sample.pdf",
            "bucket": "mpg-dev-documents-processing"
        }
        
        # Mock Lambda response
        mock_lambda_response = MagicMock()
        mock_lambda_response.__getitem__.return_value = json.dumps({
            "statusCode": 200,
            "body": {"message": "Document metadata stored successfully"}
        })
        mock_lambda_client.invoke.return_value = mock_lambda_response

        # Execute the function
        result = doc_ingestion(mock_event)
        
        # Assertions
        assert result['statusCode'] == 200
        assert result['body']['preprocessing_complete'] == True
        assert result['body']['document']['documentId'] == 'doc-12345'
        assert result['body']['document']['processingStatus'] == 'Completed'
        
        print(" Test passed: Basic document ingestion works correctly")

def test_doc_ingestion_processing_failure():
    """Test document ingestion when processing fails"""
    print("\n--- Test: Processing Failure ---")
    
    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "test-raw-bucket"
                    },
                    "object": {
                        "key": "user-001/doc-99999/corrupted.pdf"
                    }
                }
            }
        ]
    }

    with patch('app.handlers.ingestion_handler.s3') as mock_s3, \
         patch('app.handlers.ingestion_handler.document_processing') as mock_doc_processing, \
         patch('app.handlers.ingestion_handler.add_to_doc_table') as mock_add_doc_table, \
         patch('app.handlers.ingestion_handler.add_to_s3') as mock_add_s3, \
         patch('app.handlers.ingestion_handler.lambda_client') as mock_lambda_client, \
         patch('app.handlers.ingestion_handler.os.remove') as mock_os_remove, \
         patch('app.handlers.ingestion_handler.parse_s3_key') as mock_parse_s3:

        mock_parse_s3.return_value = ("user-001", "doc-99999", "corrupted.pdf")
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=b"Corrupted PDF content"))
        }
        
        # Simulate processing failure
        mock_doc_processing.process_file.return_value = None
        
        mock_add_doc_table.return_value = {
            "documentId": "doc-99999",
            "userId": "user-001",
            "filename": "corrupted.pdf",
            "fileType": "pdf",
            "fileSize": 1024,
            "processingStatus": "Failed"
        }

        result = doc_ingestion(mock_event)
        
        # Should still return 200 but with failed status
        assert result['statusCode'] == 200
        assert result['body']['document']['processingStatus'] == 'Failed'
        
        print(" Test passed: Processing failure handled gracefully")

if __name__ == "__main__":
    print("=" * 80)
    print("Running Ingestion Handler Tests")
    print("=" * 80)
    
    # Run tests manually
    test_doc_ingestion_basic()
    test_doc_ingestion_processing_failure()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)

