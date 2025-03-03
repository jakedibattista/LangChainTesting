from sqlalchemy import create_engine, text

# Connect to database
engine = create_engine("postgresql:///postgres")

def list_collections():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM langchain_pg_collection"))
        return list(result)

def list_documents():
    with engine.connect() as conn:
        # Get column info
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'langchain_pg_embedding'
        """))
        columns = [row[0] for row in result]
        
        # Get documents
        result = conn.execute(text("""
            SELECT uuid, document, cmetadata 
            FROM langchain_pg_embedding
        """))
        documents = list(result)
        
        return {
            'columns': columns,
            'documents': documents
        }

def clear_database():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM langchain_pg_embedding"))
        conn.execute(text("DELETE FROM langchain_pg_collection"))
        conn.commit()
        print("Database cleared!")

def delete_document(uuid):
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM langchain_pg_embedding WHERE uuid = :uuid"),
            {"uuid": uuid}
        )
        conn.commit()
        return True

if __name__ == "__main__":
    print("Collections:")
    collections = list_collections()
    for collection in collections:
        print(collection)
    
    print("\nDocuments:")
    docs = list_documents()
    print("Available columns:", docs['columns'])
    for doc in docs['documents']:
        print(f"UUID: {doc.uuid}")
        print(f"Document: {doc.document}")
        print(f"Metadata: {doc.cmetadata}")
        print("---") 