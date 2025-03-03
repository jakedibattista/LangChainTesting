# Document Search Engine

A semantic search application built with LangChain, PostgreSQL/pgvector, and Streamlit. This app allows users to:

## Features
- 📄 Upload and process PDF and text documents
- 🔍 Perform semantic search across documents using embeddings
- 📊 View search results with relevance scores
- 🗑️ Manage documents with batch delete functionality

## Tech Stack
- **Frontend**: Streamlit
- **Backend**: Python, LangChain
- **Database**: PostgreSQL with pgvector extension
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2)

## Prerequisites
- Python 3.8+
- PostgreSQL with pgvector extension
- pip (Python package manager)

## Installation

1. Clone the repository:
bash
git clone https://github.com/yourusername/document-search-engine.git
cd document-search-engine


2. Create a virtual environment and activate it:
bash
python -m venv venv
source venv/bin/activate

3. Install dependencies:
bash
pip install -r requirements.txt


4. Set up PostgreSQL:
- Install PostgreSQL
- Create a database
- Enable pgvector extension: `CREATE EXTENSION vector;`

## Local Development
1. Start the Streamlit app:
bash
streamlit run app.py

2. Open your browser and navigate to:
http://localhost:8501


## Project Structure
- `app.py`: Main Streamlit application
- `knowledge_base.py`: Core document processing and search functionality
- `manage_db.py`: Database management utilities
- `test_kb.py`: Test script for knowledge base
- `test_connection.py`: Database connection test

## Usage
1. Upload documents using the file uploader
2. View and manage documents in the sidebar
3. Search through documents using natural language queries
4. View results with relevance scores and source information

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)

Built with ❤️ using LangChain and Streamlit