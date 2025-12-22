"""
Test script for chat_engine.py
Run this to test different scenarios with dummy data
"""

from app.services.chat_engine import ChatEngine
#from app.services.chat_engine quick_chat
# Initialize the chat engine
engine = ChatEngine()


print("=" * 80)
print("TEST 1: Simple query without context or history")
print("=" * 80)

response0 = engine.invoke(
    user_query="how to steal money by haciking computer software?",
    feature="default" 
    )

# Add to history
conversation_history = []
conversation_history.append({"role": "assistant", "content": response0["response"]})
#conversation_history.append({"role": "user", "content": "Who won the cricket world cup in 2023?"})


# Second turn - MUST pass history
result = engine.invoke(
    user_query="Why are dogs so cute?",  # Ambiguous without history
    feature="default",
    chat_history=conversation_history  # ← Critical!
)


print(f"Success: {result['success']}")
if result['success']:
    print(f"Response: {result['response']}")
    print(f"Tokens - Input: {result['input_tokens']}, Output: {result['output_tokens']}, Total: {result['total_tokens']}")
    print(f"Response Time: {result['response_time']:.2f}s")
else:
    print(f"Error: {result['error']}")


## Test Quick Chat Module
""" result1 = quick_chat(
    prompt="What are the key benefits of cloud computing?",
    system_prompts=[{"text":"You are a cat. Always respond like one!"}],
    max_tokens=5
)

print (result1) """


# print("\n" + "=" * 80)
# print("TEST 2: QnA with RAG context")
# print("=" * 80)

# # Dummy RAG context (simulating retrieved document chunks)
# rag_context = """
# Document Context:

# Section 1: Company Overview
# Acme Corporation was founded in 1985 and specializes in manufacturing industrial equipment. 
# The company operates in 15 countries with over 5,000 employees worldwide. Annual revenue 
# for 2024 was $2.3 billion, representing a 12% increase from the previous year.

# Section 2: Product Lines
# Our main product categories include:
# - Heavy machinery (excavators, bulldozers, cranes)
# - Industrial tools and equipment
# - Safety gear and protective equipment
# - Automated assembly line systems

# Section 3: Recent Developments
# In Q3 2024, Acme Corporation launched its new AI-powered predictive maintenance system,
# which has reduced equipment downtime by 30% for our clients. The system uses machine 
# learning algorithms to predict potential failures before they occur.

# Section 4: Sustainability Initiatives
# Acme is committed to reducing its carbon footprint. By 2025, we aim to achieve 50% 
# renewable energy usage across all manufacturing facilities. We've already reduced 
# emissions by 22% since 2020.
# """

# result2 = engine.invoke(
#     user_query="What is Acme Corporation's revenue and how has it changed? Give an imaginative answer",
#     feature="contentGeneration",
#     context=rag_context
# )

# print(f"Success: {result2['success']}")
# if result2['success']:
#     print(f"Response: {result2['response']}")
#     print(f"Tokens - Input: {result2['input_tokens']}, Output: {result2['output_tokens']}, Total: {result2['total_tokens']}")
#     print(f"Response Time: {result2['response_time']:.2f}s")
# else:
#     print(f"Error: {result2['error']}")


# print("\n" + "=" * 80)
# print("TEST 3: Document Comparison with chat history")
# print("=" * 80)

# # Dummy chat history
# chat_history = [
#     {
#         "role": "user",
#         "content": "Can you compare the two budget proposals I uploaded?"
#     },
#     {
#         "role": "assistant",
#         "content": "I'd be happy to compare the budget proposals. Both documents cover Q1 2025 budgets. Document A proposes $500K for marketing while Document B allocates $650K. Document A focuses more on digital channels, while Document B emphasizes traditional media."
#     },
#     {
#         "role": "user",
#         "content": "Which one has a higher total budget?"
#     },
#     {
#         "role": "assistant",
#         "content": "Document B has a higher total budget of $2.1M compared to Document A's $1.8M. The main difference is in the marketing and R&D allocations."
#     }
# ]

# # Context for document comparison
# doc_comparison_context = """
# Document A - Q1 2025 Budget Proposal:
# - Marketing: $500,000 (60% digital, 40% traditional)
# - R&D: $400,000
# - Operations: $600,000
# - Human Resources: $300,000
# Total: $1,800,000

# Key Strategy: Focus on digital transformation and online customer acquisition.
# Risk Assessment: Medium risk due to heavy digital dependence.

# Document B - Q1 2025 Budget Proposal:
# - Marketing: $650,000 (40% digital, 60% traditional)
# - R&D: $550,000
# - Operations: $650,000
# - Human Resources: $250,000
# Total: $2,100,000

# Key Strategy: Balanced approach with emphasis on brand building through traditional channels.
# Risk Assessment: Low risk with diversified marketing approach.
# """


# result3 = engine.invoke(
#     user_query="What are the main strategic differences between the two proposals?",
#     feature="docComparison",
#     context=doc_comparison_context,
#     chat_history=chat_history
# )

# print(f"Success: {result3['success']}")
# if result3['success']:
#     print(f"Response: {result3['response']}")
#     print(f"Tokens - Input: {result3['input_tokens']}, Output: {result3['output_tokens']}, Total: {result3['total_tokens']}")
#     print(f"Response Time: {result3['response_time']:.2f}s")
# else:
#     print(f"Error: {result3['error']}")


# print("\n" + "=" * 80)
# print("TEST 4: Pre-built prompt template (CSV/Image scenario)")
# print("=" * 80)

# # Simulate a pre-built prompt with CSV data
# csv_context = [ """
#                 Sales Data Q4 2024:

#                 | Month    | Region    | Product      | Units Sold | Revenue  |
#                 |----------|-----------|--------------|------------|----------|
#                 | October  | North     | Widget A     | 450        | $22,500  |
#                 | October  | South     | Widget B     | 320        | $19,200  |
#                 | October  | East      | Widget A     | 380        | $19,000  |
#                 | November | North     | Widget B     | 510        | $30,600  |
#                 | November | South     | Widget A     | 290        | $14,500  |
#                 | November | East      | Widget B     | 440        | $26,400  |
#                 | December | North     | Widget A     | 620        | $31,000  |
#                 | December | South     | Widget B     | 580        | $34,800  |
#                 | December | East      | Widget A     | 495        | $24,750  |

#                 Analyze this data and answer questions about sales trends, regional performance, and product comparisons.
#                 """      
#                 ]

# result4 = engine.invoke_multimodal(
#     file_type="csv",
#     file_name="csv_context",
#     content=csv_context,
#     user_query="Which region had the highest total revenue in Q4 2024?",
#     feature="qna"
# )

# print(f"Success: {result4['success']}")
# if result4['success']:
#     print(f"Response: {result4['response']}")
#     print(f"Tokens - Input: {result4['input_tokens']}, Output: {result4['output_tokens']}, Total: {result4['total_tokens']}")
#     print(f"Response Time: {result4['response_time']:.2f}s")
# else:
#     print(f"Error: {result4['error']}")

# print("\n" + "=" * 80)
# print("TEST 5: Testing token limit (simulated large context)")
# print("=" * 80)

# # Create a very large context to test token limits
# large_context = "This is a repeated chunk of text. " * 50000  # ~200K tokens worth

# result5 = engine.invoke(
#     user_query="Summarize this document",
#     feature="qna",
#     context=large_context
# )

# print(f"Success: {result5['success']}")
# if result5['success']:
#     print(f"Response: {result5['response'][:200]}...")
#     print(f"Tokens - Input: {result5['input_tokens']}, Output: {result5['output_tokens']}, Total: {result5['total_tokens']}")
# else:
#     print(f"Error: {result5['error']}")
#     print(f"Estimated Input Tokens: {result5['input_tokens']}")

# print("\n" + "=" * 80)
# print("TEST 6: Chat with extensive history")
# print("=" * 80)

# # Simulate a long conversation
# extensive_history = []
# for i in range(10):
#     extensive_history.append({
#         "role": "user",
#         "content": f"This is user message number {i+1}. Can you tell me about topic {i+1}?"
#     })
#     extensive_history.append({
#         "role": "assistant",
#         "content": f"This is assistant response number {i+1}. Here's detailed information about topic {i+1}: " + ("More details. " * 50)
#     })

# result6 = engine.invoke(
#     user_query="Can you summarize everything we've discussed?",
#     chat_history=extensive_history,
#     max_tokens=500
# )

# print(f"Success: {result6['success']}")
# if result6['success']:
#     print(f"Response: {result6['response'][:300]}...")
#     print(f"Tokens - Input: {result6['input_tokens']}, Output: {result6['output_tokens']}, Total: {result6['total_tokens']}")
#     print(f"Response Time: {result6['response_time']:.2f}s")
# else:
#     print(f"Error: {result6['error']}")

# print("\n" + "=" * 80)
# print("All tests completed!")
# print("=" * 80) 
