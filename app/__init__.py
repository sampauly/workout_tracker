import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

from app.db import close_db
app.teardown_appcontext(close_db)

from app import routes