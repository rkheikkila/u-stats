from collections import defaultdict
import datetime
import time

from recommender import Recommender
import textminer

recommender = Recommender()

# Upper limit of phrases to display in word cloud
word_limit = 50

day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
hour_labels = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00",
               "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
               "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
               "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]


def parse_date(secs):
    """
    Parse seconds from epoch into a date string DD/MM/YY
    """
    date = datetime.datetime.fromtimestamp(secs, datetime.timezone.utc)
    return date.strftime("%d/%m/%y")


def get_post_text(posts):
    """
    Helper function for retrieving text content of posts.

    Args:
        posts: list of dictionaries
    Returns:
        generator of strings (post content)
    """
    for post in posts:
        post_data = post["data"]
        try:
            yield post_data["body"]
        except:
            yield post_data["selftext"]


def process(data):
    """
    Computes certain statistics from a user's post data.

    Args:
        data: dictionary containing key "posts".
    Data includes:
    - Post count and average karma by subreddit
    - Post count by day and hour
    - Frequent keyphrases

    Returns:
        Original dictionary with new dictionary under key "analytics"
        If key "posts" is missing from data, returns the dictionary unchanged
    """
    if not data.get("posts"):
        return data

    total_score = 0
    subreddits = defaultdict(lambda: defaultdict(int))
    hour_count = [0] * 24
    day_count = [0] * 7
    post_count = len(data["posts"])

    post_strings = get_post_text(data["posts"])
    top_phrases, wordcount = textminer.rank_keyphrases(post_strings, word_limit)

    for post in data["posts"]:
        post = post["data"]
        # Parse seconds from epoch to a datetime object
        secs = int(post["created_utc"])
        dt = datetime.datetime.fromtimestamp(secs, datetime.timezone.utc)
        post["created_utc"] = dt.strftime("%d/%m/%y")
        hour_count[dt.hour] += 1
        day_count[dt.weekday()] += 1

        score = int(post["score"]) - 1
        total_score += score

        sr = post["subreddit"]
        subreddits[sr]["count"] += 1
        subreddits[sr]["score"] += score

    # Turn scores into average scores
    for v in subreddits.values():
        v["score"] = round(v["score"] / v["count"], 1)

    avg_words = wordcount / post_count
    karma_per_word = total_score / wordcount
    avg_score = total_score / post_count

    counts = dict((k, v["count"]) for k, v in subreddits.items())
    recommended = recommender.get_similar(counts)

    # Parse list of top_phrases into a suitable format for D3
    top_phrases = [{"word": k, "count": v} for (k, v) in top_phrases]
    # Make the subreddit dictionary into a suitable format for D3
    subreddits = [{"name": k, "data": v} for (k, v) in subreddits.items()]

    day_data = [{"axis": k, "value": v} for (k, v) in zip(day_labels, day_count)]
    day_data = [{"axes": day_data}]
    hour_data = [{"axis": k, "value": v} for (k, v) in zip(hour_labels, hour_count)]
    hour_data = [{"axes": hour_data}]

    values = {"avg_score": avg_score,
              "total_score": total_score,
              "avg_words": avg_words,
              "karma_per_word": karma_per_word,
              "by_hour": hour_data,
              "by_day": day_data,
              "subreddits": subreddits,
              "top_phrases": top_phrases,
              "recommendations": recommended}

    data["analytics"] = values
    return data






