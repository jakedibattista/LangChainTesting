from sqlalchemy import create_engine, text

# Local PostgreSQL connection
connection_string = "postgresql:///postgres"

try:
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        print(f"Connection successful! Test query result: {result}")
except Exception as e:
    print(f"Connection failed: {e}") 