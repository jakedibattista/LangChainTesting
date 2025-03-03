from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.document_loaders import TextLoader, PyPDFLoader
import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Load environment variables
load_dotenv()

# Local PostgreSQL connection
CONNECTION_STRING = "postgresql:///postgres"

class KnowledgeBase:
    def __init__(self):
        # Initialize embedding model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # More focused text splitting for QA
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,          # Smaller chunks for more precise answers
            chunk_overlap=100,       # More overlap to maintain context
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            is_separator_regex=False,
        )
        
        # Initialize vector store
        self.vector_store = PGVector(
            connection_string=CONNECTION_STRING,
            embedding_function=self.embeddings,
            collection_name="documents",
            distance_strategy="cosine"
        )
    
    def add_document(self, file_path):
        """Add a document to the knowledge base"""
        # Load document based on file type
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
            
        documents = loader.load()
        # Split text into chunks
        texts = self.text_splitter.split_documents(documents)
        # Add to vector store
        self.vector_store.add_documents(texts)
        
    def search(self, query, k=3):
        """Enhanced search with question-answering focus"""
        # Get more results initially to find best answer
        results = self.vector_store.similarity_search_with_score(
            query, 
            k=k*2  # Get more results to filter
        )
        
        # Format and filter results
        formatted_results = []
        for doc, score in results:
            # Convert score to similarity percentage
            similarity = (1 - score) * 100
            
            # Only include relevant results
            if similarity > 30:
                # Clean and format the content
                content = doc.page_content.strip()
                
                # For "who is" questions, try to extract relevant sentences
                if query.lower().startswith("who is"):
                    name = query.lower().replace("who is ", "").strip()
                    sentences = content.split(". ")
                    relevant_sentences = []
                    for sentence in sentences:
                        if name in sentence.lower():
                            relevant_sentences.append(sentence)
                    if relevant_sentences:
                        content = ". ".join(relevant_sentences) + "."
                
                formatted_results.append({
                    'content': content,
                    'similarity': f"{similarity:.1f}%",
                    'metadata': doc.metadata
                })
        
        # Sort by similarity
        formatted_results.sort(key=lambda x: float(x['similarity'].rstrip('%')), reverse=True)
        
        # Return top k results
        return formatted_results[:k] 