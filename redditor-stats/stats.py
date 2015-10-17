"""
reddit user-analytics app providing insights on how user spends time on reddit.
Author: Rasmus Heikkila 2015
"""

from collections import Counter, defaultdict
from flask import Flask
from flask import render_template
from flask import request
from waitress import serve

import datetime
import os
import re
import requests

app = Flask(__name__)

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
post_limit = 100
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


@app.route("/")
def home():
    return render_template("index.html", message="")


@app.route("/")
class StatsEngine():
    
    def __init__(self):
        """
        Authenticates with reddit API.
        """
        self.headers = {"User-Agent": "u-stats user analytics"}
        self.auth_token = None
        self.userinfo = None
        self.posts = None
        self.post_count = 0
        self.errormsg = ""
        
        client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
        post_data = {"grant_type": "client_credentials"}
        try:
            r = requests.post("https://www.reddit.com/api/v1/access_token",
                              auth=client_auth, data=post_data, headers=self.headers, timeout=3)
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout):
            self.errormsg = "Reddit API is not responding, please try again."
            
        r_json = r.json()
        self.auth_token = r_json["access_token"]
        self.headers["Authorization"] = r_json["token_type"] + " " + self.auth_token
        
    def info(self, username):
        """
        Gets basic user info: comment karma, link karma and reddit gold status.
        Parameters:
        username -- user name as a string
        """
        url = "https://oauth.reddit.com/user/" + username + "/about"
        r = requests.get(url, headers=self.headers)
        r_json = r.json()
        try:
            self.userinfo = r_json["data"]
        except KeyError:
            self.errormsg = "Error: Some information could not be received!"
        
    def overview(self, username):
        """
        Get max 100 latest comments/submits for a user.
        Parameters:
        username -- user name as a string
        """
        url = "https://oauth.reddit.com/user/" + username + "/overview"
        p = {"limit": post_limit}
        r = requests.get(url, headers=self.headers, params=p)
        r_json = r.json()
        try:
            self.posts = r_json["data"]["children"]
            self.post_count = len(self.posts)
        except KeyError:
            pass
        
    def data(self):
        """
        Extract some stats from the latest max 100 posts.
        """
        total_score = 0
        subreddits = defaultdict(lambda: defaultdict(int))
        hour_count = [0] * 24
        day_count = [0] * 7
        wordcount = defaultdict(int)
        
        for post in self.posts:
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
        avg_words = words / self.post_count
        karma_per_word = total_score / words
        avg_score = total_score / self.post_count
        
        # Filter out stopwords
        c = Counter({k: v for (k,v) in wordcount.items() if k not in stopwords})
        # Get most common words and parse them into a suitable format for D3
        top_words = [{"word": k, "count": v} for (k,v) in c.most_common(word_count_limit)]
        # Make the dictionary into a suitable format for D3
        subreddits = [{"name": k, "data": v} for (k,v) in subreddits.items()]
        
        return (avg_score, total_score, avg_words, karma_per_word, hour_count,
                day_count, subreddits, top_words)
        

@app.route("/stats")
def statistics():
    u_input = request.args.get("username", "")
    if not is_valid(u_input):
        return render_template("index.html", message="Invalid username.")
        
    s = StatsEngine()
    if s.errormsg:
        return render_template("index.html", 
                               message="Reddit API is not responding, please try again.")
        
    s.info(u_input)
    s.overview(u_input)
    if not s.posts:
        return render_template("index.html", 
                               message="No posts were found! Does the user even exist?")
        
    (a_score, t_score, avg_words, karma_per_word, h_count, d_count, subreddits, wordcount) = s.data()
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hour_labels = ["00:00",
                   "01:00",
                   "02:00",
                   "03:00",
                   "04:00",
                   "05:00",
                   "06:00",
                   "07:00",
                   "08:00",
                   "09:00",
                   "10:00",
                   "11:00",
                   "12:00",
                   "13:00",
                   "14:00",
                   "15:00",
                   "16:00",
                   "17:00",
                   "18:00",
                   "19:00",
                   "20:00",
                   "21:00",
                   "22:00",
                   "23:00"]
       
    # Parse day and hour distributions to the format required by radar chart
    daydata = [{"axis": k, "value": v} for (k,v) in zip(day_labels, d_count)]
    daydata = [{"axes": daydata}]
    hourdata = [{"axis": k, "value": v} for (k,v) in zip(hour_labels, h_count)]
    hourdata = [{"axes": hourdata}]
    
    return render_template("stats.html",
                           user = u_input,
                           postcount = s.post_count,
                           errormessage = s.errormsg,
                           account_created = parse_date( int(s.userinfo["created_utc"]) ),
                           oldest_post_date = s.posts[-1]["data"]["created_utc"],
                           total_karma = t_score,
                           words_per_post = "{:.1f}".format(avg_words),
                           karma_per_word = "{:.2f}".format(karma_per_word),
                           avgscore = "{:.1f}".format(a_score),
                           posts = s.posts,
                           subreddits = subreddits,
                           daydata = daydata,
                           hourdata = hourdata,
                           wordcount = wordcount)              
        
        
if __name__ == "__main__":
    #app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    serve(app, host="0.0.0.0", port=port)
        