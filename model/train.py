import pickle
import logging
import time

from implicit import alternating_least_squares
import numpy as np
import pandas
import scipy.sparse


def load_data(file):
    """
    Read a csv file and creates a sparse coo_matrix.
    """
    df = pandas.read_csv(file)

    df["author"] = df["author"].astype("category")
    df["subreddit"] = df["subreddit"].str.lower()
    df["subreddit"] = df["subreddit"].astype("category")

    post_counts = scipy.sparse.coo_matrix((df["count"].astype(np.float64),
                                           (df["subreddit"].cat.codes.copy(),
                                            df["author"].cat.codes.copy())))

    return df, post_counts


def bm25_weight(X, K1=100, B=0.6):
    """
    Weighs each row of the sparse matrix X by the BM25 ranking function.

    The idea of applying BM25 weighting and the code originally by Ben Frederickson:
    http://www.benfrederickson.com/distance-metrics/

    Args:
        X (coo_matrix): sparse user/item/count matrix.
    Returns:
        Weighted sparse matrix and dictionary containing BM25 parameters.
    """
    # Calculate IDF for each user
    X = scipy.sparse.coo_matrix(X)
    N = X.shape[0]
    idf = np.log(float(N) / (1 + np.bincount(X.col)))

    # Calculate length normalization for each subreddit
    row_sums = np.ravel(X.sum(axis=1))
    average_length = row_sums.mean()
    length_norm = (1.0 - B) + B * row_sums / average_length

    # weight matrix rows by bm25
    X.data = X.data * (K1 + 1.0) / (K1 * length_norm[X.row] + X.data) * idf[X.col]
    params = {
        "K1": K1,
        "B": B,
        "avg_length": average_length,
        "idf": idf
    }
    return X, params


class TopRelated(object):
    def __init__(self, factors):
        # fully normalize artist_factors, so can compare with only the dot product
        norms = np.linalg.norm(factors, axis=-1)
        self.factors = factors / norms[:, np.newaxis]

    def get_related(self, id, n=10):
        scores = self.factors.dot(self.factors[id])
        best = np.argpartition(scores, -n)[-n:]
        return sorted(zip(best, scores[best]), key=lambda x: -x[1])


def train_model(input_filename, output_filename,
                factors=50, regularization=0.01,
                iterations=15, use_native=True,
                cg=True):
    logging.debug("Reading data from %s", input_filename)
    start = time.time()
    df, plays = load_data(input_filename)
    logging.debug("Read data file in %s", time.time() - start)

    logging.debug("Weighting matrix by bm25")
    weighted, params = bm25_weight(plays)
    params["regularization"] = regularization

    logging.debug("Calculating factors")
    start = time.time()
    subr_factors, user_factors = alternating_least_squares(weighted,
                                                           factors=factors,
                                                           regularization=regularization,
                                                           iterations=iterations,
                                                           use_native=use_native,
                                                           dtype=np.float64,
                                                           use_cg=cg)
    logging.debug("Calculated factors in %s", time.time() - start)

    logging.debug("Writing model to disk")
    with open("params.pickle", "wb") as b:
        pickle.dump(params, b)

    subreddits = dict(enumerate(df['subreddit'].cat.categories))

    with open("dict.pickle", "wb") as d:
        pickle.dump(subreddits, d)

    with open("factors.pickle", "wb") as f:
        pickle.dump(subr_factors, f)

    model = TopRelated(subr_factors)
    # Print 10 most similar subreddits for each subreddit to evaluate the model
    with open(output_filename, "w") as out:
        for i, name in subreddits.items():
            related = model.get_related(i)
            for other, score in related:
                out.write("{}\t{}\t{}\n".format(name, subreddits[other], score))

    logging.debug("Training complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    train_model("users.csv", "similarities.txt")
