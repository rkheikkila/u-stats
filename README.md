# u-stats
u-stats is a service providing analytics on redditors' activity.
Hosted on Heroku at http://u-stats.herokuapp.com/.

## Features

u-stats visualizes users' past activity and provides insight into how users' spend time on reddit. Posts are grouped by subreddit, weekday and hour. 

The service also features a recommendation system that recommends new subreddits based on past activity. This is a collaborative filtering model based on [implicit feedback matrix factorization](http://yifanhu.net/PUB/cf.pdf) and trained on the 2015 post statistics of over 600 000 reddit users on the 2 000 most popular subreddits. The training data was retrieved with Google BigQuery.

The backend and analytics processing is written in Python, and the website with jQuery and D3.js. 

## Dependencies
- Flask
- Flask-PyMongo
- requests (interfacing with reddit API)
- waitress (WSGI server)
- nltk 
- [implicit](https://github.com/benfred/implicit) (recommendation system training, not required by the web app)




