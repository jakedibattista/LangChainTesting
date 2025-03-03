import streamlit as st
from knowledge_base import KnowledgeBase
from manage_db import list_documents, clear_database, engine, delete_document
import tempfile
import os
import io
from sqlalchemy import text

# Initialize knowledge base
kb = KnowledgeBase()

# Initialize session state for view control
if 'show_documents' not in st.session_state:
    st.session_state.show_documents = False

st.title("Document Search Engine")

# Sidebar for database management
with st.sidebar:
    st.header("Database Management")
    # Change button text based on current state
    view_button_text = "Hide Documents" if st.session_state.show_documents else "View All Documents"
    if st.button(view_button_text):
        # Toggle the view state
        st.session_state.show_documents = not st.session_state.show_documents
    
    # Clear database section
    st.divider()
    st.subheader("Clear Database")
    confirm_clear = st.checkbox("I understand this will delete ALL documents")
    if st.button("🗑️ Clear Entire Database"):
        if confirm_clear:
            clear_database()
            st.success("Database cleared!")
            st.session_state.show_documents = False
            st.rerun()
        else:
            st.warning("Please confirm by checking the box above")

# Document view section
if st.session_state.show_documents:
    st.subheader("All Documents")
    try:
        with st.spinner("Loading documents..."):
            docs = list_documents()
            
            with st.expander("Available Columns"):
                st.write(docs['columns'])
            
            # Create a container for selected documents
            if 'selected_docs' not in st.session_state:
                st.session_state.selected_docs = set()
            
            # Add a delete button container at the top
            delete_container = st.container()
            
            # Display documents
            for doc in docs['documents']:
                with st.expander(f"Document {doc.uuid}"):
                    col1, col2 = st.columns([5,1])
                    with col1:
                        st.text("Content:")
                        st.write(doc.document)
                        st.text("Metadata:")
                        st.write(doc.cmetadata)
                    with col2:
                        # Use session state to maintain checkbox state
                        key = f"select_{doc.uuid}"
                        if st.checkbox("", key=key, value=doc.uuid in st.session_state.selected_docs):
                            st.session_state.selected_docs.add(doc.uuid)
                        else:
                            st.session_state.selected_docs.discard(doc.uuid)
            
            # Show delete button in the container if docs are selected
            with delete_container:
                if st.session_state.selected_docs:
                    if st.button(f"🗑️ Delete Selected Documents ({len(st.session_state.selected_docs)})"):
                        try:
                            for uuid in st.session_state.selected_docs:
                                delete_document(uuid)
                            st.success(f"Successfully deleted {len(st.session_state.selected_docs)} documents!")
                            st.session_state.selected_docs.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting documents: {str(e)}")

    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

# File upload section
st.header("Upload Documents")
uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=['txt', 'pdf'])

if uploaded_files:
    for file in uploaded_files:
        try:
            # Create a temporary directory that's more permissive
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a file path in the temporary directory
                temp_path = os.path.join(temp_dir, file.name)
                
                # Write the file contents
                with open(temp_path, 'wb') as f:
                    f.write(file.getvalue())
                
                # Add document to knowledge base
                kb.add_document(temp_path)
                st.success(f"Successfully added: {file.name}")
                
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
            st.error("Full error:", exc_info=True)  # This will show the full error trace

# Search section
st.header("Search Documents")
col1, col2 = st.columns([3,1])
with col1:
    query = st.text_input("Enter your search query")
with col2:
    k = st.number_input("Number of results", min_value=1, max_value=10, value=3)

if query:
    with st.spinner("Searching..."):
        results = kb.search(query, k=k)
        
        if not results:
            st.info("No relevant results found. Try a different query.")
        else:
            st.subheader("Search Results")
            for i, result in enumerate(results, 1):
                with st.expander(f"Result {i} (Relevance: {result['similarity']:.1f}%)", expanded=True):
                    # Create two columns - one for content, one for metadata
                    content_col, metadata_col = st.columns([2, 1])
                    
                    with content_col:
                        st.markdown("#### Content")
                        st.markdown(result['content'])
                    
                    with metadata_col:
                        st.markdown("#### Source Details")
                        if result['metadata']:
                            metadata_html = []
                            for key, value in result['metadata'].items():
                                if key == 'page':
                                    metadata_html.append(f"📄 **Page:** {value + 1}")
                                elif key == 'source':
                                    filename = os.path.basename(value)
                                    metadata_html.append(f"📁 **File:** {filename}")
                                elif key == 'creator':
                                    metadata_html.append(f"👤 **Creator:** {value}")
                                elif key == 'creationdate':
                                    # Format date if it exists
                                    try:
                                        date = value.split('D:')[1][:8]  # Extract YYYYMMDD
                                        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                                        metadata_html.append(f"📅 **Created:** {formatted_date}")
                                    except:
                                        metadata_html.append(f"📅 **Created:** {value}")
                                else:
                                    metadata_html.append(f"**{key.title()}:** {value}")
                            
                            st.markdown("\n".join(metadata_html)) 