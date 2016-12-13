import logging
import os


class Config(object):
    DEBUG = False
    TESTING = False
    MONGO_URI = os.environ.get("MONGODB_URI")
    CLIENT_ID = os.environ.get("CLIENT_ID")
    CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
    LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    LOGGING_FILE = "app.log"
    LOGGING_LEVEL = logging.WARNING


class DevelopmentConfig(Config):
    DEBUG = True
    MONGO_URI = "mongodb://localhost:27017/rest"
    LOGGING_LEVEL = logging.DEBUG
