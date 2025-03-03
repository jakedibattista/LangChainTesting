# Document Search Engine

A semantic search application built with LangChain, Supabase (PostgreSQL/pgvector), and Streamlit.

## Features

* 📄 Upload and process PDF and text documents
* 🔍 Perform semantic search across documents using embeddings
* 📊 View search results with relevance scores and metadata
* 🗑️ Manage documents with batch delete functionality

## Tech Stack

* **Frontend**: Streamlit
* **Backend**: Python, LangChain
* **Database**: Supabase (PostgreSQL with pgvector)
* **Embeddings**: HuggingFace (all-MiniLM-L6-v2)

## Prerequisites

* Python 3.8+
* Supabase account
* pip (Python package manager)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/document-search-engine.git
cd document-search-engine
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up Supabase:
   * Create a new Supabase project
   * Enable pgvector extension in the SQL editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

5. Configure environment variables:
   Create a `.env` file:
   ```env
   DATABASE_URL="your-supabase-postgres-connection-string"
   SUPABASE_URL="your-supabase-project-url"
   SUPABASE_KEY="your-supabase-anon-key"
   ```

   Or create `.streamlit/secrets.toml`:
   ```toml
   [postgres]
   database_url = "your-supabase-postgres-connection-string"

   [supabase]
   url = "your-supabase-project-url"
   key = "your-supabase-anon-key"
   ```

## Usage

1. Start the Streamlit app:

```bash
streamlit run app.py
```

2. Open your browser and navigate to: http://localhost:8501

3. Upload documents using the file uploader
4. Use the sidebar to manage documents
5. Enter search queries to find relevant content
6. View results with relevance scores and metadata

## Project Structure

* `app.py`: Main Streamlit application
* `knowledge_base.py`: Core document processing and search functionality
* `manage_db.py`: Database management utilities

## License

MIT

Built with ❤️ using LangChain, Streamlit, and Supabase
