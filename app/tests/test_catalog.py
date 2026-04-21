from app.db import connect_db

conn = connect_db()
cur = conn.cursor()

print("Abs records:")
try:
    cur.execute("""
        SELECT name, equipment
        FROM exercise
        WHERE muscle_group = 'abs'
    """)
    rows = cur.fetchall()
    for row in rows:
        print(row)

except Exception as e:
    print("Error: ", e)

cur.close()
conn.close()

