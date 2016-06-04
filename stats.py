"""
reddit user-analytics app providing insights on how user spends time on reddit.
Author: Rasmus Heikkila 2016
"""


from flask import Flask
from flask import render_template
from flask import request
from pymongo import MongoClient
from waitress import serve

from collections import Counter, defaultdict
import datetime
import logging
import os
import re
import requests
import sys
import time


logFormatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler("syslog.log")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

MONGO_URL = os.environ.get('MONGODB_URI')
if not MONGO_URL:
    MONGO_URL = "mongodb://localhost:27017/rest"
    
app = Flask(__name__)

client = MongoClient(MONGO_URL)
db = client.get_default_database()
coll = db.docs
coll.create_index("username")
logger.info("DB connection established to %s", MONGO_URL)

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
post_limit = 500
word_count_limit = 50


def get_stopwords(filename):
    """
    Retrieves a set of stopwords for word cloud filtering.
    """
    words = set()
    with open(filename, 'r') as f:
        words.update( f.read().splitlines() )
    f.close()
    return words


stopwords = get_stopwords("stopwords.txt")


def is_valid(name):
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
    

def parse_date(secs):
    """
    Parse seconds from epoch into a date string DD/MM/YY
    """
    date = datetime.datetime.fromtimestamp(secs, datetime.timezone.utc)
    return date.strftime("%d/%m/%y")
    
    
def analyze(data):
    """
    Compute some stats from the reddit posts and add them
    to the dictionary passed as the parameter.
    Assumes that posts were found, so data["posts"] does 
    not raise a KeyError.
    """
    total_score = 0
    subreddits = defaultdict(lambda: defaultdict(int))
    hour_count = [0] * 24
    day_count = [0] * 7
    wordcount = defaultdict(int)
    post_count = len(data["posts"])
    
    for post in data["posts"]:
        post = post["data"]
        # Parse seconds from epoch to a datetime object
        secs = int(post["created_utc"])
        dt = datetime.datetime.fromtimestamp(secs, datetime.timezone.utc)
        post["created_utc"] = dt.strftime("%d/%m/%y")
        hour_count[dt.hour] += 1
        day_count[dt.weekday()] += 1
        
        score = int(post["score"])
        total_score += score
        
        sr = post["subreddit"]
        subreddits[sr]["count"] += 1
        subreddits[sr]["score"] += score
        
        try:
            for word in post["body"].split():
                word = re.sub("[^\w]", "", word).lower()
                wordcount[word] += 1
        except KeyError:
            for word in post["selftext"].split():
                word = re.sub("[^\w]", "", word).lower()
                wordcount[word] += 1
    
    # Turn scores into average scores
    for v in subreddits.values():
        v["score"] = round(v["score"] / v["count"], 1)
        
    words = sum(wordcount.values())
    avg_words = words / post_count
    karma_per_word = total_score / words
    avg_score = total_score / post_count
    
    # Filter out stopwords
    c = Counter({k: v for (k,v) in wordcount.items() if k not in stopwords})
    # Get most common words and parse them into a suitable format for D3
    top_words = [{"word": k, "count": v} for (k,v) in c.most_common(word_count_limit)]
    # Make the dictionary into a suitable format for D3
    subreddits = [{"name": k, "data": v} for (k,v) in subreddits.items()]
    
    values = {"avg_score": avg_score,
              "total_score": total_score,
              "avg_words": avg_words,
              "karma_per_word": karma_per_word,
              "hour_count": hour_count,
              "day_count": day_count,
              "subreddits": subreddits,
              "top_words": top_words}
              
    data["computation"] = values
    return data


class RedditStats():
    
    def __init__(self):

        self.headers = {"User-Agent": "u-stats user analytics"}
        self.auth_token = None
        self.token_expiration_time = None
        
        success = self.auth()
        if not success:
            sys.exit("Could not establish connection with reddit API")
      
        
    def auth(self, retries=2):
        """
        Authenticates with reddit API. The access token is valid for 60 minutes.
        Returns boolean based auth on success.
        """
        if retries == 0:
            return False
            
        client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)   
        post_data = {"grant_type": "client_credentials",
                     "duration": "permanent"}   
                     
        try:
            r = requests.post("https://www.reddit.com/api/v1/access_token",
                              auth=client_auth, data=post_data, headers=self.headers, timeout=3)
            r_json = r.json()
            self.auth_token = r_json["access_token"]
            self.token_expiration_time = int(time.time()) + r_json["expires_in"]
            self.headers["Authorization"] = r_json["token_type"] + " " + self.auth_token
            logger.info("%s successful", "Auth")
            return True
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout) as e:
            logger.error("Auth error: %s", str(e))
            return self.auth(retries=retries-1)
        except Exception as e:
            logger.error("Auth error: %s", str(e))
            return False
            
    def retrieve_data(self, username, retries=2, force_reauth=False):
        """
        Retrieve user information and latest posts from the reddit API.
        Returns a dictionary containing username, some basic user information
        and latest posts. In case of failure, returns None.
        """
        if retries == 0:
            return None
        
        if (int(time.time()) >= self.token_expiration_time or force_reauth):
            self.auth()
        
        url = "https://oauth.reddit.com/user/" + username
        posts_per_request = 100
        p = {"limit": posts_per_request}
        posts = []
        posts_received = 0
    
        try:
            r_info = requests.get(url + "/about", headers=self.headers, timeout=3)
            r_info.raise_for_status()
            user_info = r_info.json()["data"]
            
            while posts_received < post_limit:
                r_posts = requests.get(url + "/overview", headers=self.headers, params=p, timeout=3)
                r_posts.raise_for_status()
                
                post_batch = r_posts.json()["data"]["children"]
                posts.extend(post_batch)
                
                # Add name of last post to params to get next set of posts 
                p["after"] = post_batch[-1]["data"]["name"] 
                
                l = len(post_batch)
                posts_received += l
                
                if l < posts_per_request:
                    break
            
            data = {"info": user_info,
                    "username": username,
                    "refreshed": parse_date( int(time.time()) )}
            if posts:
                data["posts"] = posts
            
            return data
        
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 401:
                return self.retrieve_data(username, retries=retries-1, force_reauth=True)
            elif code == 404:
                return None
            else:
                return self.retrieve_data(username, retries=retries-1)
        except KeyError:
            """
            If we don't get HTTP error and end up here, 
            most likely posts are missing.
            Catch this in handle_data function for proper error messaging
            """
            raise
        except Exception as e:
            logger.error("Error retrieving data: %s", str(e))
            return self.retrieve_data(username, retries=retries-1)
        
    
    def handle_data(self, username, refresh):
        """
        Returns dictionary containing all data. If refresh is not forced,
        attempts to retrieve data from mongoDB before connecting to reddit API.
        """
        def write_to_db(username):
            try:
                data = self.retrieve_data(username)
            except KeyError:
                return "No posts were found!"
            
            if not data:
                return "Failed to retrieve data! Does the username even exist?"           
            
            data = analyze(data)
            res = coll.replace_one({"username": username}, data, upsert=True)
            if not res.acknowledged:
                logger.warning("Failed to write %s's data to db", username)
            return data
            
        if refresh:
            return write_to_db(username)
        else:
            res = coll.find_one({"username": username})
            if not res:
                return write_to_db(username)
            else:
                return res         

                
def handle_request(username, refresh):             
    if not is_valid(username):
        return render_template("index.html", message="Invalid username.")
        
    # Attempt to get data from db or reddit API
    userdata = s.handle_data(username, refresh)
    
    if not userdata:
        return render_template("index.html", message="Something went wrong.")
    elif type(userdata) is str:
        return render_template("index.html", message=userdata)
    
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hour_labels = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00",
                   "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                   "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                   "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]
    try:
        stats = userdata["computation"]
        
        # Parse day and hour distributions to the format required by radar chart
        daydata = [{"axis": k, "value": v} for (k,v) in zip(day_labels, stats["day_count"])]
        daydata = [{"axes": daydata}]
        hourdata = [{"axis": k, "value": v} for (k,v) in zip(hour_labels, stats["hour_count"])]
        hourdata = [{"axes": hourdata}]
        
        return render_template("stats.html",
                               user = username,
                               postcount = len(userdata["posts"]),
                               refreshed = userdata["refreshed"],
                               account_created = parse_date( int(userdata["info"]["created_utc"]) ),
                               oldest_post_date = userdata["posts"][-1]["data"]["created_utc"],
                               total_karma = stats["total_score"],
                               words_per_post = "{:.1f}".format(stats["avg_words"]),
                               karma_per_word = "{:.2f}".format(stats["karma_per_word"]),
                               avgscore = "{:.1f}".format(stats["avg_score"]),
                               posts = userdata["posts"],
                               subreddits = stats["subreddits"],
                               daydata = daydata,
                               hourdata = hourdata,
                               wordcount = stats["top_words"])  
    except KeyError:
        # Something must be missing from the file, refresh it
        return handle_request(username, True)
    
    
@app.route("/")
def home():
    return render_template("index.html", message="")
        

@app.route("/stats")
def stats():
    u_input = request.args.get("username", "")
    return handle_request(u_input, False)
    

@app.route("/refresh")
def refresh():
    u_input = request.args.get("username", "")
    return handle_request(u_input, True)

         
          
if __name__ == "__main__":
    s = RedditStats()
    #app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    serve(app, host="0.0.0.0", port=port)
        