import boto3, time
import os, json, re
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, ClientError
from app.utils.util import logger, modelId, maxOutputTokens, persist_bedrock_response
from app.utils.util import guardrailIdentifier, guardrailVersion, useGuardrails, guardrailTrace
from typing import Any, Dict, Optional

# Load environment variables
load_dotenv()

# Nuclear cleaning option below (not used for now) .. Clearing done by Parser post Orchestration instead
def clean_response_text(text):
    """Remove invalid control characters that break JSON encoding"""
    if not isinstance(text, str):
        return text
    # Remove control characters except \n (newline), \r (carriage return), \t (tab)
    return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    #return text

def get_bedrock_credentials():
    """
    Get credentials for Bedrock client.
    
    - In Lambda: Use STS to assume Bedrock invocation role
    - Locally: Use .env credentials or default AWS profile
    
    Returns:
        dict with boto3 session kwargs
    """
    # Check if running in Lambda (AWS_EXECUTION_ENV exists in Lambda)
    is_lambda = os.getenv('AWS_EXECUTION_ENV') is not None # pragma: allowlist-secret
    
    if is_lambda:
        # Lambda environment - use STS to assume Bedrock role
        bedrock_role_arn = os.getenv('BEDROCK_ROLE_ARN') # pragma: allowlist-secret
        
        if not bedrock_role_arn:
            logger.error("BEDROCK_ROLE_ARN not set in Lambda environment")
            raise ValueError("BEDROCK_ROLE_ARN environment variable is required in Lambda")
        
        logger.info(f"Lambda environment detected. Assuming Bedrock role: {bedrock_role_arn}")
        
        try:
            # Create STS client with Lambda execution role credentials
            sts_client = boto3.client('sts') # pragma: allowlist-secret
            
            # Assume the Bedrock invocation role
            assumed_role = sts_client.assume_role(
                RoleArn=bedrock_role_arn,
                RoleSessionName='BedrockInvocationSession',
                DurationSeconds=900
            )
            
            credentials = assumed_role['Credentials']
            
            logger.info("Successfully assumed Bedrock invocation role")
            
            return {
                'aws_access_key_id': credentials['AccessKeyId'], # pragma: allowlist-secret
                'aws_secret_access_key': credentials['SecretAccessKey'], # pragma: allowlist-secret
                'aws_session_token': credentials['SessionToken'], # pragma: allowlist-secret
                'region_name': os.getenv('AWS_REGION', 'us-east-2') # pragma: allowlist-secret
            }
            
        except Exception as e:
            logger.error(f"Failed to assume Bedrock role: {e}")
            raise
    
    else:
        # Local development - use .env credentials or default AWS profile
        logger.info("Local environment detected. Using .env credentials or AWS profile")
        
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', "") # pragma: allowlist-secret
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', "") # pragma: allowlist-secret
        aws_session_token = os.getenv("AWS_SESSION_TOKEN", "") # pragma: allowlist-secret
        aws_region = os.getenv('AWS_REGION', 'us-east-2') # pragma: allowlist-secret
        
        # Debug logging
        logger.debug(f"AWS Access Key loaded: {'Yes' if aws_access_key_id else 'No'}") # pragma: allowlist-secret
        logger.debug(f"AWS Secret Key loaded: {'Yes' if aws_secret_access_key else 'No'}") # pragma: allowlist-secret
        logger.debug(f"AWS Session Token loaded: {'Yes' if aws_session_token.strip() else 'No'}") # pragma: allowlist-secret
        logger.debug(f"AWS Region: {aws_region}") # pragma: allowlist-secret
        
        # If credentials exist in .env, use them
        if aws_access_key_id and aws_secret_access_key: # pragma: allowlist-secret
            return {
                'aws_access_key_id': aws_access_key_id, # pragma: allowlist-secret
                'aws_secret_access_key': aws_secret_access_key, # pragma: allowlist-secret
                'aws_session_token': aws_session_token if aws_session_token.strip() else None, # pragma: allowlist-secret
                'region_name': aws_region # pragma: allowlist-secret
            }
        else:
            # Use default AWS credentials (from ~/.aws/credentials or IAM role)
            logger.info("No .env credentials found. Using default AWS credentials chain") # pragma: allowlist-secret
            return {
                'region_name': aws_region
            }
        
def get_bedrock_client(model_id: str = modelId):
    # Initialize Bedrock client
    logger.info("Initializing Bedrock client using model: %s", model_id)
    try:
        bedrock_credentials = get_bedrock_credentials()
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            **bedrock_credentials
        )
        logger.info("Bedrock client initialized successfully")

        return bedrock
    except Exception as e:
        logger.exception("Failed to initialize Bedrock client")
        raise

def invoke_claude(prompt: str, temperature: float = 0, max_tokens: int = maxOutputTokens,
                  top_p: float = 0, system_prompts: Optional[list] = None,
                 model_id: str = modelId) -> str:
    """
    Invoke Claude via AWS Bedrock with a single prompt.
    """
    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]
    return invoke_claude_messages(conversation, temperature, max_tokens, top_p, 
                                  system_prompts = system_prompts, model_id = model_id)

def invoke_claude_messages(messages: list, temperature: float = 0, max_tokens: int = maxOutputTokens,
                           top_p: float = 0.99, system_prompts: Optional[list] = None,
                           prompt_id: str = "promptid123", 
                           useGuardrails: bool = useGuardrails,
                           model_id: str = modelId ) -> Dict[str, Any]:
    """
    Invoke Claude via AWS Bedrock with a list of messages.
    Each message should be a dict with 'role' and 'content'.
    """
    try:
        start_time = time.time()

        logger.info(f"Starting Bedrock Invocation..")
        bedrock = get_bedrock_client(model_id)          

        # Build base arguments
        kwargs = {
            "modelId": model_id,
            "messages": messages,
            "system": system_prompts if system_prompts else [],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": top_p
            }
        }

        # Build guardrail config
        # Add guardrailConfig only if enabled
        if useGuardrails:
            logger.info(f"Using guardrail: {guardrailIdentifier}: v{guardrailVersion}")
            kwargs["guardrailConfig"] = {
                "guardrailIdentifier": guardrailIdentifier,
                "guardrailVersion": guardrailVersion,
                "trace": guardrailTrace
            }

        # Call the API
        response = bedrock.converse(**kwargs)

        # Check if stop reaons if response intervened
        stop_reason = response.get("stopReason", "")
        action_reason = response.get("actionReason", "").lower()
        trace = response.get("trace", {})  # always extract trace
        
        guardrail_action = None

        # If stop reason is because of token limit
        if stop_reason == "max_tokens":
            logger.error(f"Response stopped due to max token limit for prompt: {prompt_id}")
            return {
                "response": "Response stopped: maximum token limit reached. Try reducing prompt size or starting a new chat.",
                "trace": trace,
                "guardrail_action": "bedrock_max_tokens_limit"
            }
        
        # If stop reason is because of guardrails
        if stop_reason == "guardrail_intervened":
            logger.info(f"Guardrail trace: {json.dumps(trace.get('guardrail', {}), indent=2)}")

            if "blocked" in action_reason:
                    logger.error(f"Guardrail blocked content for prompt {prompt_id}")        
                    # Return structured error response
                    return {"response":"Response is blocked by safety guardrails. Please try again with a different prompt.",
                            "trace": trace,
                            "guardrail_action": "blocked"
                            }
            else:
                logger.info(f"Guardrail masked content but allowed response for prompt {prompt_id}")
                guardrail_action = "masked"
        
        # Log time
        end_time = time.time()
        response_time = end_time - start_time
        logger.info(f"Bedrock Invocation Response Time: {response_time:.2f}s.")

        # Log full Bedrock response for inspection/logging
        try:
            bedrock_json = persist_bedrock_response(response, prompt_id)
            logger.info(f"Raw Bedrock output json saved at {bedrock_json}")
        except Exception as e:
                logger.warning(f"Failed to persist Bedrock raw output: {str(e)}")

        content = response["output"]["message"]["content"]

        # Temporary debug
        if isinstance(content, str):
            logger.info("NOTICE: Bedrock returned RAW string instead of parsed JSON")
        else:
            logger.info("NOTICE: Bedrock returned JSON dict")

        if isinstance(content, list) and len(content) > 0:
            response_text = content[0].get("text", "") # Nuclear option: Add clean_response_test function
        elif isinstance(content, dict):
            response_text = content.get("text", "") # Nuclear option: Add clean_response_test function
        elif isinstance(content, str):
            response_text = content
        
        # Handle empty response with single retry
        if not response_text:
            logger.info("Bedrock returned empty content. Retrying once...")
            try:
                response = bedrock.converse(**kwargs)
                content = response["output"]["message"]["content"]
                
                if isinstance(content, list) and len(content) > 0:
                    response_text = content[0].get("text", "")
                elif isinstance(content, dict):
                    response_text = content.get("text", "")
                elif isinstance(content, str):
                    response_text = content
                
                if not response_text:
                    response_text = "Bedrock did not return any response text. Please try again."
            except Exception as e:
                logger.error(f"Retry failed: {str(e)}")
                response_text = "Bedrock did not return any response text. Please try again."

        # Always return both response and trace
        return {"response": response_text, "trace": trace, "guardrail_action": guardrail_action}  

    
    except ClientError as e:
        logger.error("AWS ClientError during Claude invocation: %s", e.response['Error']['Message'])
        #return {"error": f"ClientError: {e.response['Error']['Message']}"}
        return {"response": f"AWS Bedrock did not respond. Please retry with a different prompt. Details: ClientError: {e.response['Error']['Message']}"}
    except BotoCoreError as e:
        logger.error("BotoCoreError during Claude invocation: %s", str(e))
        #return {"error": f"BotoCoreError: {str(e)}"}
        return {"response": f"AWS Bedrock did not respond. Please retry with a different prompt. Details: BotoCoreError: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error during Claude invocation")
        #return {"error": f"Error invoking Claude: {str(e)}"}
        return {"response": f"AWS Bedrock did not respond. Please retry with a different prompt. Details: ClaudeError: {str(e)}"}


# Example usage
if __name__ == "__main__":
    # Test System prompt (Optional)
    test_system_prompts = [
        {"text": "You are a cat. Always respond like one!"}
    ]

    # Test simple query
    test_messages = [
        {
            "role": "user",
            "content": [{"text": "Tell me a joke about cloud computing."}]
        }
    ]
    result = invoke_claude_messages(test_messages, system_prompts=test_system_prompts) # system_prompt is optional
    print("Claude says:", result)
    
