"""
Main chat service for handling different GenAI features and core chat functionality.
Manages prompt templates, message formatting, and Bedrock invocations.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.helpers import truncate_content
from app.utils.util import logger, modelConfig, modelType, globalPrompt, maxOutputTokens, format_rows_as_table
from app.models.bedrock_client import invoke_claude_messages, invoke_claude
from app.utils.prompt_decorators import (content_generation_style_decorator, code_review_decorator,
                                          text_summarisation_decorator, doc_comparison_decorator,
                                          qna_decorator, search_decorator)


class ChatEngine:
    """
    Main chat engine for handling different GenAI features and core chat functionality.
    Manages prompt templates, message formatting, and Bedrock invocations.
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize the chat engine with prompt templates.
        
        Args:
            prompts_dir: Directory containing system_prompts.json and output_schema.json
        """
        self.prompts_dir = Path(prompts_dir)
        self.system_prompts = self._load_json("system_prompts.json")
        self.output_schemas = self._load_json("output_schema.json")
        self.max_input_tokens = modelConfig[modelType]["max_tokens"]

        logger.info(f"ChatEngine initialized successfully. Max input tokens: {self.max_input_tokens}")
    
    def _load_json(self, filename: str) -> dict:
        """Load JSON configuration file relative to this file's location."""
        base_dir = Path(__file__).resolve().parent.parent 
        prompts_dir = base_dir / "prompts"
        filepath = prompts_dir / filename    
        try:    
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}. Using empty dict.")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing {filepath}: {e}")
            return {}
    
    def _get_system_prompt(self, feature: Optional[str] = None,
                           **kwargs) -> str:
        """
        Get system prompt for a specific feature or default.
        
        Args:
            feature: GenAI feature name (e.g., 'docComparison', 'qna') or None for default
            style: Style modifier for content generation
            focus: optional input for code review
            
        Returns:
            Enhached System prompt string
        """
        if feature and feature in self.system_prompts:
            logger.debug(f"Using system prompt for feature: {feature}")
            base_prompt = self.system_prompts[feature]

        else:
            logger.debug("Using default system prompt")
            base_prompt = self.system_prompts.get("default", "")

        # Apply feature-specific decorators
        if feature == "contentGeneration":
            base_prompt = content_generation_style_decorator(
                base_prompt,
                style=kwargs.get("style", "normal")
            )

        if feature == "codeReview":
            base_prompt = code_review_decorator(
                base_prompt,
                focus=kwargs.get('focus', 'comprehensive')
            )
            
         
        if feature == "textSummarisation":
            base_prompt =  text_summarisation_decorator(
                base_prompt,
                summary_style=kwargs.get('summary_style', 'normal')
            )

        if feature == "docComparison":
            base_prompt = doc_comparison_decorator(
                base_prompt,
                comparison_type=kwargs.get('comparison_type', 'all')
            )

        if feature == "qna":
            base_prompt = qna_decorator(
                base_prompt,
                qna_type=kwargs.get('qna_type', 'standard')
            )

        if feature == "search":
            base_prompt = search_decorator(
                base_prompt,
                search_type=kwargs.get('search_type', 'standard')
            )

        return base_prompt
    
    def _get_output_schema(self, feature: Optional[str] = None) -> Optional[dict]:
        """
        Get output schema for a specific feature.
        
        Args:
            feature: GenAI feature name or None
            
        Returns:
            Output schema dict or None
        """
        if feature and feature in self.output_schemas:
            logger.debug(f"Using output schema for feature: {feature}")
            return self.output_schemas[feature]
        
        default_schema = self.output_schemas.get("default")
        if default_schema:
            logger.debug("Using default output schema")
        return default_schema
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Rough approximation: 1 token ≈ 4 characters
        
        Args:
            text: Text content to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def _check_token_limit(self, 
                          messages: List[Dict],
                          system_prompt: str,
                          context: Optional[str] = None,
                          output_schema: Optional[dict] = None) -> Tuple[bool, int]:
        """
        Check if the complete prompt (messages + system prompt + context + schema) 
        exceeds maximum input token limit.
        
        Args:
            messages: List of formatted messages
            system_prompt: System prompt text
            context: Optional RAG context
            output_schema: Optional output schema
            
        Returns:
            Tuple of (within_limit, estimated_tokens)
        """
        # Calculate tokens for all components
        messages_tokens = 0
        # Estimate tokens from messages (handle binary content)
        for msg in messages:
            for content_item in msg.get("content", []):
                if "text" in content_item:
                    # Count text tokens
                    messages_tokens += self._estimate_tokens(content_item["text"])
                elif "image" in content_item:
                    # Images have fixed token cost in Claude
                    # Approximate: 1 image ≈ 1500-2000 tokens depending on size
                    messages_tokens += 1600


        system_prompt_tokens = self._estimate_tokens(system_prompt)
        
        context_tokens = 0
        if context:
            context_tokens = self._estimate_tokens(context)
        
        schema_tokens = 0
        if output_schema:
            schema_tokens = self._estimate_tokens(json.dumps(output_schema))
        
        # Total estimated tokens
        estimated_tokens = messages_tokens + system_prompt_tokens + context_tokens + schema_tokens + 1000 # 1000 buffer for output tokens
        within_limit = estimated_tokens <= self.max_input_tokens
        
        if not within_limit:
            logger.warning(
                f"Token limit exceeded: {estimated_tokens} > {self.max_input_tokens} "
                f"(messages: {messages_tokens}, system: {system_prompt_tokens}, "
                f"context: {context_tokens}, schema: {schema_tokens})"
            )
        else:
            logger.debug(
                f"Token check passed: {estimated_tokens}/{self.max_input_tokens} "
                f"(messages: {messages_tokens}, system: {system_prompt_tokens}, "
                f"context: {context_tokens}, schema: {schema_tokens})"
            )
        
        return within_limit, estimated_tokens 
    
    def _format_messages(self,
                        user_query: str,
                        system_prompt: str,
                        output_schema: Dict[str,any],
                        chat_history: Optional[List[Dict]] = None,
                        context: Optional[str] = None) -> List[Dict]:
        """
        Format messages for Bedrock converse API.
        
        Args:
            user_query: Current user question
            system_prompt: System prompt to use
            output_schema: Output schema to use
            chat_history: Previous conversation messages
            context: Additional context (e.g., RAG retrieved content)
            
        Returns:
            List of formatted messages
        """
        messages = []
        
        # Build the first user message with system prompt and context
        system_message_parts = [system_prompt]

        # Format output_schema
        schema_block = json.dumps(output_schema["schema"], indent=2)

        # Append output schema to template
        system_message_parts.append(f"{output_schema['output_format']}\n```json\n{schema_block}\n```")

        # Avoid the the triple backtick for Prompt Injection
        #system_message_parts.append(f"{output_schema['output_format']}\nThe expected response format is:\n{schema_block}")


        if context:
            system_message_parts.append(f"\nDOCUMENT CONTEXT:\n{context}")
        
        system_text = "\n\n".join(system_message_parts)
        
        # Add chat history
        if chat_history:
            # If first message is assistant, prepend system text as separate user message
            if chat_history[0].get("role") in ["assistant"]:
                messages.append({
                    "role": "user",
                    "content": [{"text": f"{system_text}\n\n---CONVERSATION HISTORY---\n\n"}]
                })

            for i, msg in enumerate(chat_history):
                role = msg.get("role")
                content = msg.get("content", "")
                
                # Convert 'human' to 'user' if needed
                if role == "human":
                    role = "user"
                
                if role in ["user", "assistant"]:
                    # Handle dict content from guardrail responses
                    if isinstance(content, list):
                        # Content is already a list (from Bedrock format)
                        text_content = content[0].get('text', '') if content else ''
                        
                        # If text is a dict (guardrail response), extract string
                        if isinstance(text_content, dict):
                            text_content = text_content.get('response', 'Previous response unavailable')
                            
                        content = text_content
                    elif isinstance(content, dict):
                        # Content is a dict (guardrail response)
                        content = content.get('response', 'Previous response unavailable')

                    # Truncate content if too long .. update as needed
                    MAX_HISTORICAL_CHARS = 1500
                    if isinstance(content, str) and len(content) > MAX_HISTORICAL_CHARS:
                        #content = content[:MAX_HISTORICAL_CHARS] + "…[truncated]"
                        # Using a more refined helper truncation function
                        content = truncate_content(content, max_chars=MAX_HISTORICAL_CHARS)

                    # Prepend system text to FIRST user message only
                    if i == 0 and role == "user":
                        content = f"{system_text}\n\n---CONVERSATION HISTORY---\n\n{content}"
                    
                    messages.append({
                        "role": role,
                        "content": [{"text": content}]
                    })
    
        # If no history, create first message with system text
        if not messages:
            #json_reminder = "\n\nCRITICAL: Your response must be ONLY a valid JSON. Do not include any text before or after the JSON. Start your response with { and end with }. No preambles, explanations, or additional text."
            json_reminder = ""
            messages.append({
                "role": "user",
                "content": [{"text": system_text + json_reminder}]
            })

        # Add current user query with optional header
        messages.append({
            "role": "user",
            "content": [{"text": f"CURRENT QUESTION:\n{user_query}"}]
        })  

        # Debug
        # Debug - log only first n characters
        messages_str = str(messages)

        # Handle unicode
        messages_str = messages_str.encode('ascii', 'replace').decode()
        
        if len(messages_str) > 6000:
            logger.info(f"Final Prompt Template Created (truncated): \n {messages_str[:6000]}... \n[Total length: {len(messages_str)} characters]")
        else:
            logger.info(f"Final Prompt Template Created: \n {messages_str} \n")
                
        return messages
    
    def _MultimodalPromptBuilder(self, file_type: str, content_list: list[Dict], 
                                file_name: str, user_question: str, 
                                chat_history: Optional[list] = None,
                                system_prompt: Optional[str] = None,
                                output_schema: Optional[dict] = None) -> List[Dict]:
            """
            Build a multimodal prompt template for multiple images/csvs
            
            Args:
                file_type: Type of file ("image" or "csv")
                content_list: List of Multiple File content (bytes for image, string for CSV)
                file_name: Name of the file (without extension)
                user_question: Current user question
                chat_history: List of previous messages in format- [{"role": "user|assistant", "content": "text"}, ...]
                system_prompt: System instructions
                output_schema: Schema definition with 'output_format' and 'schema' keys
                
            Returns:
                List of formatted messages for Bedrock API
            """
            
            messages = []

            # Build system message parts
            system_parts = []
            if system_prompt:
                system_parts.append(system_prompt)
            
            if output_schema:
                schema_block = json.dumps(output_schema["schema"], indent=2)
                system_parts.append(
                    f"{output_schema['output_format']}\n```json\n{schema_block}\n```"
                )
            
            if file_type == "image":
                # Build content parts for ALL images
                content_parts = []
                
                # Add system prompt first (if any)
                if system_parts:
                    content_parts.append({"text": "".join(system_parts)})

                # Add previous chat history if present
                if chat_history:
                    history_text = "\n\n=== CONVERSATION HISTORY ===\n\n"
                    for msg in chat_history:
                        role = "User" if msg.get("role") == "human" else "Assistant"
                        history_text += f"{role}: {msg.get('content', '')}\n\n"
                    content_parts.append({"text": history_text})

                # Build image context header
                image_context = "\n\n=== IMAGE DATA CONTEXT ===\n\n"

                # Add each image with its summary and metadata
                for idx, item in enumerate(content_list, 1):
                    file_name = item['file_name']
                    content = item['content']
                    summary = item.get('summary', '')
                    upload_date = item['upload_date']
                    logger.info(f"Date added for the Image by Chat Engine: {upload_date}")

                    media_type = "png" if file_name.lower().endswith(".png") else "jpeg"
                    
                    # Image Header
                    image_context += f"\n--- Image File {idx}: {file_name} ---\n"
                    image_context += f"Upload Date: {upload_date}\n"

                    # Add summary if available
                    if summary:
                        image_context += f"Summary:\n{summary}\n\n"
                        logger.info(f"Summary added for image {idx}: {summary}...")
                    image_context += f"Image Type: {media_type.upper()}\n\n---\n\n"
                
                # Add the text context first
                content_parts.append({"text": image_context})
                
                # Add all image data
                for idx, item in enumerate(content_list, 1):
                    file_name = item['file_name']
                    content = item['content']
                    media_type = "png" if file_name.lower().endswith(".png") else "jpeg"
                    
                    # Image binary data
                    content_parts.append({ 
                        "image": { 
                            "format": media_type,
                            "source": {"bytes": content} 
                        }
                    })

                # Add user question at the end
                content_parts.append({
                    "text": f"\nUser Question: {user_question}"
                })

                # Add all as one user message
                messages.append({
                    "role": "user",
                    "content": content_parts
                })
                
            elif file_type == "csv":
                # Combine all CSV content
                content_parts = []
                if system_parts:
                    content_parts.append({"text": "".join(system_parts)}) 

                # Add previous chat history if present
                if chat_history:
                    history_text = "\n\n=== CONVERSATION HISTORY ===\n\n"
                    for msg in chat_history:
                        role = "User" if msg.get("role") == "human" else "Assistant"
                        history_text += f"{role}: {msg.get('content', '')}\n\n"
                    content_parts.append({"text": history_text})  
                
                # Build CSV context similar to document retrieval format
                csv_context = "\n\n=== CSV DATA CONTEXT ===\n\n"
                
                for idx, item in enumerate(content_list, 1):
                    file_name = item['file_name']
                    prepared_data = item['content']
                    summary = item.get('summary', '')
                    logger.info(f"Summary added for CSV: {summary}")
                    upload_date = item['upload_date']
                    logger.info(f"Date added for the CSV by Chat Engine: {upload_date}")


                    csv_context += f"\n--- CSV File {idx}: {file_name} ---\n\n"
                    csv_context += f"Upload Date: {upload_date}\n"

                    # Add summary if available (like PDF format)
                    if summary:
                        csv_context += f"Summary:\n{summary}\n\n"
                        
                    # Add metadata
                    columns = prepared_data.get('columns', [])
                    total_rows = prepared_data.get('total_rows', 0)

                    csv_context += f"CSV Structure:\n"
                    csv_context += f"Columns: {', '.join(columns)}\n"
                    csv_context += f"Total Rows in Dataset: {total_rows}\n\n"

                    # Add data based on what we have
                    if 'rows' in prepared_data:
                        # Small dataset - all rows sent
                        csv_context += f"Complete Data ({len(prepared_data['rows'])} rows):\n"
                        csv_context += format_rows_as_table(prepared_data['rows'], columns)
                    else:
                        # Large dataset - sample + relevant
                        csv_context += f"Sample Data (First 50 rows):\n"
                        csv_context += format_rows_as_table(prepared_data.get('sample_rows', []), columns)
                        
                        if prepared_data.get('relevant_rows'):
                            logger.info(f"Adding relevant rows")
                            csv_context += f"\n\nQuery-Relevant Rows ({len(prepared_data['relevant_rows'])} matches):\n"
                            csv_context += format_rows_as_table(prepared_data['relevant_rows'], columns)
                            csv_context += f"\n(Note: {total_rows - 50 - len(prepared_data['relevant_rows'])} additional rows exist but are not shown)\n"
                        else:
                            logger.info(f"No relevant rows found")
                            csv_context += f"\n(Note: {total_rows - 50} additional rows exist but are not shown)\n"

                    csv_context += "\n\n---\n\n"
                
                csv_context += f"\nUser Question: {user_question}\n"
                content_parts.append({"text": csv_context})

                messages.append({
                    "role": "user",
                    "content": content_parts
                })

            else:
                raise ValueError(f"Unsupported file type for multimodal prompt: {file_type}")
            
            # Debug
            messages_str = str(messages)
            if len(messages_str) > 4000:
                logger.info(f"Final Prompt Template Created (truncated): \n {messages_str[:4000]}... \n[Total length: {len(messages_str)} characters]")
            else:
                logger.info(f"Final Prompt Template Created: \n {messages_str} \n")
              
            return messages 

    def invoke(self,
               user_query: str,
               feature: Optional[str] = None,
               genai_params: Optional[Dict[str,any]] = None,
               chat_history: Optional[List[Dict]] = None,
               context: Optional[str] = None,
               temperature: float = 0,
               max_tokens: int = maxOutputTokens,
               top_p: float = 0.99,
               global_prompt: Optional[list] = globalPrompt,
               prompt_id: str = "promptid123") -> Dict:
        """
        Main method to invoke the chat engine.
        
        Args:
            user_query: User's question or message
            feature: GenAI feature to use ('docComparison', 'qna', etc.) or None for default
            genai_params: Dict of feature-specific parameters, e.g.:
                {'style': 'concise', 'tone': 'formal'}    
            chat_history: Previous conversation messages in format - [{"role": "user|assistant", "content": "text"}, ...]
            context: Additional context (e.g., RAG retrieved content)
            temperature: Sampling temperature (default: 0 for deterministic responses)
            max_tokens: Maximum tokens in response (default: 1000)
            top_p: Top-p sampling parameter (default: 0 for deterministic)
            global_prompt: Global level system prompt
            
        Returns:
            Dict containing:
                - success: Boolean indicating if invocation succeeded
                - response: Model's response text (if successful)
                - error: Error message (if failed)
                - input_tokens: Number of input tokens
                - output_tokens: Number of output tokens
                - total_tokens: Total tokens used
                - response_time: Time taken in seconds
        """
        start_time = time.time()
        
        logger.info(f"Invoking Chat engine with: {feature or 'default'}")
        #logger.info(f"Input Prompt from user: {user_query}")  

        # Load GenAI parameters
        if genai_params is None:
            genai_params = {}
        
        logger.info(f"Invoking GenAI feature: {feature or 'default'}, params: {genai_params}")

        # Get appropriate system prompt and schema
        system_prompt = self._get_system_prompt(feature = feature,
                                                **genai_params)  #Unpack genAi params dictionary
        output_schema = self._get_output_schema(feature)
        
        # Debug prompt template and schema
        logger.info(f"Global Level Prompt Used: {global_prompt}")
        logger.info(f"System Prompt Template Used: {system_prompt}")
        logger.info(f"Output Schema Template Used: {output_schema}")

        # Format messages
        messages = self._format_messages(
            user_query=user_query,
            system_prompt=system_prompt,
            output_schema=output_schema,
            chat_history=chat_history,
            context=context
        )
        
        logger.debug(f"Formatted {len(messages)} messages for Bedrock")
        
        # Check token limit before proceeding - includes ALL components
        within_limit, estimated_input_tokens = self._check_token_limit(
            messages=messages,
            system_prompt=system_prompt,
            context=context,
            output_schema=output_schema
        )
        
        if not within_limit:
            error_msg = (f"Input token limit exceeded. Estimated tokens: {estimated_input_tokens}, "
                        f"Maximum allowed: {self.max_input_tokens}. "
                        f"Please reduce chat history or context size.")
            logger.error(error_msg)
            return {
                "success": False,
                "response": "Response stopped: maximum AWS input token limit reached. Try reducing prompt size or starting a new chat.",
                "error": error_msg,
                "input_tokens": estimated_input_tokens,
                "output_tokens": 0,
                "total_tokens": estimated_input_tokens,
                "bedrock_response_time": time.time() - start_time    
            }
        
        # Invoke Bedrock
        response_text = invoke_claude_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            system_prompts=global_prompt,
            prompt_id=prompt_id
        )
        
        response_time = time.time() - start_time
        
        # Estimate output tokens
        response_string = response_text.get("response", "")
        output_tokens = len(response_string) // 4
        total_tokens = estimated_input_tokens + output_tokens
        
        logger.info(f"Chat Engine Response generated in {response_time:.2f}s. Tokens: {total_tokens} ({estimated_input_tokens} in, {output_tokens} out)")
        
        return {
            "success": True,
            "response": response_text,
            "input_tokens": estimated_input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "bedrock_response_time": response_time
        }
    
    def invoke_multimodal(self,
                         file_type: str,
                         content_list: List[dict],
                         file_name: str,
                         user_query: str,
                         feature: Optional[str] = None,
                         genai_params: Optional[Dict[str, any]] = None,
                         chat_history: Optional[List[Dict]] = None,
                         temperature: float = 0,
                         max_tokens: int = maxOutputTokens,
                         top_p: float = 0,
                         global_prompt: Optional[list] = globalPrompt,
                         prompt_id: str = "promptid123") -> Dict:
        """
        Invoke with multimodal content (images or CSV).
        
        Args:
            file_type: Type of file ('image' or 'csv')
            content_list: List of dicts with 'content' and 'file_name' keys
            file_name: Name of the file
            user_query: User's question about the file
            feature: GenAI feature name (optional)
            genai_params: Dict of feature-specific parameters, e.g.:
                {'style': 'concise', 'tone': 'formal'}    
            chat_history: Previous conversation messages in format - [{"role": "user|assistant", "content": "text"}, ...]
            temperature: Sampling temperature (default: 0)
            max_tokens: Maximum tokens in response (default: 1000)
            top_p: Top-p sampling parameter (default: 0)
            global_prompt: Global level system prompt

        Returns:
            Dict with success status, response, and token counts
        """

        start_time = time.time()  
        logger.info(f"Invoking Chat engine with feature: {feature or 'default'}")
        logger.info(f"Invoking Multimodal chat for {file_type} file: {file_name}")
        logger.info(f"Input Prompt from user: {user_query}")  

              
        # Load GenAI parameters
        if genai_params is None:
            genai_params = {}
        
        logger.info(f"Invoking Multimodal Chat Engine with GenAI feature: {feature or 'default'}, params: {genai_params}")

        # Get appropriate system prompt and schema
        system_prompt = self._get_system_prompt(feature,
                                                **genai_params)  # Unpack GenAI params dictionary
        output_schema = self._get_output_schema(feature)
        
        # Debug prompt template and schema
        logger.info(f"Global Level Prompt Used: {global_prompt}")
        logger.info(f"System Prompt Template Used: {system_prompt}")
        logger.info(f"Output Schema Template Used: {output_schema}")

        # Build multimodal prompt
        try:
            messages = self._MultimodalPromptBuilder(
                file_type=file_type,
                content_list=content_list,
                file_name=file_name,
                user_question=user_query,
                chat_history=chat_history,
                system_prompt=system_prompt,
                output_schema=output_schema
            )   
            logger.debug(f"Formatted {len(messages)} messages for Bedrock")
        except ValueError as e:
            logger.error(f"Error building multimodal prompt: {e}")
            return {
                "success": False,
                "error": str(e),
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "response_time": time.time() - start_time
            }
        
        # Get output schema if feature specified
        output_schema = self._get_output_schema(feature)
        
        # Check token limit
        # For multimodal, estimate based on messages only (images have fixed token cost)
        within_limit, estimated_input_tokens = self._check_token_limit(
            messages=messages,
            system_prompt=system_prompt,
            context=None,
            output_schema=output_schema
        )
        
        if not within_limit:
            error_msg = (f"Input token limit exceeded. Estimated tokens: {estimated_input_tokens}, "
                        f"Maximum allowed: {self.max_input_tokens}. "
                        f"Please reduce file size or chat history.")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "input_tokens": estimated_input_tokens,
                "output_tokens": 0,
                "total_tokens": estimated_input_tokens,
                "response_time": time.time() - start_time
            }
        
        # Invoke Bedrock
        response_text = invoke_claude_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            system_prompts=global_prompt,
            prompt_id=prompt_id
        )
        
        response_time = time.time() - start_time
        
        # Estimate output tokens
        output_tokens = len(response_text) // 4
        total_tokens = estimated_input_tokens + output_tokens
        
        logger.info(f"Multimodal response generated in {response_time:.2f}s. Tokens: {total_tokens}")
        
        return {
            "success": True,
            "response": response_text,
            "input_tokens": estimated_input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "bedrock_response_time": response_time  
        }
    
# Convenience function for simple usage
def quick_chat(prompt: str, 
            feature: Optional[str] = None,
            context: Optional[str] = None,
            max_tokens: int = maxOutputTokens,
            temperature: float = 0,
            top_p: float = 0,
            system_prompts: Optional[list] = globalPrompt) -> str:
    """
    Quick chat function for simple use cases.
    
    Args:
        user_query: User's question
        feature: Feature name or None for default
        context: Optional context string
        max_tokens: Maximum response tokens
        
    Returns:
        Response text
    """
    logger.info(f"Invoking Quick Chat Mode")

    result = invoke_claude(
        prompt=prompt,
        system_prompts=system_prompts,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
    )
    return result

if __name__ == "__main__":
    """
    Simple test when running chat_engine.py directly
    Usage: python app.services.chat_engine
    """

    print("--- Test 1: Simple Query ---")
    
    # Initialize engine
    engine = ChatEngine()
    
    # Simple query
    result = engine.invoke(
        user_query="What is machine learning?",
        max_tokens=200
    )
    print(f"Success: {result['success']}")

    if result['success']:
        print(f"Response: {result['response'][:100]}...")
        print(f"Tokens - Input: {result['input_tokens']}, Output: {result['output_tokens']}, Total: {result['total_tokens']}")
        print(f"Response Time: {result['response_time']:.2f}s")
    else:
        print(f"Error: {result['error']}")



    ''' Flow
        invoke() called
            ↓
        _get_system_prompt() → Get right prompt
            ↓
        _get_output_schema() → Get schema (if needed)
            ↓
        _format_messages() → Build message structure
            ↓
        _estimate_tokens() → Count tokens
            ↓
        _check_token_limit() → Verify within limits
            ↓
        invoke_claude_messages() → Call Bedrock
    
    '''
