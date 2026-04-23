import psycopg2
import os
from dotenv import load_dotenv, find_dotenv

# Ensure DATABASE_URL is available even when running this file directly
# (e.g., `python .\app\db.py` or from within the `app\` directory).
load_dotenv(find_dotenv())

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


if __name__ == "__main__":
    check_db()
