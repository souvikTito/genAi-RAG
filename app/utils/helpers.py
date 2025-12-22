### helpers

import json
from datetime import datetime, timezone
from app.utils.util import logger
from app.models.dynamodb import read_from_dynamodb, dynamoDb
from app.models.s3 import s3
import base64
import os, re
from pathlib import Path

doc_table = os.getenv("DOCUMENTS_TABLE_NAME")
session_table = os.getenv("SESSION_TABLE_NAME")
chat_table = os.getenv("CHATS_TABLE_NAME")
prompt_template_table = os.getenv("PROMPT_TEMPLATES_TABLE")

file_types_allowed = ['pdf','csv','jpg','png','docx','jpeg']
max_size = 10*1024*1024     #10 mb
max_files_per_chat = 6

# Cleaning JSON from bytes
def clean_json(obj):
   if isinstance(obj, bytes):
       logger.info(f"Converted bytes → base64")
       return base64.b64encode(obj).decode("utf-8")
   if isinstance(obj, list):
       logger.info(f"Converted List → base64")
       return [clean_json(x) for x in obj]
   if isinstance(obj, dict):
       logger.info(f"Converted Dict → base64")
       return {k: clean_json(v) for k, v in obj.items()}
   return obj

async def add_to_doc_table(raw_bucket:str, processing_bucket:str, file_name:str, raw_filename:str,content:bytes, user_PK:str,document_PK:str,doc_processed_data: dict):
    print(f"Preparing DynamoDB-safe payload for documentId: {document_PK}")

    file_type = doc_processed_data.get("file_type", "")
    summary = doc_processed_data['summary'].get("response", "Missing document summary")
    
    processing_key = f"documents/{document_PK}.json"
    processing_s3_path = f"s3://{processing_bucket}/{processing_key}"

    raw_s3_key = f"doc_processing/{user_PK}/{document_PK}_{raw_filename}"
    raw_s3_path = f"s3://{raw_bucket}/{raw_s3_key}"

    # user_file_name = file_name.split('_')[1]
    session_PK = get_latest_session_for_user(user_PK)


    doc_payload = {
        "document_PK": document_PK,
        "user_PK": user_PK,
        "session_PK": session_PK,
        "chat_PK": 'chatId12345',
        "s3Path": raw_s3_path,
        "fileName": file_name,
        "fileSize": len(content),
        "contentType": file_type,
        "summary": summary,
        "chunks": processing_s3_path,
        "embeddings": processing_s3_path,
        "imageData": processing_s3_path,
        "csvContent": processing_s3_path,
        "auditCreateDateTime": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    }

    return doc_payload

async def add_to_s3(raw_bucket:str, processing_bucket: str, file_name: str, raw_filename:str, content: bytes, user_PK: str, doc_processed_data: dict, document_PK: str):
    logger.info(f"Starting S3 document record upload for documentId: {document_PK}")

    try:
        file_type = doc_processed_data.get("file_type", "")

        summary = doc_processed_data['summary'].get("response", "Missing document summary")
        chunks = doc_processed_data.get("chunks", [])
        embeddings = doc_processed_data.get("embeddings", [])   
        image_data = doc_processed_data.get("image_data","")
        csv_content = doc_processed_data.get("content","")

        processed_s3_key = f"documents/{document_PK}.json"

        raw_s3_key = f"doc_processing/{user_PK}/{raw_filename}"
        raw_s3_path = f"s3://{raw_bucket}/{raw_s3_key}"

        # user_file_name = file_name.split('_')[1]

        session_PK = get_latest_session_for_user(user_PK)

        ## Safely clean Bytes in Chunks or Summary if needed
        if isinstance(summary, bytes):
            logger.info ("Cleaning BYTES found in Summary from Bedrock")
            summary = summary.decode("utf-8", errors="replace")

        clean_chunks = []
        for c in chunks:
            if isinstance(c, bytes):
                logger.info ("Cleaning BYTES found in Chunks from Bedrock")
                c = c.decode("utf-8", errors="replace")
            clean_chunks.append(c)
        chunks = clean_chunks

        if embeddings and any(isinstance(e, bytes) for e in embeddings):
            logger.info("Cleaning BYTES found in Embeddings from Bedrock")
            clean_embeddings = []
            for e in embeddings:
                if isinstance(e, bytes):
                    e = e.decode("utf-8", errors="replace")
                clean_embeddings.append(e)
            embeddings = clean_embeddings


        doc_payload = {
            "documentId": document_PK,
            "user_id": user_PK,
            "sessionId": session_PK,
            "chatId": '',
            "s3Path": raw_s3_path,
            "fileName": file_name,
            "fileSize": len(content),
            "contentType": file_type,
            "summary": summary,
            "chunks": chunks,
            "embeddings": embeddings,
            "imageData": base64.b64encode(image_data).decode("utf-8") if image_data else None,
            "csvContent": csv_content,
            "createdAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        }

        print(f"Uploading document metadata to S3 Bucket: {processing_bucket}, Key at: {processed_s3_key}")
        logger.info(f"Uploading document metadata to S3 Bucket: {processing_bucket}, Key at: {processed_s3_key}")
       
        s3.put_object(
            Bucket=processing_bucket,
            Key=processed_s3_key,
            Body=json.dumps(doc_payload),
            ContentType="application/json")
        
        logger.info(f"Successfully uploaded document metadata for documentId: {document_PK}")
        return doc_payload
    
    except TypeError as e:
        # Handle specific serialization errors
        logger.error(f"JSON serialization error: {str(e)}")
        
        # Identify problematic fields
        problem_fields = []
        for key, value in doc_payload.items():
            try:
                json.dumps({key: value})
            except TypeError:
                problem_fields.append(key)
                logger.error(f"Problem field identified: {key}")
        
        logger.error(f"Problematic fields in payload: {problem_fields}")
        raise
    except Exception as e:
        logger.error(f"Failed to upload to s3 document metadata for documentId: {document_PK}. Error: {str(e)}")
        raise RuntimeError(f"S3 upload failed for documentId: {document_PK}. Error: {str(e)}")


def validate_foreign_keys(body: dict):
    
    if not read_from_dynamodb("Users Table", body["User_id"]):
        return body, "User not found"

    if not read_from_dynamodb("Sessions Table", body["sessionId"]):
        return body, "Session not found"

    return body, None

def get_latest_session_for_user(user_PK: str):
    session_PK = None

    # Try from chat table
    session_details = read_from_dynamodb(
        table_name=session_table,
        index_name="SessionsByUser",
        partition_key="user_PK",
        partition_value=user_PK,
        sort_key="auditCreateDateTime",
        sort_desc=True,
        limit=1
    )

    # if session_details["sessionStatus"] == "ACTIVE":
    #     session_PK = session_details[0].get("session_PK")
    try:
        session_PK = session_details[0].get("session_PK")
        logger.info(f'Found session_PK: {session_PK}')
    except:
        logger.info('Session_PK not found')
        
    return session_PK or "session123"

def parse_s3_key(s3_key:str):
    path = Path(s3_key)
    filename = path.name.replace(' ','-')
    # stem = Path(filename).stem

    parts = filename.split("_", 1)
    # try:
    #     document_PK, full_filename = filename.split("_", 1)
    # except ValueError:
    #     raise ValueError(f"Invalid filename format: {filename}. Expected 'documentId_filename.ext'")
    
    # parts = path.parts
    if len(parts) < 2:
        raise ValueError(f"Invalid filename format: {filename}. Expected 'documentId_filename.ext'")
    
    document_PK = parts[0]
    full_filename = parts[1]

    path_parts = path.parts
    if len(path_parts) < 2:
        raise ValueError(f"Invalid S3 key structure: {s3_key}. Expected at least 2 parts")
    user_PK = path_parts[1]

    return user_PK, document_PK, full_filename



# Chat Engine Helper Function
def truncate_content(content, max_chars=None, truncation_marker="..TRUNCATED.."):
    """
    Truncates content if it exceeds the maximum length while preserving context.
    
    Args:
        content (str): The content to truncate
        max_chars (int, optional): Maximum allowed length of content. If None, no truncation occurs.
        truncation_marker (str): Marker to indicate truncation
        
    Returns:
        str: Truncated content if needed, original content otherwise
    """
    
    # If max_chars is None or content is within limits, return as is
    if max_chars is None or len(content) <= max_chars:
        return content
        
    # Calculate truncation points to preserve beginning and end context
    # Use 70% from start and 30% from end when truncating
    start_portion = int(max_chars * 0.7)
    end_portion = max_chars - start_portion - len(truncation_marker)
    
    # Perform the truncation
    truncated = content[:start_portion] + truncation_marker + content[-end_portion:]
    
    return truncated


# Retrieval Helper Function
def sanitize_retrieval_query(query: str) -> str:
    """
    Sanitize user query for document retrieval (PDF/DOCX).
    Balances noise removal with preserving semantic meaning.
    
    Args:
        query: Raw user query string
        
    Returns:
        Cleaned query optimized for document embedding similarity
    """    
    # Strip leading/trailing whitespace
    q = query.strip()
    
    # Remove URLs (not in documents typically)
    q = re.sub(r"https?://\S+|www\.\S+", "", q)
    
    # Remove HTML/XML tags (from pasted content)
    q = re.sub(r"<[^>]+>", "", q)
    
    # Remove excessive punctuation repetition (!!!, ???, ...)
    q = re.sub(r"([!?.]{2,})", lambda m: m.group(1)[0], q)
    
    # Normalize whitespace (including tabs, newlines)
    q = re.sub(r"\s+", " ", q)
    
    # Remove leading/trailing punctuation around the query
    q = q.strip(".,;:!?")
    
    return q.strip()


# Retrieval Query Type Detector for RAG Helper
def detect_query_type(query: str) -> str:
    """Detect if query is broad or specific."""
    q_lower = query.lower()
    
    # Broad queries
    if any(word in q_lower for word in ["summarize", "overview", "explain", "what is"]):
        return "broad"
    
    # Specific queries
    if any(word in q_lower for word in ["page", "section", "table", "figure", "specific"]):
        return "specific"
    
    return "normal"


    # Usage Sample
    """
    if query_type == "broad":
        top_k = 10
        similarity_threshold = 0.2
    elif query_type == "specific":
        top_k = 5
        similarity_threshold = 0.4
    else:
        top_k = 10
        similarity_threshold = 0.3

    """

def resolve_file_type(content_type: str, file_name: str = "") -> str:
    """
    Resolve file type based on contentType or fileName.
    Returns one of: 'csv', 'image', 'pdf', 'docx', or '' if unknown.
    """
    if not content_type and not file_name:
        return ""

    # Normalize both inputs
    ftype = content_type.strip().lower()
    fname = file_name.strip().lower()

    # Priority: contentType first, then fileName
    if "csv" in ftype or fname.endswith(".csv"):
        return "csv"
    elif any(ext in ftype for ext in ["png", "jpg", "jpeg"]) or fname.endswith((".png", ".jpg", ".jpeg")):
        return "image"
    elif "pdf" in ftype or fname.endswith(".pdf"):
        return "pdf"
    elif "docx" in ftype or fname.endswith(".docx"):
        return "docx"
    else:
        return ""
