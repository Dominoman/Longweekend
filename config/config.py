import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

class Config:
    APIKEY = os.environ.get("APIKEY","not set")
    SAVEDIR = os.environ.get("SAVEDIR", "tmp")

