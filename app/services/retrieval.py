"""
Retrieval module for fetching and ranking document chunks from DynamoDB.
Uses semantic search with Titan embeddings for RAG (Retrieval Augmented Generation).
"""

import json, os
import time
from typing import List, Dict, Optional
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.util import logger, get_mock_data_path
from app.utils.helpers import sanitize_retrieval_query
from app.services.document_processing import get_titan_embedding
from app.models.s3 import read_json_from_s3
#from app.models.dynamodb import dynamoDb

class DocumentRetriever:
    """
    Handles retrieval of relevant document chunks from S3 for RAG.
    """
    
    def __init__(self, table_name: str = None, s3_documents_bucket: str = None, mock_data_path: str = None):
        """
        Initialize the document retriever.
        
        Args:
            s3_bucket: Name of the S3 bucket containing documents (optional if using mock data)
            mock_data_path: Path to JSON file for local testing (optional)
        """

        #self.table_name = table_name
        self.mock_data_path = mock_data_path
        self.mock_data = None
        
        if mock_data_path:
            # Load mock data for local testing
            try:
                with open(mock_data_path, 'r') as f:
                    data = json.load(f)
                self.mock_data = data if isinstance(data, list) else [data]
                logger.info(f"Loaded mock Document data from: {mock_data_path}")
            except Exception as e:
                logger.error(f"Error loading mock data: {e}")
                self.mock_data = []
        else:
            # Initialize DynamoDB connection (IMP: Move this to model and call dynamodb.py model)
            #self.dynamodb = dynamoDb
            #self.table = self.dynamodb.Table(table_name)
  
            self.s3_documents_bucket= s3_documents_bucket or os.getenv("S3_DOCUMENTS_BUCKET") 
            logger.info(f"S3 DocumentRetriever initialized for bucket: {self.s3_documents_bucket}")
    
    def _fetch_document(self, document_id: str) -> Optional[Dict]:
        """
        Fetch a document from DynamoDB or mock data.    
        
        Args:
            document_id: Unique identifier for the document (documentId)
            
        Returns:
            Document dictionary with chunks and metadata
        """
        try:
            if self.mock_data:
                # Search in mock data
                logger.info(f"Looking for {document_id} in mock_data")
                for doc in self.mock_data:
                    if doc.get('documentId') == document_id:
                        logger.info(f"Found document in mock data: {document_id}")
                        return doc
                logger.warning(f"Document not found in mock data: {document_id}")
                return None
            else:
                # Fetch from DynamoDB
                #response = self.table.get_item(Key={'documentId': document_id})
                
                #if 'Item' in response:
                #    logger.info(f"Retrieved document from DynamoDB: {document_id}")
                #    return response['Item']
                #else:
                #    logger.warning(f"Document not found in DynamoDB: {document_id}")
                #    return None

                # Updating from s3
                s3_key = f"documents/{document_id}.json"
                bucket_name = self.s3_documents_bucket
                document = read_json_from_s3(bucket_name, s3_key)
                if document:
                    logger.info(f"Retrieved document from S3: {document_id}")
                    return document
                else:
                    logger.warning(f"Document not found in S3: {document_id}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching document from s3: {e}")
            return None
    
    def _rank_chunks_by_similarity(self, 
                                   query_embedding: List[float], 
                                   chunks: List[Dict]) -> List[Dict]:
        """
        Rank chunks by cosine similarity to query embedding.
        
        Args:
            query_embedding: Query embedding vector
            chunks: List of chunk dictionaries with embeddings
            
        Returns:
            List of chunks sorted by similarity (highest first)
        """
        similarities = []
        
        for chunk in chunks:
            # Get embedding from chunk
            chunk_embedding = chunk.get('embedding')
            
            if not chunk_embedding:
                logger.warning(f"Chunk {chunk.get('id', 'unknown')} missing embedding")
                continue
            
            # Calculate cosine similarity
            similarity = cosine_similarity([query_embedding], [chunk_embedding])[0][0]
            
            logger.info(f"Chunk ID: {chunk.get('id')} | Similarity: {similarity:.4f} | Source: {chunk.get('source', 'unknown')}")

            similarities.append({
                'id': chunk.get('id'),
                'content': chunk.get('content', ''),
                'similarity': similarity,
                'source': chunk.get('source', ''),
                'file_type': chunk.get('file_type', '')
            })
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        logger.info(f"Ranked {len(similarities)} chunks by similarity")

        return similarities
    
    def retrieve(self, 
                document_id: str, 
                user_query: str, 
                top_k: int = 10,  # maximum number of chunks that can be retrieved
                similarity_threshold: float = 0.1,
                include_summary: bool = True) -> str:
        """
        Retrieve and format relevant chunks for a user query.
        
        Args:
            document_id: Document ID (documentId in DynamoDB)
            user_query: User's question/query
            top_k: Number of top chunks to return
            similarity_threshold: Minimum similarity score (0-1)
            include_summary: Include document summary as introduction
            
        Returns:
            Formatted context string ready for ChatEngine.invoke()
        """
        retrieval_start_time = time.time()
        logger.info(f"Starting retrieval for document: {document_id}, query: '{user_query[:600]}...'")
        logger.info(f"Embedding Similarity matching threshold: {similarity_threshold}, Max Chunks: {top_k}")
        
        # Step 1: Fetch document
        document = self._fetch_document(document_id)
        
        if not document:
            logger.error(f"Document not found: {document_id}")
            return f"Error: Document {document_id} not found."
        
        # Step 2: Get query embedding
        retrieval_query = sanitize_retrieval_query(user_query)
        logger.info(f"Sanitised User Query for Retrieval: {retrieval_query}")

        #Embed query for retrieval
        query_embedding = get_titan_embedding(retrieval_query)
        
        if query_embedding is None:
            logger.error("Failed to create query embedding")
            return "Error: Unable to process query for retrieval."
        
        # Step 3: Extract chunks from document
        chunks = document.get('chunks', [])
        
        if not chunks:
            logger.warning(f"No chunks found in document: {document_id}")
            # Still return summary if available
            return f"No content found for document ID: {document_id}"
        
        logger.info(f"Document has {len(chunks)} chunks")

        # Defensive Check for debugging dimension related error
        #expected_dim = len(query_embedding)
        #invalid_chunks = [c for c in chunks if len(c.get("embedding", [])) != expected_dim]

        #if invalid_chunks:
        #    logger.warning(f"{len(invalid_chunks)} chunks skipped due to embedding dimension mismatch")
        #    chunks = [c for c in chunks if len(c.get("embedding", [])) == expected_dim]
        
        # Step 4: Rank chunks by similarity
        ranked_chunks = self._rank_chunks_by_similarity(query_embedding, chunks)
        
        # Step 5: Filter by threshold and select top_k
        relevant_chunks = [
            chunk for chunk in ranked_chunks 
            if chunk['similarity'] >= similarity_threshold
        ]

        # Log how many chunks exceeded threshold
        logger.info(f"Document: {len(relevant_chunks)} chunks above threshold {similarity_threshold}")
    
        if not relevant_chunks:
            logger.warning(f"No chunks exceeded similarity threshold {similarity_threshold}")
            #return "No sufficiently relevant content found for your query."
            # For broad queries like "summarize", use fallback strategy
            logger.info("Using fallback strategy: including top chunks regardless of threshold")
            relevant_chunks = ranked_chunks[:top_k]  # Take top 5 chunks as fallback
        else:
            # Apply top_k limit
            relevant_chunks = relevant_chunks[:top_k]      
        
        # Step 6: Format context for ChatEngine
        context_parts = []
        
        doc_name = document.get('fileName', document_id)
        upload_date = document.get('createdAt', 'Unknown date')
            
        # Add document header
        context_parts.append(f"=== Document: {doc_name} ===\n")
        context_parts.append(f"Uploaded Date: {upload_date}\n")

        # Add document summary as introduction (if available)
        if include_summary and document.get('summary'):
            summary = document['summary']
            context_parts.append(f"Document Overview:\n{summary}\n")
            logger.info(f"Added document summary: {len(summary)} chars")
        
        # Add relevant chunks with metadata
        for i, chunk in enumerate(relevant_chunks, 1):
            source_info = chunk.get('source', f"Chunk {i}")
            similarity_score = chunk['similarity']

            context_parts.append(
            f"\nSection {i} - {source_info} [Relevance: {similarity_score:.3f}]:\n{chunk['content']}"
            )

            logger.info(f"Chunk {i}: similarity={similarity_score:.3f}, length={len(chunk['content'])} chars")
  
        # Join with separators
        formatted_context = "\n---\n".join(context_parts)
        
        retrieval_duration = time.time() - retrieval_start_time
        logger.info(f"Retrieval completed in {retrieval_duration:.2f}s. Retrieved {len(relevant_chunks)} chunks.")
        
        return formatted_context
    
    def retrieve_multi_document(self,
                           document_ids: List[str],
                           user_query: str,
                           top_k_per_doc: int = 10,     # maximum number of chunks / document
                           similarity_threshold: float = 0.1) -> str:
        """
        Retrieve context from multiple documents.
        
        Args:
            document_ids: List of document IDs to retrieve from
            user_query: User's question
            top_k_per_doc: Chunks per document
            similarity_threshold: Minimum similarity score
            
        Returns:
            Combined formatted context from all documents
        """
        retrieval_start_time = time.time()
        logger.info(f"Initiating Multi-document retrieval for {len(document_ids)} documents")
        logger.info(f"Embedding Similarity matching threshold: {similarity_threshold}, Max Chunks/Doc: {top_k_per_doc}")
        
        all_context_parts = []
        
        # Get query embedding once
        retrieval_query = sanitize_retrieval_query(user_query)
        logger.info(f"Sanitised User Query for Retrieval: {retrieval_query}")

        #Embed query for retrieval
        query_embedding = get_titan_embedding(retrieval_query)
        
        if query_embedding is None:
            logger.error("Failed to create query embedding")
            return "Error: Unable to process query for retrieval."
        
        for doc_id in document_ids:
            # Fetch document
            document = self._fetch_document(doc_id)
            
            if not document:
                logger.warning(f"Document {doc_id} not found, skipping")
                continue
            
            # Add document summary
            doc_name = document.get('fileName', doc_id)
            upload_date = document.get('createdAt', 'Unknown date')
            if document.get('summary'):
                all_context_parts.append(f"===Document: {doc_name} ===\nUploaded Date: {upload_date}\nSummary:\n{document['summary']}\n")
            else:
                all_context_parts.append(f"=== Document: {doc_name} ===\nUploaded Date: {upload_date}\n")
            
            # Rank chunks
            chunks = document.get('chunks', [])
            if not chunks:
                logger.warning(f"No chunks found in document {doc_id}")
                all_context_parts.append("No content chunks available.\n")
                continue
                     
            ranked_chunks = self._rank_chunks_by_similarity(query_embedding, chunks)
            
            # Get all chunks above threshold
            relevant_chunks = [
                chunk for chunk in ranked_chunks 
                if chunk['similarity'] >= similarity_threshold
            ]

            # Log how many chunks exceeded threshold
            logger.info(f"Document {doc_name}: {len(relevant_chunks)} chunks above threshold {similarity_threshold}")
   
            # Uncomment this line to keep ALL chunks above threshold
            relevant_chunks = relevant_chunks[:top_k_per_doc]

            if not relevant_chunks:
                all_context_parts.append("No chunks exceeded similarity threshold.\n")
                continue

            # Format chunks from this document with metadata
            all_context_parts.append("Relevant Sections:")
            for i, chunk in enumerate(relevant_chunks, 1):
                source_info = chunk.get('source', f"Chunk {i}")
                similarity_score = chunk['similarity']
                
                all_context_parts.append(
                f"Section {i} - {source_info} [Relevance: {similarity_score:.3f}]:\n{chunk['content']}"
                )
            
                logger.info(f"  Chunk {i}: similarity={similarity_score:.3f}, length={len(chunk['content'])} chars")



        if not all_context_parts:
            return "No relevant content found across the provided documents."
        
        formatted_context = "\n---\n".join(all_context_parts)
        
        retrieval_duration = time.time() - retrieval_start_time
        logger.info(f"Multi-doc retrieval completed in {retrieval_duration:.2f}s")
        
        return formatted_context

    def retrieve_with_metadata(self, 
                              document_id: str, 
                              user_query: str, 
                              top_k: int = 3,
                              similarity_threshold: float = 0.6) -> Dict:
        """
        Retrieve chunks with full metadata (for advanced use cases).
        
        Args:
            document_id: Document ID (documentId)
            user_query: User's question/query
            top_k: Number of top chunks to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Dict with context string and metadata
        """
        retrieval_start_time = time.time()
        logger.info(f"Starting retrieval for document: {document_id}, query: '{user_query[:100]}...'")
        
        # Fetch document
        document = self._fetch_document(document_id)
        
        if not document:
            return {
                "success": False,
                "error": f"Document {document_id} not found",
                "context": "",
                "chunks": [],
                "document_metadata": {}
            }
        
        # Get query embedding
        query_embedding = get_titan_embedding(user_query)
        
        if query_embedding is None:
            return {
                "success": False,
                "error": "Failed to create query embedding",
                "context": "",
                "chunks": [],
                "document_metadata": {}
            }
        
        # Rank chunks
        chunks = document.get('chunks', [])
        
        if not chunks:
            return {
                "success": False,
                "error": "No chunks found in document",
                "context": "",
                "chunks": [],
                "document_metadata": {}
            }
        
        logger.info(f"Document has {len(chunks)} chunks")

        # Defensive Check
        expected_dim = len(query_embedding)
        invalid_chunks = [c for c in chunks if len(c.get("embedding", [])) != expected_dim]

        if invalid_chunks:
            logger.warning(f"{len(invalid_chunks)} chunks skipped due to embedding dimension mismatch")
            chunks = [c for c in chunks if len(c.get("embedding", [])) == expected_dim]

        if not chunks:
            return "No valid chunks available for similarity comparison."
        
        ranked_chunks = self._rank_chunks_by_similarity(query_embedding, chunks)
        
        relevant_chunks = [
            chunk for chunk in ranked_chunks 
            if chunk['similarity'] >= similarity_threshold
        ][:top_k]

        if not relevant_chunks:
            logger.warning(f"No chunks exceeded similarity threshold {similarity_threshold}")
            return {
                "success": False,
                "error": "No chunks found in document",
                "context": "",
                "chunks": [],
                "document_metadata": {}
            }     
        
        # Format context with summary
        context_parts = []
        
        if document.get('summary'):
            context_parts.append(f"Document Overview:\n{document['summary']}\n")
        
        for i, chunk in enumerate(relevant_chunks, 1):
            source_info = chunk.get('source', f"Chunk {i}")
            relevance = f"[Relevance Score: {chunk['similarity']:.2f}]"

            context_parts.append(
                f"Section {i} - {source_info} {relevance}:\n{chunk['content']}"
            )

            logger.info(
                f"Chunk {i}: {chunk.get('source', 'unknown')} | "
                f"Similarity: {chunk['similarity']:.3f} | "
                f"Content: {len(chunk['content'])} chars"
            )

        # Join with separators
        formatted_context = "\n---\n".join(context_parts)
        
        retrieval_duration = time.time() - retrieval_start_time
        logger.info(f"Retrieval completed in {retrieval_duration:.2f}s. Retrieved {len(relevant_chunks)} chunks.")

        # Extract document metadata
        document_metadata = {
            "documentId": document.get('documentId'),
            "fileName": document.get('fileName'),
            "fileSize": document.get('fileSize'),
            "contentType": document.get('contentType'),
            "createdAt": document.get('createdAt'),
            "userId": document.get('user_Id'),
            "chatId": document.get('chatId')
        }
        
        return {
            "success": True,
            "context": formatted_context,
            "chunks": relevant_chunks,
            "retrieval_time": retrieval_duration,
            "total_chunks_available": len(chunks),
            "chunks_returned": len(relevant_chunks),
            "document_metadata": document_metadata
        }


# Convenience function for simple usage
def retrieve_context(document_id: str, 
                    user_query: str, 
                    table_name: str = None,
                    mock_data_path: str = None,
                    top_k: int = 3) -> str:
    """
    Simple function to retrieve context for a query.
    
    Args:
        document_id: Document ID
        user_query: User's question
        table_name: DynamoDB table name (optional if using mock data)
        mock_data_path: Path to mock JSON file (optional)
        top_k: Number of chunks to retrieve
        
    Returns:
        Formatted context string
    """
    retriever = DocumentRetriever(table_name=table_name, mock_data_path=mock_data_path)
    return retriever.retrieve(document_id, user_query, top_k)


if __name__ == "__main__":
    """Test the retrieval module with mock data"""
    print("=" * 80)
    print("Testing DocumentRetriever with Mock Data")
    print("=" * 80)
    
    # Initialize retriever with mock data

    mock_data_path = get_mock_data_path()
    retriever = DocumentRetriever(mock_data_path=mock_data_path)
    
    # Test retrieval
    test_document_id = "doc-123e4567-e89b-12d3-a456-426614174000"
    test_query = "What is Acme Corporation's revenue?"
    
    print(f"Query: {test_query}")
    print(f"\nDocument ID: {test_document_id}")
    print("\n" + "-" * 80)
    
    # Simple retrieval
    context = retriever.retrieve(
        document_id=test_document_id,
        user_query=test_query
    )
    
    print("Retrieved Context:")
    print(context[:3000] + "..." if len(context) > 3000 else context)

    print("\n" + "-" * 80)
    
    print("\n" + "-" * 80)
    print ("Multi-doc Retrival Test")
    print("\n" + "-" * 80)
    # Test multi-document retrieval
    context = retriever.retrieve_multi_document(
        document_ids=["doc-123e4567-e89b-12d3-a456-426614174123", "doc-123e4567-e89b-12d3-a456-426614174000"],
        user_query="What new products did Acme launch in 2024?",
        top_k_per_doc=10,  # Allow up to 10 chunks per doc
        similarity_threshold=0.5
    )

    print("=" * 80)
    print("MULTI-DOC CONTEXT:")
    print(context)
    print("=" * 80)


    """     
    # Retrieval with metadata
    result = retriever.retrieve_with_metadata(
        document_id=test_document_id,
        user_query=test_query,
        top_k=3,
        similarity_threshold=0.7    
    )
    
    if result["success"]:
        print(f"\nSuccess! Retrieved {result['chunks_returned']} chunks in {result['retrieval_time']:.2f}s")
        print(f"Document: {result['document_metadata']['fileName']}")
        if result['chunks']:
            print(f"Top chunk similarity: {result['chunks'][0]['similarity']:.3f}")
    else:
        print(f"Error: {result['error']}") 
    
    """
