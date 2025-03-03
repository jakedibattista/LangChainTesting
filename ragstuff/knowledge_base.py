from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.document_loaders import TextLoader, PyPDFLoader
import os
from dotenv import load_dotenv
import streamlit as st
import psycopg2
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def get_connection_string():
    """Get database connection string with proper formatting"""
    if hasattr(st, 'secrets'):
        try:
            # Get the connection URL from secrets
            db_url = st.secrets["postgres"]["database_url"]
            return db_url
        except KeyError:
            st.error("Database configuration not found in secrets")
            raise
    return os.getenv("DATABASE_URL", "postgresql:///postgres")

def init_database():
    """Initialize database with required extensions and tables"""
    conn_string = get_connection_string()
    
    try:
        # Create engine with required parameters
        engine = create_engine(
            conn_string,
            connect_args={
                "sslmode": "require"  # Required for Supabase
            } if "supabase.co" in conn_string else {}
        )
        
        # Create extensions and tables
        with engine.connect() as conn:
            # Create vector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.execute(text("COMMIT;"))  # Commit the extension creation
            
            # Create tables
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_collection (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100),
                    cmetadata JSONB
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    collection_id UUID REFERENCES langchain_pg_collection(id),
                    embedding vector(384),
                    document TEXT,
                    cmetadata JSONB,
                    custom_id VARCHAR(100)
                );
            """))
            
            conn.commit()
            
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        raise e

def get_db_params():
    """Get database connection parameters"""
    if hasattr(st, 'secrets'):
        try:
            url = st.secrets["postgres"]["database_url"]
            # Parse URL into components
            parsed = urlparse(url)
            return {
                "host": parsed.hostname,
                "port": parsed.port,
                "database": parsed.path[1:],  # Remove leading slash
                "user": parsed.username,
                "password": parsed.password,
                "sslmode": "require"
            }
        except KeyError:
            st.error("Database configuration not found in secrets")
            raise
    return {}

class KnowledgeBase:
    def __init__(self):
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
        
        # Initialize vector store with proper connection handling
        try:
            db_params = get_db_params()
            self.vector_store = PGVector(
                connection_string=get_connection_string(),
                embedding_function=self.embeddings,
                collection_name="documents",
                distance_strategy="cosine",
                pre_delete_collection=False,
                connection_args=db_params
            )
        except Exception as e:
            st.error(f"Failed to connect to database: {str(e)}")
            st.info("Please check your database configuration in Streamlit secrets.")
            raise
    
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