# util.py
# Get Mock document path fo retrieval.py testing
import logging, json, platform
from pathlib import Path
import os, re
from typing import List
from app.utils import logger_context
from itertools import islice

# Set local path
base_path = Path(r"C:\Users\600002608\Git\medpro-data-ai-gpt") # IMP: UPDATE your local base path here
relative_path_documents = Path("genai/app/testdocs/mock_documents.json") # This should not change
relative_path_history = Path("genai/app/testdocs/mock_history.json") # This should not change
full_path_documents = base_path / relative_path_documents
full_path_history = base_path / relative_path_history

# Model Selection
modelId = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Switch to Sonnet in Production
#modelId_option2 = "us.anthropic.claude-3-5-haiku-20241022-v1:0" 
modelId_option2 = "us.anthropic.claude-3-haiku-20240307-v1:0" # UNCOMMENT: For Haiku 3 
modelType = "sonnet" if "sonnet" in modelId else "haiku" # This should not change
embeddingModel = "amazon.titan-embed-text-v2:0"
maxOutputTokens = 3000 # Keep upper limit buffer for complex queries
maxOutputTokens_withBuffer = maxOutputTokens - 1500 # keep a token buffer for complex queries
globalPrompt =[{"text": f"You are a professional, helpful, factual AI assistant for the employees of MedPro Group (formerly known as The Medical Protective Company)."
            f" Follow any ROLE assigned and complete the TASK accordingly."
            f" If the user query is vague, low-information, unclear, or cannot be reliably answered"
            f" from the available context, respond briefly with a safe follow up question. Do not attempt extended reasoning, speculation, or long explanations."
            f" Keep the output concise and stable. Ask well meaning follow up questions always."
            f" ALWAYS respond in the OUTPUT JSON SCHEMA"
            f" format provided - this is critical for downstream processing. Do not exceed token limit"
            f" of {maxOutputTokens_withBuffer} tokens. Always ensure that the OUTPUT JSON is complete & closed."
            f" Always ensure that any HTML inside the OUTPUT JSON is valid and properly closed.\n\n"
            "CONTEXT HANDLING:\n"
            "- When explicit CONTEXT or documents are provided, answer using ONLY that information.\n"
            "- MULTIPLE DOCUMENTS: If multiple documents are provided in the CONTEXT:\n"
            "  * If the user explicitly mentions or refers to a specific document (e.g., 'explain from document XYZ', 'according to the budget proposal'), "
            "    prioritize information from that document and cite it clearly.\n"
            "  * If the user's query is generic or references multiple documents, synthesize information from all relevant documents"
            "    and cite which document each piece of information comes from.\n"
            "  * Pay attention to document relevance scores - sections with higher relevance scores are more pertinent to the query.\n"
            "- When answering from CONTEXT, ALWAYS cite which document or section you're using (e.g., 'According to Document A, Section 2...').\n"
            "- If the answer is not in the provided CONTEXT, state clearly: 'This information is not found in the provided documents' "
            " and do not attempt to answer from general knowledge.\n"
            "- Do not give internal processing details (e.g., number of chunks, chunk IDs, embeddings, token counts, relevance scores)."
            " If such internal metadata appears in the context, respond normally to the user without mentioning these details.\n\n"
            "CONVERSATION CONTINUITY:\n"
            "- If CONVERSATION HISTORY is provided, use it to understand follow-up questions and maintain context."
            " Ask follow up questions if needed to clarify requirements.\n"
            "- If previous messages referenced a specific document or context, assume follow-up questions refer to the same document or context unless stated otherwise.\n\n"
            "Always remember that accuracy and honesty are paramount."}]

# Guardrail Config from AWS Bedrock
guardrailIdentifier= os.getenv("GUARDRAIL_ID", "22gv7e04bbov") # mpg Guardrail
#guardrailIdentifier= "lkwv1uqsnxqr" # General Guardrail
guardrailVersion = os.getenv("GUARDRAIL_VERSION", "DRAFT")
guardrailTrace = "enabled"
useGuardrails = True

## Manage model configurations for Input Tokens & CSV row limits
modelConfig = {
    "haiku": {"max_tokens": 200000, "max_rows": 10000},
    "sonnet": {"max_tokens": 200000, "max_rows": 10000}
}

# Logging Util
def configure_logger(request_id: str = None, chat_id: str = None, prompt_id: str= None) -> logging.Logger:
        logger = logging.getLogger('app') # change from 'name'

        if logger.hasHandlers() and request_id is None:
            return logger  # Prevent duplicate handlers

        if logger.hasHandlers():
            logger.handlers.clear()
        
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Prevent duplicate logs
        formatter = logging.Formatter('%(asctime)s- %(filename)s- %(name)s- %(levelname)s - %(message)s')

        # Always log to console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Determine log filename
        if request_id and chat_id and prompt_id:
            log_filename = f"{request_id}_{chat_id}_{prompt_id}.logs"
        elif request_id:
            log_filename = f"{request_id}.logs"
        else:
            log_filename = "app.logs"

        # Log to file only on Windows
        if platform.system() == "Windows":
            log_dir = 'logs'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'app.logs')
        else:
            log_dir = '/tmp'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, log_filename)
            logger_context.log_file_path = log_file

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

logger = configure_logger()


# For Loading mock data for retrieval local testing
def get_mock_data_path() -> str:
    if platform.system() == "Windows":
        logger.info(f"OS Detected - Windows/Local, Mock Document Data Path in Local For Retrieval")
        return full_path_documents
    else:
        logger.info(f"OS Detected - AWS, Mock Document Data Path in tmp folder/S3 in Lambda")
        return "/tmp/mock_documents.json"  # change to Lambda-compatible path later / s3 


# For Loading mock data for retrieval local testing
def get_mock_history_path() -> str:
    if platform.system() == "Windows":
        logger.info(f"OS Detected - Windows/Local, Mock Chat/Prompt History Data Path in Local For Retrieval")
        return full_path_history
    else:
        logger.info(f"OS Detected - AWS, Mock Chat/Prompt History Data Path in tmp folder/S3 in Lambda")
        return "/tmp/mock_documents.json"  # change to Lambda-compatible path later / s3 



# Util Function to persist entire Bedrock raw output silently
def persist_bedrock_response(response: dict, promptId: str, label: str = "bedrock"):
    base_dir = Path(__file__).resolve().parent.parent.parent
    logs_dir = base_dir / "logs" / "bedrock"

        # Handle AWS Lambda or restricted environments
    if not logs_dir.exists():
        if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:   # Assuming Lambda name is available at runtime in OS
            logs_dir = Path("/tmp/bedrock")
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create logs directory: {e}")
            return ""

    filename = f"{label}_{promptId}.json"
    filepath = logs_dir / filename

    try:
        with open(filepath, "w") as f:
            json.dump(response, f, indent=2)
        return str(filepath)
    except Exception as e:
        logger.error(f"Failed to persist Bedrock response: {e}")
        return ""
    

# Chat Handler Utility Functions
def clean_control_characters(text):
    """Remove invalid control characters that break JSON"""
    if isinstance(text, str):
        return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text


def clean_dict(data):
    """Recursively clean control characters from dict/list"""
    if isinstance(data, dict):
        return {k: clean_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_dict(item) for item in data]
    elif isinstance(data, str):
        return clean_control_characters(data)
    return data


def strip_markdown_fences(text):
    """Remove markdown code fences from JSON strings"""
    if not isinstance(text, str):
        return text
    
    text = text.strip()
    
    # Check for markdown code blocks
    if text.startswith("```"):
        lines = text.split('\n')
        
        # Remove opening fence (```json or just ```)
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        
        text = '\n'.join(lines).strip()
    
    return text


def unwrap_nested_json(data, max_depth=3):
    """
    Recursively unwrap double-nested JSON responses.
    Handles cases where Claude returns {"response": "{\"response\": \"...\"}"}
    
    CRITICAL: Also checks if "response" field itself contains a JSON string,
    even if other fields exist (like empty title, tags, chat_summary)
    """
    depth = 0
    logger.info ("Beggining Unwrapping of nested data")
    logger.info(f"Initial data type: {type(data)}")

    if isinstance(data, dict):
        logger.info(f"Initial keys: {list(data.keys())}")
        if "response" in data:
            logger.info(f"Response type: {type(data['response'])}")
            logger.info(f"Response preview: {str(data['response'])[:100]}...")

    while depth < max_depth:
        if isinstance(data, dict) and "response" in data:
            inner = data["response"]
            
            # Check if the "response" field is a JSON string
            if isinstance(inner, str):
                logger.info(f"Found string response, checking if it's JSON")
                # Clean control characters that break JSON
                inner = clean_control_characters(inner)

                # NEW: Strip markdown fences from inner string too!
                inner = strip_markdown_fences(inner)
                    
                inner_stripped = inner.strip()

                # Check if it looks like JSON
                if inner_stripped.startswith('{') and inner_stripped.endswith('}'):
                    try:    
                        logger.info("Attempting to parse inner JSON")
                        # First try with Strict false
                        parsed_inner = json.loads(inner_stripped, strict=False)
                        logger.info(f"Unwrapping layer {depth + 1}: 'response' field contains JSON string")
                        
                        # CRITICAL: Check if parsed_inner has the same structure (nested)
                        # If it has response, title, tags, etc., use it and discard wrapper
                        if isinstance(parsed_inner, dict) and "response" in parsed_inner:
                            # This is the real data, discard the wrapper
                            logger.info(f"Found nested structure, replacing wrapper with inner data")
                            data = parsed_inner
                            depth += 1
                            continue
                        else:
                            # Parsed but doesn't have nested structure, keep as-is
                            logger.info("Parsed inner JSON doesn't have nested 'response' field")
                            break
                    except json.JSONDecodeError as e:
                        # Not valid JSON, it's just a string with braces
                        logger.info(f"Unwrapping stopped: JSON parse failed at char {e.pos}")
                        
                        # Don't attempt repair - it causes more problems
                        # Just keep the current data structure as-is
                        break
                else:
                    # Plain string, not JSON
                    logger.info("Inner content doesn't look like JSON (no { } brackets)")
                    break
            # If we're here and depth == 0, no unwrapping happened
            break
        else:
            # No "response" key at all
            break
    
    if depth > 0:
        logger.info(f"UNWRAPPED {depth} LAYERS")
        logger.info(f"Final keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
    
    logger.info("Unwrapping complete!")
    return data


def ensure_valid_structure(data):
    """ 
    Ensure response is properly structured and typed.
    Does NOT add missing fields - only validates what exists.
    Guaranteed fields: response, title, chat_summary (others are feature-specific)
    """
    #if not isinstance(data, dict):
    #    logger.info(f"Response is not a dict, wrapping: {type(data)}")
    #    return {
    #        "response": str(data),
    #        "title": "Chat",
    #        "chat_summary": "Conversation with Medpro LLM"
    #    }
    
    # Unwrap if nested
    data = unwrap_nested_json(data)

    # CRITICAL: Only add guaranteed fields if ALL of them are missing
    # This prevents wrapping an already-correct response
    has_any_guaranteed = any(key in data for key in ["response", "title", "chat_summary"])
    
    if not has_any_guaranteed:
        # Completely empty/invalid structure, add defaults
        logger.info("Response missing all guaranteed fields, adding defaults")
        data = {
            "response": data.get("response", ""),
            "title": data.get("title", "Chat"),
            "chat_summary": data.get("chat_summary", "Conversation with Medpro LLM")
        }
    else:
        # Has some structure, only fill missing guaranteed fields
        guaranteed_fields = {
            "response": "",
            "title": "Chat",
            "chat_summary": "Conversation with Medpro LLM"
        }
        
        for key, default in guaranteed_fields.items():
            if key not in data:
                logger.info(f"Missing guaranteed field '{key}', adding default")
                data[key] = default
            elif not isinstance(data[key], str):
                logger.info(f"Field '{key}' is not a string: {type(data[key])}, converting")
                data[key] = str(data[key])
            elif isinstance(data[key], str):
                # NEW: Check if the field itself is still a nested JSON string
                value = data[key].strip()
                if value.startswith('{') and key in ['title', 'chat_summary']:
                    try:
                        parsed = json.loads(value, strict=False)
                        # If it's {"title": "actual value"}, extract the inner value
                        if isinstance(parsed, dict) and key in parsed:
                            logger.info(f"Unwrapping nested JSON string in field '{key}'")
                            data[key] = parsed[key]
                            # If still empty after unwrapping, use default
                            if not data[key] or not data[key].strip():
                                logger.info(f"Field '{key}' empty after unwrapping, using default")
                                data[key] = default
                    except json.JSONDecodeError:
                        # Not valid JSON, keep as-is
                        pass
                # Check if field is empty string and use default
                elif not value:
                    logger.info(f"Field '{key}' is empty, using default")
                    data[key] = default
        
        # Handle tags field specially (might be JSON array string)
        if "tags" in data:
            if isinstance(data["tags"], str):
                value = data["tags"].strip()
                if value.startswith('['):
                    try:
                        logger.info("Unwrapping nested JSON in 'tags' field")
                        data["tags"] = json.loads(value, strict=False)
                    except json.JSONDecodeError:
                        logger.warning(f"'tags' looks like JSON array but failed to parse")
                        data["tags"] = []
                elif not value:
                    # Empty string, set to empty array
                    data["tags"] = []
            elif not isinstance(data["tags"], list):
                logger.warning(f"'tags' is not a list: {type(data['tags'])}, converting to empty list")
                data["tags"] = []
    
    return data

def parse_claude_response(response_str, userQuery):
    """
    Parse Claude's response with multiple fallback strategies.
    Handles: string-JSON, nested JSON, markdown fences, plain text.
    
    Args:
        response_str: The raw response from Bedrock (can be str or dict)
    
    Returns:
        dict: Normalized response structure
    """
    # If already a dict, validate and return
    if isinstance(response_str, dict):
        logger.info("Response is already a dict, validating structure")
        try: 
            validated_data = ensure_valid_structure(response_str) 

            # If title and chat_summary are defaults, validation likely failed
            if validated_data.get("title") in ["Chat", ""]:
                    logger.info("Response doesn't look correct..")
                    counter = 0
                    while counter <=1:
                        counter += 1

                        # Check if response field looks like nested Json
                        #response_field = validated_data.get("response", "")
                        #if isinstance(response_field, str) and looks_like_json(response_field):
                        # IGNORING for now.. Always send non parseable output to Bedrock at least once
                        logger.info("Dict validation failed - response field contains non parseable JSON string")

                        # Try self repar on the nested JSON string
                        logger.info("Attempting self repair on Bedrock Dict Response...")
                        repaired = attempt_self_repair_with_claude(response_str, userQuery)

                        if repaired and isinstance(repaired, dict):
                            logger.info("Self repair on nested JSON Content")
                            return ensure_valid_structure(repaired)
                        
                        if isinstance(repaired, str):
                            repaired_str = repaired.strip()
                            try:
                                parsed = json.loads(repaired_str, strict=False)
                                if isinstance(parsed, dict):
                                    logger.info("Self repair return JSON string, parsed successfully")
                                    return ensure_valid_structure(parsed)
                            except Exception:
                                logger.info("Not even a valid JSON string after Self repair")
                                break #Not a valid JSON string return as is
                        
            # Validation succeeded or repair failed, return what we have
            return validated_data
  
        except Exception as e:
            logger.info(f"Dict serialization failed: {e}")

            # Try to stringify and repair the whole thing
            try: 
                dict_as_string = json.dumps(response_str)
                logger.info("Attempting self repair on stringified dict...")
                repaired = attempt_self_repair_with_claude(dict_as_string, userQuery)

                if repaired and isinstance(repaired, dict):
                    logger.info("Self repair successfull on stringifield dict")
                    return ensure_valid_structure(repaired)
                                  
                if isinstance(repaired, str):
                    repaired_str = repaired.strip()
                    try:
                        parsed = json.loads(repaired_str, strict=False)
                        if isinstance(parsed, dict):
                            logger.info("Self repair return JSON string, parsed successfully")
                            return ensure_valid_structure(parsed)
                    except Exception:
                        logger.info("Not even a valid JSON string after Self repair")
                        pass #Not a valid JSON string

            except:
                logger.info("Unable to repair stringified dict")
                pass
            
            # Fallback
            return ensure_valid_structure(response_str)

    
    # If not a string at this point, something is wrong
    if not isinstance(response_str, str):
        logger.error(f"Unexpected response type: {type(response_str)}")
        return ensure_valid_structure({"response": str(response_str)})
    
    # Strip and clean the string
    response_str = response_str.strip()

    # Log before stripping
    logger.info(f"Before strip_markdown_fences: starts with '{response_str[:20]}'")
   
    response_str = strip_markdown_fences(response_str)

    # Log after stripping
    logger.info(f"After strip_markdown_fences: starts with '{response_str[:20]}'")
  
    
    # Try to parse as JSON
    try:
        # Clean control characters
        cleaned_response_str = clean_control_characters(response_str)
        parsed_data = json.loads(cleaned_response_str, strict=False)
        logger.info("Successfully parsed response as JSON")
        
        # Validate and unwrap if needed
        validated_data = ensure_valid_structure(parsed_data)
        return validated_data
        
    except json.JSONDecodeError as e:
        logger.info(f"JSON parse failed at char {e.pos}: {e.msg}")
        
        # Check if it's HTML/plain text that should be wrapped
        if response_str.strip().startswith("<"):
            logger.info("Response appears to be HTML/plain text, wrapping in structure without Self repair")
            return ensure_valid_structure({
                "response": response_str,
                "title": "Chat",
                "tags": [],
                "chat_summary": "Conversation with Medpro LLM"
            })
        
        # NEW: Try self-repair with Claude before giving up
        logger.info("Attempting self repair with Bedrock retry as last resort...")
        repaired = attempt_self_repair_with_claude(response_str, userQuery)

        if repaired and isinstance(repaired, dict):
            logger.info("Self-repair successful, using repaired response dict")
            return ensure_valid_structure(repaired)

        if isinstance(repaired, str):
            repaired_str = repaired.strip()
            try:
                parsed = json.loads(repaired_str, strict=False)
                if isinstance(parsed, dict):
                    logger.info("Self repair return JSON string, parsed successfully")
                    return ensure_valid_structure(parsed)
            except Exception:
                logger.info("Not even a valid JSON string after Self repair")
                pass #Not a valid JSON string

        # Last resort: return as-is wrapped in structure
        logger.error("Unable to parse response & Self repair failed, returning as plain text")
        return ensure_valid_structure({"response": response_str})

def normalize_response_for_dynamo(response_data):
    # If response_data["response"] is itself a JSON string, decode it once
    if isinstance(response_data, dict) and isinstance(response_data.get("response"), str):
        logger.info ("Bedrock Response reached final normalization block for Prompt payload")
        try:
            inner = json.loads(response_data["response"])
            # If inner is a dict, replace it
            if isinstance(inner, dict):
                logger.info("Inner part a dict, using unwrapped layer finally")
                response_data["response"] = inner
        except Exception:
            logger.info("Normalization not needed: Response not nested for Prompt Payload")
            pass
    return response_data


def attempt_self_repair_with_claude(raw_broken_json: str, userQuery: str = ""):
    """
    Calls Claude to repair malformed JSON as last resort.
    Returns dict with response, title, chat_summary or None if repair fails.
    """
    from app.models.bedrock_client import invoke_claude

    repair_system = [{"text": """You received a malformed JSON. 
        Extract any readable text content and return this simple JSON SCHEMA: 
        { "response" : "the extracted text here using HTML formatting for the frontend. Use HTML tags like <p>, <br>, <strong>, <ul>, <li> etc. Use appropriate heading tags (<h2>, <h3>, <h4>) to structure the content based on section importance and hierarchy. Do NOT use Markdown.  For code blocks, use <pre> tags with minimal escaping of special characters - Do not use special characters that require escaping instead use plain text.",
          "title": "Concise, descriptive title that captures the main topic. If the title previously is just 'Chat', then give it another appropriate Title."
        }

        Guidelines:
        - Return a single valid JSON only.              
        - In your response, Do NOT wrap fields like "response" in an extra JSON string.
            - For example, NEVER return: {"response": "{ \"response\": ... }"
        - No Markdown, no code fences, no explanations, no commentary, no trailing text, no backticks.
        - Output must start with '{' and end with '}' with nothing before or after.
        - Use proper string escaping for HTML content (single backslash before special characters). Do NOT double-escape.
        - For Code sections, keep your response simple. Do not use special characters that require escaping. Use Simple formatting so that it is easy to parse in a json.dumps.

        """ }]

    repair_user = f"""
        <<<MalformedInput>>>
        {raw_broken_json}
        <<</MalformedInput>>>
        
        <<<USER_QUERY>>>
        {userQuery}
        <<</USER_QUERY>>>

        """
    logger.info("Self Repair Note: Sending to Bedrock for Repair: %s", raw_broken_json)
    try:
        logger.info("Important: Calling Bedrock again for JSON repair...")
        
        # Use your bedrock client to call Claude
        fixed_text = invoke_claude(
            system_prompts=repair_system,
            prompt=repair_user,
            max_tokens=maxOutputTokens_withBuffer,
            temperature=0,
            top_p=1.0,
            model_id=modelId_option2
        )

        logger.info("Fixed Response from Bedrock: %s", fixed_text["response"])

        repair_text = fixed_text["response"]

        if not repair_text:
            logger.error("Empty response from repair attempt")
            return None
        
        # If we already got a dictionary back   
        if isinstance(repair_text, dict):
            logger.info("NOTICE: JSON repair successful!")
            logger.info("Repair returned a dictionary directly")
            return repair_text

        if isinstance(repair_text, str):
            # Self repair created a string
            # Strip any markdown fences
            repair_text = strip_markdown_fences(repair_text)
            
            # Additional check for nested JSON
            try:
                parsed_json = json.loads(repair_text, strict=False)
                logger.info("NOTICE: JSON string repair successful!")
                return parsed_json  # Return the parsed dictionary

            except json.JSONDecodeError as json_err:
                logger.error(f"Repair returned text but not valid JSON: {json_err}")
                return repair_text  # Fall back to returning the string

        
        logger.info("NOTICE: JSON repair successful but unexpected type!")
        return repair_text
        
    except Exception as e:
        logger.error(f"JSON repair failed from Bedrock Self Repair: {str(e)}")
        return None

def looks_like_json(s: str) -> bool:
   s = s.strip()
   # Must start and end with matching braces
   if not (s.startswith("{") and s.endswith("}")):
       return False
   # Must contain at least one colon (key-value pair)
   if ":" not in s:
       return False
   # Reject cases where HTML tags appear before any JSON keys
   if re.search(r"<[a-zA-Z]", s):
       return False
   return True


# Some helper functions for CSV Handling
def prepare_csv_for_llm(csv_data: List[dict], user_query: str, summary: str = None) -> dict:
    """
    Intelligently samples CSV data based on query and size.
    Returns structured data optimized for LLM context.
    """
    if not csv_data:
        return {'columns': [], 'total_rows': 0, 'rows': []}
    
    
    columns = list(csv_data[0].keys())
    total_rows = len(csv_data)
    
    logger.info(f"Preparing smart filtering of CSV data: Columns: {columns}, Total Rows: {total_rows}")
    
    # Small dataset - send everything
    if total_rows <= 100:
        logger.info(f"CSV data with few records, so sending as is.")
        return {
            'columns': columns,
            'total_rows': total_rows,
            'summary': summary,
            'rows': csv_data
        }
    
    # Large dataset - smart sampling
    logger.info(f"CSV data with many records, so starting Smart filtering")
    sample_rows = csv_data[:50]
    
    # Get analytical rows
    analytical_rows = add_analytical_samples(csv_data, user_query)

    # If analytical samples were found, use them as relevant rows
    if analytical_rows:
        logger.info(f"Analytical query detected, found {len(analytical_rows)} relevant rows")
        relevant_rows = analytical_rows
    # Otherwise fall back to keyword filtering
    else: 
        # Extract keywords (filter short words)
        keywords = [word.lower() for word in user_query.split() if len(word) > 3]
        logger.info(f"Keywords found: {keywords}")

        # Use generator with early exit for performance
        if keywords:
            def matching_rows():
                for row in csv_data[50:]:
                    # Convert row values to lowercase string once
                    row_str = ' '.join(str(v).lower() for v in row.values())
                    if any(kw in row_str for kw in keywords):
                        yield row
            
            relevant_rows = list(islice(matching_rows(), 50))
            logger.info(f"Relevant rows found by keyword filtering: {len(relevant_rows)}")
        else:
            logger.info(f"No keywords for filtering, skipping relevant rows search")
            relevant_rows = []
    
    return {
        'columns': columns,
        'total_rows': total_rows,
        'summary': summary,
        'sample_rows': sample_rows,
        'relevant_rows': relevant_rows
    }


# CSV Handling Helper Function
def format_rows_as_table(rows: List[dict], columns: List[str]) -> str:
    """Convert rows to simple CSV string format"""
    if not rows:
        return "(No data)\n"
    
    # Header
    result = ','.join(columns) + '\n'
    
    # Rows
    for row in rows:
        result += ','.join(str(row.get(col, '')) for col in columns) + '\n'
    
    return result


def add_analytical_samples(csv_data: List[dict], user_query: str) -> List[dict]:
    """Extract analytical samples based on query intent for min/max/average values.
    Works with any dataset and detects generic analytical intents.
    """
    if not csv_data or len(csv_data) == 0:
        return []
        
    analytical_samples = []
    query_lower = user_query.lower()
    
    # Detect analytical intents
    find_highest = any(term in query_lower for term in ['highest', 'maximum', 'max', 'top', 'largest', 'greatest', 'most', 'expensive', 'highest-paid'])
    find_lowest = any(term in query_lower for term in ['lowest', 'minimum', 'min', 'bottom', 'smallest', 'least', 'cheapest', 'lowest-paid'])
    find_average = any(term in query_lower for term in ['average', 'avg', 'mean', 'median', 'typical', 'middle'])
    find_trend = any(term in query_lower for term in ['trend', 'pattern', 'growth', 'decline', 'increase', 'decrease'])
    find_outliers = any(term in query_lower for term in ['outlier', 'outliers', 'anomaly', 'unusual', 'exceptional', 'atypical'])
    find_distribution = any(term in query_lower for term in ['distribution', 'spread', 'range', 'variance', 'standard deviation'])
    find_comparison = any(term in query_lower for term in ['compare', 'comparison', 'versus', 'vs', 'difference between'])
    find_correlation = any(term in query_lower for term in ['correlation', 'relationship', 'connection', 'associated'])


    # If no analytical intent detected, return empty list
    if not (find_highest or find_lowest or find_average or find_trend or find_outliers):
        logger.info(f"No Analytical intent detected via keyword matches.")
        return []
    
    # Find all potentially numeric columns
    numeric_columns = []
    for col in csv_data[0].keys():
        # Check a sample of values to determine if column is numeric
        sample_size = min(10, len(csv_data))
        numeric_values = 0
        for i in range(sample_size):
            try:
                # Try to convert to float, counting successes
                val = csv_data[i].get(col, '')
                if val and (isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).replace('-', '', 1).isdigit())):
                    float(val)
                    numeric_values += 1
            except (ValueError, TypeError):
                pass
        
        # If most values are numeric, consider it a numeric column
        if numeric_values >= sample_size * 0.7:  # 70% threshold
            numeric_columns.append(col)
    
    # If no numeric columns found, return empty list
    if not numeric_columns:
        return []
    
    # Try to identify the most relevant numeric column based on query terms
    target_column = None
    for col in numeric_columns:
        col_lower = col.lower()
        # Check if column name appears in the query
        if any(term in col_lower for term in query_lower.split()):
            target_column = col
            logger.info("Target column found: ", target_column)
            break
    
    # If no specific column identified, use the first numeric column
    if not target_column and numeric_columns:
        target_column = numeric_columns[0]
        logger.info("No Target column found, taking Target as:", target_column)
    
    # Process based on analytical intent
    if target_column:
        # Convert to numeric for sorting
        for row in csv_data:
            try:
                row[f'_numeric_{target_column}'] = float(row[target_column]) if row[target_column] else 0
            except (ValueError, TypeError):
                row[f'_numeric_{target_column}'] = 0
        
        if find_highest:
            # Sort descending and take top 5
            logger.info(f"Analytical matched = find_highest")
            # DEBUG: Print sample of numeric values used for sorting
            logger.info(f"Sample numeric values for sorting: {[row.get(f'_numeric_{target_column}') for row in csv_data[:5]]}")
     
            sorted_data = sorted(csv_data, key=lambda x: x[f'_numeric_{target_column}'], reverse=True)
            analytical_samples = sorted_data[:5]

            # DEBUG: Print the highest values found
            logger.info(f"Top 5 highest values for {target_column}: {[row.get(target_column) for row in analytical_samples]}")
            logger.info(f"Corresponding numeric values: {[row.get(f'_numeric_{target_column}') for row in analytical_samples]}")
            
        elif find_lowest:
            logger.info(f"Analytical matched = find_lowest")
            # Sort ascending and take bottom 5
            sorted_data = sorted(csv_data, key=lambda x: x[f'_numeric_{target_column}'])
            analytical_samples = sorted_data[:5]
            # DEBUG: Print the lowest values found
            logger.info(f"Top 5 lowest values for {target_column}: {[row.get(target_column) for row in analytical_samples]}")
            logger.info(f"Corresponding numeric values: {[row.get(f'_numeric_{target_column}') for row in analytical_samples]}")
            
        elif find_average:
            logger.info(f"Analytical matched = find_average")
            # Calculate average and find rows close to average
            values = [row[f'_numeric_{target_column}'] for row in csv_data if row[f'_numeric_{target_column}'] != 0]
            if values:
                avg_value = sum(values) / len(values)
                # Sort by closeness to average
                sorted_data = sorted(csv_data, key=lambda x: abs(x[f'_numeric_{target_column}'] - avg_value))
                analytical_samples = sorted_data[:5]
                # DEBUG: Print the average values found
                logger.info(f"Top average values for {target_column}: {[row.get(target_column) for row in analytical_samples]}")
                logger.info(f"Corresponding numeric values: {[row.get(f'_numeric_{target_column}') for row in analytical_samples]}")
             
        elif find_trend:
            logger.info(f"Analytical matched = find_trend")
            # Identify potential time/date columns
            date_columns = [col for col in csv_data[0].keys() if any(date_term in col.lower() for date_term in ['date', 'time', 'year', 'month', 'day'])]
            
            if date_columns:
                time_col = date_columns[0]  # Use the first identified date column
                # Sort by date column and take samples across the time range
                try:
                    sorted_data = sorted(csv_data, key=lambda x: x[time_col])
                    # Take samples from beginning, middle and end to show trend
                    samples_count = min(len(sorted_data), 5)
                    indices = [int(i * (len(sorted_data)-1) / (samples_count-1)) for i in range(samples_count)]
                    analytical_samples = [sorted_data[i] for i in indices]

                    # DEBUG: Print the Trend values found
                    logger.info(f"Trend for {target_column}: {[row.get(target_column) for row in analytical_samples]}")
                    logger.info(f"Corresponding numeric values: {[row.get(f'_numeric_{target_column}') for row in analytical_samples]}")
            
                except (KeyError, TypeError):
                    # Fallback if sorting fails
                    logger.info("Failed to find analytical samples using trend calculation logic. Taking top 5.")
                    analytical_samples = csv_data[:5]
            else:
                logger.info("No date column found in CSV. Need atleast one column with date, time etc in the column name.")
        
        elif find_outliers:
            logger.info(f"Analytical matched = find_outliers")
            values = [row[f'_numeric_{target_column}'] for row in csv_data if f'_numeric_{target_column}' in row]
            if values:
                # Calculate mean and standard deviation
                mean = sum(values) / len(values)
                std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
                
                # Find rows with values more than 2 standard deviations from mean
                outliers = [row for row in csv_data if abs(row.get(f'_numeric_{target_column}', 0) - mean) > 2 * std_dev]
                
                if outliers:
                    logger.info("Outliers found! Taking the top 5...")
                    analytical_samples = outliers[:5]
                    # DEBUG: Print the top 5 outliers found
                    logger.info(f"Top outlier values for {target_column}: {[row.get(target_column) for row in analytical_samples]}")
                    logger.info(f"Corresponding numeric values: {[row.get(f'_numeric_{target_column}') for row in analytical_samples]}")
            
                else:
                    # If no clear outliers, take the most extreme values
                    logger.info("No clear outliers, taking most extreme values")
                    sorted_data = sorted(csv_data, key=lambda x: abs(x.get(f'_numeric_{target_column}', 0) - mean), reverse=True)


        # Clean up temporary numeric field
        for row in analytical_samples:
            if f'_numeric_{target_column}' in row:
                del row[f'_numeric_{target_column}']

    logger.info(f"Analytical rows detected: {len(analytical_samples)} records")

    return analytical_samples


def has_embedded_newlines(file_path):
   with open(file_path, "r", errors="ignore") as f:
       in_quotes = False
       for line in f:
           for char in line:
               if char == '"':
                   in_quotes = not in_quotes
           if in_quotes and line.endswith("\n"):
               return True
   return False

