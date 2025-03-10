from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.document_loaders import TextLoader, PyPDFLoader
import os
from dotenv import load_dotenv
import streamlit as st
from supabase import create_client
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def get_connection_string():
    if hasattr(st, 'secrets'):
        try:
            # Get Supabase credentials
            supabase_url = st.secrets["supabase"]["url"]
            # Use the postgres connection string directly
            return st.secrets["postgres"]["database_url"]
        except KeyError:
            pass
    # Fallback to environment variables
    return os.getenv("DATABASE_URL")

def init_database():
    """Initialize database with required extensions and tables"""
    conn_string = get_connection_string()
    
    try:
        # Create engine
        engine = create_engine(conn_string)
        
        # Create tables with correct schema
        with engine.connect() as conn:
            # Create vector extension if not exists
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Drop existing tables if they exist
            conn.execute(text("DROP TABLE IF EXISTS langchain_pg_embedding;"))
            conn.execute(text("DROP TABLE IF EXISTS langchain_pg_collection;"))
            
            # Create collection table with uuid
            conn.execute(text("""
                CREATE TABLE langchain_pg_collection (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100),
                    cmetadata JSONB
                );
            """))
            
            # Create embedding table
            conn.execute(text("""
                CREATE TABLE langchain_pg_embedding (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    collection_id UUID REFERENCES langchain_pg_collection(uuid),
                    embedding vector(384),
                    document TEXT,
                    cmetadata JSONB,
                    custom_id VARCHAR(100)
                );
            """))
            
            conn.commit()
            
        # Initialize Supabase client for other operations
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if hasattr(st, 'secrets'):
            try:
                supabase_url = st.secrets["supabase"]["url"]
                supabase_key = st.secrets["supabase"]["key"]
            except KeyError:
                pass
        
        supabase = create_client(supabase_url, supabase_key)
            
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        raise e

class KnowledgeBase:
    def __init__(self):
        # Initialize database
        init_database()
        
        # Initialize embedding model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Text splitting configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            is_separator_regex=False,
        )
        
        # Initialize vector store
        self.vector_store = PGVector(
            connection_string=get_connection_string(),
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