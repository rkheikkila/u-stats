from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import requests
import sys
import time

from app import app
from analytics import parse_date

# Upper limit to number of posts retrieved from reddit
post_limit = 500


class RedditAPI(object):
    def __init__(self, client_id, client_secret):

        self.headers = {"User-Agent": "u-stats reddit user analytics"}
        self.auth_token = None
        self.token_expiration_time = None
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        self.api_url = "https://oauth.reddit.com/user/"
        self.api_id = client_id
        self.api_secret = client_secret
        # Reddit API allows 60 requests per minute
        self.requests_remaining = 60
        # Seconds to API ratelimit reset
        self.ratelimit_reset = 60

        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

        success = self._auth()
        if not success:
            sys.exit("Could not establish connection with reddit API")

    def _auth(self):
        """
        Authenticates with reddit API. The access token is valid for 60 minutes.
        Returns boolean based auth on success.
        """
        try:
            client_auth = requests.auth.HTTPBasicAuth(self.api_id, self.api_secret)
            post_data = {"grant_type": "client_credentials",
                         "duration": "permanent"}
            response = self.session.post(self.auth_url, auth=client_auth, data=post_data, headers=self.headers)
            response_json = response.json()
            self.auth_token = response_json["access_token"]
            self.token_expiration_time = int(time.time()) + response_json["expires_in"]
            self.headers["Authorization"] = response_json["token_type"] + " " + self.auth_token
            app.logger.info("Authorization successful")
            return True
        except Exception as e:
            app.logger.error("Failed to authorize: %s", str(e))
            return False

    def _send_request(self, url, params, retries=1):
        """
        Send a HTTP GET request to the reddit API.

        Args:
            url: target url
            params: request parameters
            retries: number of retries
        Returns:
            Retrieved data as a dictionary or dictionary with key "error"
        """
        if not retries:
            return {"error": "Timeout"}

        now = int(time.time())

        if now >= self.token_expiration_time:
            self._auth()
        if now - self.ratelimit_reset > 60:
            self.ratelimit_reset = now
            self.requests_remaining = 60

        if self.requests_remaining < 10:
            delay = self.ratelimit_reset / self.requests_remaining
            time.sleep(delay)

        try:
            response = self.session.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            self.requests_remaining -= 1
            return response.json()
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 401:
                self._auth()
            return self._send_request(url, params, retries-1)
        except Exception as e:
            app.logger.error("Error retrieving data: %s", str(e))
            return {"error": str(e)}

    def user(self, username):
        """
        Retrieve user information and latest posts from the reddit API.

        Args:
            username: reddit username, expected to be valid but not necessarily existent
        Returns:
            dictionary containing username, some basic user information, time or retrieval
            and latest posts.
            If an exception is countered, returns a dictionary with key "error"
        """

        url = self.api_url + username
        posts_per_request = 100
        p = {"limit": posts_per_request}
        posts = []
        posts_received = 0

        try:
            response = self._send_request(url + "/about", p)
            if "error" in response:
                return response

            user_info = response["data"]

            while posts_received < post_limit:
                post_response = self._send_request(url + "/overview", p)
                if "error" in post_response:
                    return post_response

                post_batch = post_response["data"]["children"]
                posts.extend(post_batch)

                # Add name of last post to params to get next set of posts
                p["after"] = post_batch[-1]["data"]["name"]

                l = len(post_batch)
                posts_received += l

                if l < posts_per_request:
                    break

            data = {"info": user_info,
                    "username": username,
                    "refreshed": parse_date(int(time.time()))}
            if posts:
                data["posts"] = posts

            return data

        except Exception as e:
            app.logger.error("Some data could not be retrieved: %s", str(e))
            return {"error": str(e)}


api = RedditAPI(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])