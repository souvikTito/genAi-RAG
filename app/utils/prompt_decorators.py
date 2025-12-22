"""
Prompt decorator functions for dynamic prompt enhancement.
Works alongside system_prompts.json for flexible prompt building.
"""

from typing import Optional
from app.utils.util import logger

def content_generation_style_decorator(base_prompt: str, style: str = "normal") -> str:
    """
    Decorate content generation prompts with style variations.
    
    Args:
        base_prompt: Base prompt from system_prompts.json
        style: One of 'normal', 'concise', 'explanatory', 'formal'
        
    Returns:
        Enhanced prompt with style instructions
    """
    style_instructions = {
        "normal": """
        Use a natural, balanced tone. Avoid extremes in formality or casualness.
        Guidelines:
        - Maintain clarity and flow
        - Use everyday language unless technical terms are required
        - Keep the tone neutral and informative
        """,

        "concise": """
        Keep the content brief and to the point.
        Guidelines:
        - Use short, direct sentences
        - Avoid unnecessary elaboration
        - Prefer bullet points or lists when possible
        """,

        "explanatory": """
        Explain concepts clearly with examples or analogies.
        Guidelines:
        - Assume the reader is unfamiliar with the topic
        - Define technical terms
        - Use analogies or examples to aid understanding
        """,

        "formal": """
        Use a professional and formal tone.
        Guidelines:
        - Avoid contractions and casual phrases
        - Use precise, respectful language
        - Maintain grammatical correctness
        """
    }

    enhanced_prompt = base_prompt
    instruction = style_instructions.get(style, style_instructions["normal"])
    enhanced_prompt += f"\n\nCONTENT GENERATION STYLE:\n{instruction.strip()}"

    enhanced_prompt += """
    Structure the CONTENT with the below sections and stucture:
    1. Title (within 12 words)
    2. Introduction (within 50 words)
    3. Main Content (within 500 words)
    4. Summary (within 100 words)
    """

    logger.debug(f"Applied content generation style: {style}")
    return enhanced_prompt

def code_review_decorator(base_prompt: str, 
                         focus: str = "comprehensive", # can have a user input for security, performance etc
                         language: Optional[str] = None,   # can have a user input for code language
                         framework: Optional[str] = None) -> str: # can have an input for specific framework
    """
    Decorate code review prompts with focus areas and parameters.
    
    Args:
        base_prompt: Base prompt from system_prompts.json
        focus: Review focus area - 'comprehensive', 'security', 'performance', 
               'maintainability', 'bugs', 'style', 'bestPractices'
        language: Programming language (e.g., 'Python', 'JavaScript', 'Java')
        framework: Framework being used (e.g., 'React', 'Django', 'Spring')
        
    Returns:
        Enhanced prompt with review instructions
    """
    
    # Focus area instructions
    focus_instructions = {
        "comprehensive": """
            Evaluate the code across all dimensions: 
            1. CORRECTNESS: Logic errors, edge cases, potential bugs
            2. SECURITY: Vulnerabilities, injection risks, data exposure
            3. PERFORMANCE: Algorithm efficiency, memory usage, bottlenecks
            4. MAINTAINABILITY: Code clarity, documentation, modularity
            5. STYLE: Naming conventions, formatting, code organization
            6. BEST PRACTICES: Design patterns, language idioms, standards compliance
        """
        ,
        
        "security": """
            Focus on security vulnerabilities:
            - Input validation and sanitization issues
            - SQL/NoSQL injection vulnerabilities
            - Cross-site scripting (XSS) risks
            - Authentication and authorization flaws
            - Sensitive data exposure
            - Insecure dependencies or configurations
            - Cryptographic weaknesses
        """,
        
        "performance": """
            Focus on performance optimization:
            - Algorithm complexity (time and space)
            - Inefficient loops or recursive calls
            - Database query optimization
            - Memory leaks and resource management
            - Caching opportunities
            - Network call efficiency
            - Concurrency and parallelization potential
        """,
        
        "maintainability": """
            Focus on code maintainability:
            - Code readability and clarity
            - Function/method size and complexity
            - DRY principle violations (code duplication)
            - SOLID principles adherence
            - Documentation quality
            - Error handling and logging
            - Test coverage and testability
        """,
        
        "bugs": """
            Focus on identifying bugs and logical errors:
            - Null/undefined reference errors
            - Off-by-one errors and boundary conditions
            - Race conditions and concurrency issues
            - Type mismatches and casting errors
            - Exception handling gaps
            - Resource leaks (file handles, connections)
            - Logic flaws in conditional statements
        """,
        
        "style": """
            Focus on code style and conventions:
            - Naming conventions (variables, functions, classes)
            - Code formatting and indentation
            - Comment quality and placement
            - Import/dependency organization
            - File and module structure
            - Language-specific style guide compliance
        """,
        
        "bestPractices": """
            Focus on best practices and design patterns:
            - Design pattern application
            - Separation of concerns
            - Error handling strategies
            - Configuration management
            - Dependency injection
            - API design principles
            - Framework-specific best practices
        """
    }
    
    
    # Build the enhanced prompt
    enhanced_prompt = base_prompt
    
    # Add focus area
    focus_instruction = focus_instructions.get(focus, focus_instructions["comprehensive"])
    #enhanced_prompt += f"\n\nCODE REVIEW FOCUS:\n{focus_instruction.strip()}"
    
     
    # Add language-specific context (if included in the future)
    language = ["Python", "Java", "JavaScript", "TypeScript", "C#", "SQL", "Go", "Bash/Shell", "C++", "Rust", "Node.js", "React", "HTML", "CSS"]
    if language:
        languages_str = ", ".join(language)
        enhanced_prompt += f"\n\nLANGUAGE CONTEXT: The code could be written in the following languages: {languages_str}. Apply Programming specific best practices and idioms."
    
    if framework:
        enhanced_prompt += f"\n\nFRAMEWORK CONTEXT: The code uses the {framework} framework. Consider framework-specific patterns and conventions."
    
    # Add output format instructions
    enhanced_prompt +="""
    Structure the Code Review as a single response with the below sections and stucture:
    • Code Review Summary (within 50 words)
    • Correctness (within 30 words)
    • Readability & Maintainability (within 30 words)
    • Standardization (within 30 words)
    • Security (within 30 words)
    • Performance (within 30 words)
    • Improved Version of the Code (stay within 500 tokens)

    """
    
    logger.info(f"Applied code review decorator: focus={focus}")
    
    return enhanced_prompt

def text_summarisation_decorator(base_prompt: str, summary_style: str = "normal") -> str:
    """
    Decorate text summarisation prompts with style variations.
    
    Args:
        base_prompt: Base prompt from system_prompts.json,
        summary_style: One of 'normal', 'concise' etc
        
    Returns:
        Enhanced prompt with style instructions
    """
    style_instruction = f"""SUMMARY STYLE: Use a {summary_style} style. Summarize the following text with a focus on the following standards:
        1. Factual Accuracy
        2. Clarity & Coherence
        3. Brevity or Completeness
        4. Tone Consistency
        5. Audience Appropriateness
        
        OUTPUT FORMAT:
        Structure the text summary as a single response with below sections within the summary.
        1. Summary (within 200 words)   
        2. Key Points (within 80 words)
        3. Tone & Style Notes (within 50 words)
        4. Compliance with Standards (within 50 words)
        5. Suggestions for Improvement (if applicable) (within 50 words)
        """ 

    logger.debug(f"Applied style decorator: {summary_style}")
    return f"{base_prompt} {style_instruction}"


def doc_comparison_decorator(base_prompt: str, comparison_type: str = "all") -> str:
    """
    Decorate document comparison prompts with focus areas.
    Works in conjunction with output_schema.json for structured output.
    
    Args:
        base_prompt: Base prompt from system_prompts.json
        comparison_type: One of 'all', 'additions', 'deletions', 'modifications', 'structural'
        
    Returns:
        Enhanced prompt with focus instructions
    """
    
    # Define focus instructions
    focus_instructions = {
        "all": """
            Perform a comprehensive comparison covering all aspects.
            Prioritize the following standards: 
            - Relevance of Comparison
            - Clarity & Structure
            - Completeness of Coverage
            - Tone Consistence
            - Contextual Accuracy
            - Source Attribution
        """,
        
        "additions": """
            Focus primarily on new content in the second document.
        
        """,
        
        "deletions": """
            Focus primarily on removed content from the first document.
        """,
        
        "modifications": """
            Focus primarily on changed content between documents.

        """,
        
        "structural": """
            Focus primarily on organizational and structural changes.

        """
    }
    
    enhanced_prompt = base_prompt
    # Get the appropriate instruction
    instruction = focus_instructions.get(comparison_type, focus_instructions["all"])
    enhanced_prompt += f"\n\nDOC COMPARISON FOCUS:\n{instruction.strip()}"

    enhanced_prompt += """\n\n
    RESPONSE STRUCTURE:
    1. **response field**: Structure the analysis with HTML formatting following this outline:
       - Overview of Documents (within 60 words)
       - Key Differences (within 50 words)
       - Tone & Style Comparison (within 20 words)
       - Structural or Thematic Insights (within 20 words)
       - Compliance with Standards (within 20 words)
    
    2. **differences_table field**: CRITICAL - Generate a complete HTML table with Key differences within 500 words (or within top 10 differences only).
        Required format - use standard HTML table structure with these exact columns:
        Document | Type | Location | Description | Importance
        
        Example:
        <table><thead><tr><th>Document</th><th>Type</th><th>Location</th><th>Description</th><th>Importance</th></tr></thead><tbody><tr><td>document1</td><td>addition</td><td>Section 3.2: Payment Terms</td><td>Added new clause regarding late payment penalties</td><td>high</td></tr></tbody></table>
   
        Requirements:
        - Generate as a single line HTML string without line breaks or extra whitespace
        - Include every difference as a separate tr row within the body
        - Type must be exactly one of: addition, deletion, modification
        - Importance must be exactly one of: high, medium, low
        - Use plain text only in td elements - avoid special characters, quotes, or HTML entities
        - Keep descriptions concise and simple to avoid encoding issues
    """

    logger.info(f"Applied document comparison decorator: {comparison_type}")
    return enhanced_prompt

def qna_decorator(base_prompt: str, qna_type: str = "standard") -> str:
    """
    Decorate Q&A prompts with response type variations.
    
    Args:
        base_prompt: Base prompt from system_prompts.json
        qna_type: One of 'standard', 'brief', 'detailed', 'educational', 'technical'
        
    Returns:
        Enhanced prompt with Q&A instructions
    """
    
    # Define different Q&A types
    qna_instructions = {
            "standard": """
        Respond to the user's question clearly and accurately.
        Prioritize the following standards:
        - Factual Accuracy
        - Relevance
        - Clarity & Structure
        - Completeness
        - Tone Appropriateness
        - Source Attribution
        Tone: Professional and informative.
        """,

        "brief": """
        Respond concisely in 2–3 sentences. Focus only on the essential information.

        Tone: Direct and minimal.
        """,
        
        "educational": """
        Explain the topic clearly as if teaching a beginner. Use analogies and define key terms.

        Tone: Friendly and instructive.
        """,

        "technical": """
        Provide a precise, expert-level answer. Include metrics, standards, and implementation details.

        Tone: Formal and domain-specific.
        """
        }
    
    enhanced_prompt = base_prompt
    # Get the appropriate instruction
    instruction = qna_instructions.get(qna_type, qna_instructions["standard"])
    enhanced_prompt += f"\n\nQNA FOCUS:\n{instruction.strip()}"

    enhanced_prompt += """\n\n Output FORMAT:
    Structure the text as a single response with the below sections and structure:
    1. Answer (within 200 words)
    2. Supporting Details (within 100 words)
    3. Reference to Document (if applicable) (within 50 words)
    4. Compliance with Standards (within 20 words)
    5. Suggestions for Further Reading or Clarification (within 50 words)
    """
    logger.info(f"Applied Q&A decorator: {qna_type}")

    return enhanced_prompt

def search_decorator(base_prompt: str, search_type: str = "standard") -> str:
    """
    Decorate search prompts with response type variations.
    
    Args:
        base_prompt: Base prompt from system_prompts.json
        search_type: One of 'standard', 'focused', 'exploratory', 'comparative', 'investigative'
        
    Returns:
        Enhanced prompt with search instructions
    """
    
    search_instructions = {
        "standard": """
            Perform a general-purpose search to answer the user's query using ONLY the context provided. If there is no relevant context for the search query, please mention that before responding.
            
            Guidelines:
            - Prioritize factual accuracy and relevance
            - Use clear, direct language
            - Summarize key findings from credible sources
            - Include citations or references when appropriate
            - Avoid speculation or unsupported claims
        """,
        
        "focused": """
            Perform a targeted search to extract specific information requested by the user.
            
            Guidelines:
            - Focus only on the exact question or topic
            - Avoid general background unless necessary
            - Use bullet points for clarity
            - Include precise data, names, or figures
        """,
        
        "exploratory": """
            Perform a broad search to explore multiple angles or perspectives on the topic.
            Guidelines:
            - Cover different viewpoints or interpretations
            - Include historical, cultural, or technical context
            - Highlight emerging trends or debates
            - Use section headers to organize content
        """,
        
        "investigative": """
            Perform a deep-dive search to uncover underlying causes, implications, or hidden details. 
            Guidelines:
            - Go beyond surface-level answers
            - Investigate root causes, motivations, or consequences
            - Use data, quotes, or expert opinions
            - Highlight gaps or uncertainties
        """
    }
    
    enhanced_prompt = base_prompt
    instruction = search_instructions.get(search_type, search_instructions["standard"])
    enhanced_prompt += f"\n\nSEARCH FOCUS:\n{instruction.strip()}"

    enhanced_prompt += """\n\n Output FORMAT:
    Structure the text as a single response with the below sections and stucture:
    1. Search Results (within 200 words)
    2. Contextual Explanation (within 100 words)
    3. Source References (within 80 words)
    4. Compliance with Standards (within 20 words)
    5. Suggestions for Further Exploration (within 50 words)
    """

    logger.info(f"Applied Search decorator: {search_type}")

    return enhanced_prompt
    
    




