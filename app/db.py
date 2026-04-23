import psycopg2
import os
from flask import g

# basic connection function for our app
def connect_db():
    # using env vars if available, otherwise fallback values
    # db_name = os.getenv("DB_NAME") or "workout_tracker"
    # user = os.getenv("DB_USER") or "postgres"
    # password = os.getenv("DB_PASS") or "postgres"
    # host = os.getenv("DB_HOST") or "localhost"

    # conn = psycopg2.connect(
    #     dbname=db_name,
    #     user=user,
    #     password=password,
    #     host=host
    # )
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn


# quick check to see if connection works
def check_db():
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        print("db connected")
        cur.close()
        conn.close()
    except Exception as err:
        print("error connecting to db:", err)

def get_db():
    if 'db' not in g:
        g.db = connect_db()
    return g.db

def close_db(_e=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

if __name__ == "__main__":
    check_db()
