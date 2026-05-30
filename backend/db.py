"""
Database connection helper.
Reads individual DB_* fields from .env (avoids URL-encoding issues with
special characters in the password) and provides a connection factory.
Using psycopg (v3) directly against Supabase Postgres.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_USER, DB_PASSWORD]):
    raise RuntimeError(
        "Missing DB credentials. Check DB_HOST, DB_USER, DB_PASSWORD in your .env file."
    )


def get_connection():
    """Open a new database connection. Caller is responsible for closing.
    Passing params as keyword args means the password is used raw — no
    URL percent-encoding required even if it contains %, @, :, etc.
    """
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


if __name__ == "__main__":
    # Quick connection + sanity test
    print("Connecting to database...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM knowledge_nodes;")
            node_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM edges WHERE edge_type = 'DERIVED_FROM';")
            edge_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM users;")
            user_count = cur.fetchone()[0]

    print("Connection successful!")
    print(f"  knowledge_nodes : {node_count}  (expect 18)")
    print(f"  DERIVED_FROM    : {edge_count}  (expect 12)")
    print(f"  users           : {user_count}  (expect 5)")