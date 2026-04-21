from flask import Flask
from dotenv import load_dotenv

# load env vars and initialize flask 
load_dotenv()
app = Flask(__name__)

from app import routes