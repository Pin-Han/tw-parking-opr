import pytest
from sqlalchemy import create_engine, text
import os


@pytest.fixture
def db_engine(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                stmt = stmt.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                conn.execute(text(stmt))
    yield engine
    engine.dispose()
