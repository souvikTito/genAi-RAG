### ingestion handler

# app/handlers/ingestion_handler.py

from app.services import document_processing
from app.utils.util import logger, modelType as model_type
from app.utils.helpers import add_to_doc_table, add_to_s3, parse_s3_key
from app.models.s3 import s3
from urllib.parse import unquote_plus
import os
import asyncio
import json
import boto3
from datetime import datetime, timezone
from app.models.bedrock_client import get_bedrock_client

lambda_client = boto3.client('lambda')
doc_write_lambda = os.getenv("DOCUMENT_WRITE_LAMBDA")
table_name = os.getenv("DOCUMENTS_TABLE_NAME")

def doc_ingestion(event):
    """
    Handler for document ingestion + QA.
    Expects: {
        "s3_bucket": "bucket-name",
        "s3_key": "path/to/file.pdf",
        "user_id": "abc123",
        "chatId": "chatA1",
        "documentId": "doc123"
    }
    """
    # bucket = event.get("s3_bucket")
    # key = event.get("s3_key")       #file path
    # user_id = event.get("user_id")
    # chat_id = event.get("chatId")
    # doc_id = event.get("documentId")
    record = event["Records"][0]
    raw_bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    # key = record["s3"]["object"]["key"]

    processing_bucket = os.getenv('S3_DOCUMENTS_BUCKET')

    print(f"Triggered by S3 upload: bucket={raw_bucket}, key={key}")
    try:
        user_id, doc_id, filename = parse_s3_key(key)
    except Exception as e:
        print(f"Failed to parse metadata from key: {key}. Error: {str(e)}")
        raise
    
    print(f"Starting ingestion for document_PK: {doc_id}, file: {key}")

    try:
        #Download file from S3
        response = s3.get_object(Bucket=raw_bucket, Key=key)
        file_bytes = response['Body'].read()

        #save s3 files to tmp
        raw_filename = os.path.basename(key)
        local_path = f"/tmp/{raw_filename}"

        with open(local_path, 'wb') as f:
            f.write(file_bytes)
        
        print(f"File saved successfully to: {local_path}")

    except Exception as e:
        print(f"Failed to download or save file: {str(e)}", exc_info=True)
        raise

    # For Local Run
    # import tempfile
    # tmp_dir = tempfile.gettempdir()
    # local_path = os.path.join(tmp_dir, f"{chat_id}_{filename}")

    # with open(local_path, "wb") as f:
    #     f.write(file_bytes)

    #Record processing started data
    processing_start = datetime.now(timezone.utc).isoformat()
    processing_status = "Started"

    # Initialise Bedrock Client
    bedrock = get_bedrock_client() 
    # Process the document
    doc_context = document_processing.process_file(local_path, bedrock_client=bedrock)
    

    #Record completed data
    processing_end = datetime.now(timezone.utc).isoformat()
    processing_status = "Completed" if doc_context else "Failed"

    if doc_context:
        print(f"Successfully processed: {key}")
        content = str(doc_context.get("content"))[:200]
        print(f"Processed {key}. Context: {content}...")
    else:
        print(f"File processing skipped or failed: {key}. Skipping query for this file type.")
        logger.info(f"File processing failed or skipped for {key}. No context available.")

    try:
        # Insert to doc table
        dynamo_doc_payload = asyncio.run(add_to_doc_table(raw_bucket,
            processing_bucket, filename, raw_filename, file_bytes, user_id, 
            document_PK=doc_id, doc_processed_data=doc_context
        ))
        logger.info(f"Document Payload created for DynamoDB: {doc_id}")
        
    except Exception as e:
        logger.error(f"Failed to create DynamoD Payload: {str(e)}", exc_info=True)
        raise Exception(f"Failed to create DynamoD Payload {doc_id}")

    try:
        # Insert to S3
        s3_doc_payload = asyncio.run(add_to_s3(raw_bucket,
            processing_bucket, filename, raw_filename,file_bytes, user_id, 
            doc_processed_data=doc_context, document_PK=doc_id
        ))
        logger.info(f"Document uploaded to S3: {filename}")
        
    except Exception as e:
        print("S3 error")
        logger.error(f"Failed to upload to S3: {str(e)}", exc_info=True)
        raise Exception(f"S3 upload failed for document {doc_id}")
    
    #Add processed meta data to the table
    dynamo_doc_payload["processingStatus"] = processing_status
    dynamo_doc_payload["processingStartTimestamp"] = processing_start
    dynamo_doc_payload["processingEndTimestamp"] = processing_end


    #invoke dynamodb lambda
    db_event = {
        "tableName":table_name,
        "payload": dynamo_doc_payload
    }

    print ("Invoking Dynamo Lambda: ", db_event)
    lambda_response = lambda_client.invoke(
        FunctionName=doc_write_lambda,     #change lambda name 
        InvocationType="RequestResponse",
        Payload=json.dumps(db_event)
    )
    db_result = json.load(lambda_response['Payload'])
    print(f"The dynamo write lambda response is: {db_result}")

    # Clean up the temporary file
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Temporary file deleted: {local_path}")
        else:
            print(f"Temporary file not found for deletion: {local_path}")
    except Exception as e:
        print(f"Failed to delete temporary file: {str(e)}")

    return {
        "statusCode": 200,
        "body": {
            "document": dynamo_doc_payload,
            "preprocessing_complete": True
        }
    }



