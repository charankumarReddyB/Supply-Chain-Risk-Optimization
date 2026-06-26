import os
import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.config import Config

# SQLAlchemy setup (with 3-second connection timeout)
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    connect_args={"connect_timeout": 3},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def is_postgres():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return "postgres" in db_url or "postgresql" in db_url
    port = int(os.environ.get("DB_PORT", Config.DB_PORT))
    return port not in (3306, 3307)

def acquire_db_lock():
    try:
        if is_postgres():
            res = execute_query("SELECT pg_try_advisory_lock(123456) as locked")
            return res and res[0]["locked"]
        else:
            res = execute_query("SELECT GET_LOCK('init_lock', 0) as locked")
            return res and res[0]["locked"] == 1
    except Exception:
        return False

def release_db_lock():
    try:
        if is_postgres():
            execute_query("SELECT pg_advisory_unlock(123456)")
        else:
            execute_query("SELECT RELEASE_LOCK('init_lock')")
    except Exception:
        pass

def get_db_connection():
    """Returns a raw PostgreSQL or MySQL connection with a 3-second timeout."""
    if is_postgres():
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return psycopg2.connect(
                db_url,
                connect_timeout=3,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        return psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            sslmode=Config.DB_SSLMODE,
            connect_timeout=3,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    else:
        import pymysql
        import pymysql.cursors
        return pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3
        )

def execute_query(query, params=None, fetch=True):
    """Executes a SQL query and returns results if fetch is True."""
    if is_postgres() and "LAST_INSERT_ID()" in query:
        query = query.replace("LAST_INSERT_ID()", "LASTVAL()")
    
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

def execute_insert(query, params=None):
    """Executes an INSERT query and returns the generated ID on the same connection."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if is_postgres():
                cursor.execute("SELECT LASTVAL() as last_id")
                res = cursor.fetchone()
                if isinstance(res, dict):
                    last_id = res["last_id"]
                elif res:
                    last_id = res[0]
                else:
                    last_id = None
            else:
                last_id = cursor.lastrowid
            conn.commit()
            return last_id
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
    """Reads a SQL file and executes its statements query-by-query."""
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
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            for q in queries:
                if q.strip():
                    try:
                        cursor.execute(q)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"DDL execution warning: {e} for query: {q.strip().splitlines()[0]}")
    finally:
        conn.close()

