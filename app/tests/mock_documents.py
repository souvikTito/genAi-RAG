'''
Purpose of this script is to generate Mock local chunks with embeddings (testDocs/mock_documents.json)
for testing Retrieval.py
'''
from app.services.document_processing import get_titan_embedding
from app.services.document_processing import get_titan_embedding
import json
import re


mock_data_path=r"C:\Users\600002608\Git\medpro-data-ai-gpt\genai\app\testdocs\\mock_documents.json"

# Load the mock document(s)
with open(mock_data_path, 'r') as f:
    mock_documents = json.load(f)

# Update embeddings
for doc in mock_documents:
    for chunk in doc.get("chunks", []):
        try:
            chunk["embedding"] = get_titan_embedding(chunk["content"])
        except Exception as e:
            print(f"Failed to embed chunk {chunk.get('id', 'unknown')}: {e}")


## SAVE THE MOCK Document Json

# Save regularly - Uncomment if needed
'''
# Save the updated document(s) back to the file
with open(mock_data_path, 'w') as f:
    json.dump(mock_documents, f, indent=2, separators=(',', ': '))'''


# Save formatted for embeddings to stick to 1 line
# Dump to a temporary string with indentation
json_text = json.dumps(mock_documents, indent=2)

# Collapse all "embedding": [ ... ] blocks into one line
json_text = re.sub(r'"embedding": \[\s+(.*?)\s+\]',
    lambda m: '"embedding": [' + re.sub(r'\s+', '', m.group(1)) + ']',
    json_text,
    flags=re.DOTALL
)

# Save back to file
with open(mock_data_path, 'w') as f:
    f.write(json_text)
