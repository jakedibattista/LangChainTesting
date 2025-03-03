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
    """Get database connection string from environment or secrets"""
    conn_string = None
    
    # Try getting from Streamlit secrets
    if hasattr(st, 'secrets'):
        try:
            conn_string = st.secrets["postgres"]["database_url"]
        except KeyError:
            st.warning("Database URL not found in Streamlit secrets")
    
    # Fallback to environment variable
    if not conn_string:
        conn_string = os.getenv("DATABASE_URL")
    
    if not conn_string:
        raise ValueError(
            "Database connection string not found. "
            "Please set DATABASE_URL environment variable "
            "or configure postgres.database_url in Streamlit secrets."
        )
    
    return conn_string

def create_db_engine(conn_string):
    """Create SQLAlchemy engine with proper SSL configuration"""
    # Add query parameters to connection string if not present
    if '?' not in conn_string:
        conn_string += "?sslmode=require"
    
    return create_engine(
        conn_string,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    )

def init_database():
    """Initialize database with required extensions and tables"""
    try:
        # Get database connection
        conn_string = get_connection_string()
        
        # Initialize vector store with pre-initialized embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Let PGVector handle the initialization
        vector_store = PGVector.from_documents(
            documents=[],  # Empty list for initial setup
            embedding=embeddings,
            collection_name="documents",
            connection_string=conn_string,
            distance_strategy="cosine",
            pre_delete_collection=False  # Don't delete existing data
        )
        
        return vector_store
            
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        raise e

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
        
        # Initialize vector store
        self.vector_store = init_database()
    
    def add_document(self, file_path):
        """Add a document to the knowledge base"""
        try:
            st.write(f"Loading document: {file_path}")
            
            # Load document based on file type
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                st.write("Using PDF loader")
            else:
                loader = TextLoader(file_path)
                st.write("Using Text loader")
                
            documents = loader.load()
            st.write(f"Loaded {len(documents)} document(s)")
            
            # Split text into chunks
            texts = self.text_splitter.split_documents(documents)
            st.write(f"Split into {len(texts)} chunks")
            
            # Add to vector store
            ids = self.vector_store.add_documents(texts)
            st.write(f"Added {len(ids)} chunks to vector store")
            
            return True
            
        except Exception as e:
            st.error(f"Error adding document: {str(e)}")
            return False

    def search(self, query, k=3, debug=False):
        """Enhanced search with question-answering focus"""
        try:
            if debug:
                st.write("Executing search...")
            
            # Expand the query with relevant terms based on the question type
            query_lower = query.lower()
            expanded_query = query
            
            if "example" in query_lower or "work" in query_lower:
                # For queries asking about specific examples or work
                expanded_query = f"{query} developed created designed implemented led project experience"
            
            # Get more results with expanded query
            results = self.vector_store.similarity_search_with_score(
                expanded_query, 
                k=k*4  # Get more results to filter
            )
            
            if debug:
                st.write(f"Found {len(results)} initial results")
            
            # Format and filter results
            formatted_results = []
            for doc, score in results:
                # Convert score to similarity percentage
                similarity = (1 - score) * 100
                
                if debug:
                    st.write(f"Score: {score}, Similarity: {similarity}%")
                    st.write(f"Content: {doc.page_content[:100]}...")
                
                content = doc.page_content.strip()
                
                # Handle different types of questions
                if "example" in query_lower or "work" in query_lower:
                    # For specific work examples
                    relevant_terms = [
                        "developed", "created", "designed", "built", "implemented",
                        "led", "project", "worked on", "delivered", "launched",
                        "ux", "user experience", "interface", "user interface",
                        "research", "usability", "prototype", "wireframe"
                    ]
                    sentences = content.split(". ")
                    relevant_sentences = [
                        sent for sent in sentences 
                        if any(term in sent.lower() for term in relevant_terms)
                    ]
                    if relevant_sentences:
                        content = ". ".join(relevant_sentences) + "."
                        # Boost similarity for concrete examples
                        if any(term in content.lower() for term in ["ux", "user experience", "interface"]):
                            similarity += 15
                        if any(term in content.lower() for term in ["developed", "created", "designed", "implemented"]):
                            similarity += 10
                
                # Only include relevant results
                if similarity > 35:  # Threshold for relevance
                    formatted_results.append({
                        'content': content,
                        'similarity': similarity,
                        'metadata': doc.metadata
                    })
            
            # Sort by similarity
            formatted_results.sort(key=lambda x: float(x['similarity']), reverse=True)
            
            # Remove duplicate content
            seen_content = set()
            unique_results = []
            for result in formatted_results:
                content_hash = hash(result['content'])
                if content_hash not in seen_content and len(result['content'].split()) > 10:  # Ensure meaningful content
                    seen_content.add(content_hash)
                    unique_results.append(result)
            
            if debug:
                st.write(f"Returning {len(unique_results[:k])} filtered results")
            
            return unique_results[:k]
            
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def check_documents(self):
        """Debug function to check stored documents"""
        try:
            results = self.vector_store.similarity_search_with_score(
                "test",  # Generic query to get some results
                k=100  # Get many results to check
            )
            
            st.write("### Stored Documents")
            for doc, score in results:
                st.write("---")
                st.write("Content:", doc.page_content[:200])  # First 200 chars
                st.write("Metadata:", doc.metadata)
            
        except Exception as e:
            st.error(f"Error checking documents: {str(e)}")

    def check_vector_store(self):
        """Debug function to check vector store status"""
        try:
            # Try to query the collection table
            conn_string = get_connection_string()
            engine = create_engine(conn_string)
            
            with engine.connect() as conn:
                # Check collection
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM langchain_pg_collection 
                    WHERE name = 'documents';
                """)).fetchone()
                st.write(f"Collections found: {result[0]}")
                
                # Check embeddings
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = 'documents';
                """)).fetchone()
                st.write(f"Embeddings stored: {result[0]}")
                
                # Sample some documents
                results = conn.execute(text("""
                    SELECT e.document, e.cmetadata
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = 'documents'
                    LIMIT 5;
                """)).fetchall()
                
                if results:
                    st.write("Sample documents:")
                    for doc in results:
                        st.write("---")
                        st.write("Content:", doc[0][:200])
                        st.write("Metadata:", doc[1])
                else:
                    st.write("No documents found in the database")
                
        except Exception as e:
            st.error(f"Error checking vector store: {str(e)}") 