"""
reddit user-analytics app providing insights on how user spends time on reddit.
Author: Rasmus Heikkila 2016
"""

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask.ext.pymongo import PyMongo
from waitress import serve

import logging
import logging.handlers
import os
import re

from analytics import parse_date
import analytics
import reddit

app = Flask(__name__)
app.config.from_object(os.environ["APP_CONFIG"])

handler = logging.handlers.RotatingFileHandler(app.config["LOGGING_FILE"])
formatter = logging.Formatter(app.config["LOGGING_FORMAT"])
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(app.config["LOGGING_LEVEL"])

with app.app_context():
    mongo = PyMongo(app)
    users = mongo.db.users
    users.create_index("username")
    app.logger.info("DB connection established to %s", app.config["MONGO_URI"])


def valid(name):
    """
    Checks whether the given string is a valid reddit username.
    """
    user_regexp = re.compile(r"\A[\w-]+\Z", re.UNICODE)
    min_length = 3
    max_length = 20
    
    if name is None:
        return False
    elif len(name) < min_length or len(name) > max_length:
        return False
    try:
        if any(char.isspace() for char in name):
            return False
        return True if user_regexp.match(name) else False
    except TypeError:
        return False
    except UnicodeEncodeError:
        return False


def retrieve_data(username):
    """
    Returns a dictionary containing user data from reddit API and
    saves it in the database if successful.

    If data retrieval, returns a dictionary with "error" key.
    """
    result = reddit.api.user(username)
    if not "error" in result:
        data = analytics.process(result)
        res = users.replace_one({"username": username}, data, upsert=True)
        if not res.acknowledged:
            app.logger.warning("Failed to write data of user: %s", username)
        return data
    else:
        return result
    
    
@app.route("/")
def home():
    return render_template("index.html", message="")
        

@app.route("/u/<name>")
def user(name):
    if not valid(name):
        return render_template("index.html", message="Invalid username.")

    return render_template("stats.html", user=name)


@app.route("/stats/<name>")
def stats(name):
    if not valid(name):
        return jsonify(error="Invalid name")

    refresh = request.args.get("refresh") == "true"

    if refresh:
        user_data = retrieve_data(name)
    else:
        user_data = users.find_one({"username": name})
        if not user_data:
            user_data = retrieve_data(name)

    if "error" in user_data:
        return jsonify(**user_data)

    if not (user_data.get("posts") or user_data.get("analytics")):
        return jsonify(error="No posts were found!")

    statistics = user_data["analytics"]

    payload = {
        "postcount": len(user_data["posts"]),
        "refreshed": user_data["refreshed"],
        "account_created": parse_date(int(user_data["info"]["created_utc"])),
        "oldest_post_date": user_data["posts"][-1]["data"]["created_utc"],
        "total_karma": statistics["total_score"],
        "words_per_post": "{:.1f}".format(statistics["avg_words"]),
        "karma_per_word": "{:.2f}".format(statistics["karma_per_word"]),
        "avgscore": "{:.1f}".format(statistics["avg_score"]),
        "posts": user_data["posts"],
        "subreddits": statistics["subreddits"],
        "daydata": statistics["by_day"],
        "hourdata": statistics["by_hour"],
        "wordcount": statistics["top_phrases"],
        "recommendations": statistics["recommendations"]
    }
    return jsonify(**payload)


if __name__ == "__main__":
    #app.run()
    port = int(os.environ.get('PORT', 5000))
    serve(app, host="0.0.0.0", port=port)
