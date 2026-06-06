import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///parking.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db():
    """Run schema.sql to create tables if they don't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))


def get_engine():
    return engine
