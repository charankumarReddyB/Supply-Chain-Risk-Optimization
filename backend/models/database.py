import os
import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.config import Config

# SQLAlchemy setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, pool_size=10, max_overflow=20)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db_connection():
    """Returns a raw PostgreSQL connection."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(
            db_url,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        sslmode=Config.DB_SSLMODE,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def execute_query(query, params=None, fetch=True):
    """Executes a SQL query and returns results if fetch is True."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()

def execute_many(query, data):
    """Executes a query against multiple data rows."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(query, data)
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()

def run_sql_file(file_path):
    """Reads a SQL file and executes its statements."""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split queries by semicolon, ignoring empty lines/comments
    queries = []
    current_query = []
    for line in sql_content.splitlines():
        if line.strip().startswith("--") or not line.strip():
            continue
        current_query.append(line)
        if line.strip().endswith(";"):
            queries.append("\n".join(current_query))
            current_query = []
            
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for q in queries:
                if q.strip():
                    cursor.execute(q)
            conn.commit()
    finally:
        conn.close()
