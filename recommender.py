import pickle
import sys

import numpy as np
import scipy.sparse

factors_file = "model/factors.pickle"
params_file = "model/params.pickle"
vectorizer_file = "model/dict.pickle"


class Recommender(object):
    """
    Recommends subreddits given a vector of post counts.

    This recommender uses a pretrained implicit matrix factorization model.
    The class is initialized from three files:
    - matrix of item (subreddit) factors
    - parameters of BM25 ranking and regularization
    - dictionary mapping indices to subreddit names
    """
    def __init__(self):
        try:
            with open(factors_file, "rb") as f:
                factors = pickle.load(f)
            norms = np.linalg.norm(factors, axis=-1)
            self.factors = factors / norms[:, np.newaxis]
            self.f = self.factors.shape[1]
            # Precompute factor matrix product and add regularization
            self.A = self.factors.T.dot(self.factors) + 0.01 * np.eye(self.f)

            with open(params_file, "rb") as b:
                params = pickle.load(b)
            self.K1 = params["K1"]
            self.B = params["B"]
            self.avg_len = params["avg_length"]
            self.idf = params["idf"]
            self.regularization = params["regularization"]

            with open(vectorizer_file, "rb") as d:
                self.inverse_vectorizer = pickle.load(d)
            # Pickled file contains inverse transformation (idx -> subreddit),
            # we also need (subreddit -> idx)
            self.vectorizer = dict((v, k) for k, v in self.inverse_vectorizer.items())
        except (FileNotFoundError, KeyError) as e:
            sys.exit("Model missing: {}".format(str(e)))
        except:
            raise

    def _bm25(self, x):
        """
        Weight the observed post counts in different subreddits using the BM25 ranking function.

        Args:
            x (coo_matrix): Sparse data vector x
        Returns:
            Weighted sparse data vector
        """
        row_sum = x.sum()
        length_norm = (1.0 - self.B) + self.B * row_sum / self.avg_len
        x.data = x.data * (self.K1 + 1.0) / (self.K1 * length_norm + x.data) * self.idf[x.col]
        return x

    def _user_weights(self, c):
        """
        Calculates user weights based on confidence vector and item factors.

        Args:
            c: vector containing confidence that user likes the items
        Returns:
            vector of user
        """
        A = self.A
        b = np.zeros(self.f)
        nonzero = np.nonzero(c)
        c = c.tocsr()
        for i in np.nditer(nonzero):
            factor = self.factors[i[1]]
            confidence = c[i]
            A += (confidence - 1.0) * np.outer(factor, factor)
            b += confidence * factor

        return np.linalg.solve(A, b)

    def get_similar(self, post_counts, n=15):
        """
        Recommends subreddits based on the implicit matrix factorization model.

        Args:
            post_counts: a dictionary of (subreddit, postcount) pairs.
            n: number of returned subreddits
        Returns:
            list of subreddits (strings) with best recommendation first
        """
        post_counts = dict((k.lower(), v) for k, v in post_counts.items())
        counts = list()
        indices = list()
        for k, v in post_counts.items():
            idx = self.vectorizer.get(k)
            if idx:
                counts.append(v)
                indices.append(idx)

        data = np.array(counts)
        row = np.zeros(len(counts))
        col = np.array(indices)
        p = scipy.sparse.coo_matrix((data, (row, col)))

        weighted = self._bm25(p)
        preferences = self._user_weights(weighted)
        recommendations = self.factors.dot(preferences)
        indices = recommendations.argsort()[::-1]

        result = list()
        for i in indices:
            subr = self.inverse_vectorizer[i]
            if subr not in post_counts.keys():
                result.append(subr)
            if len(result) == n:
                break

        return result
