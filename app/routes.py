from app import app
from app.db import connect_db, check_db

@app.route('/')
@app.route('/index')
def index():
    check_db()
    return "Hello World!"