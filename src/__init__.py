from flask import Flask

app = Flask(__name__, static_folder='temp_images')

from src import login
from src import dashboard
from src import camera
