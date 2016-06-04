"""
NLP system for extracting key words/phrases from text. The system tokenizes 
strings, classifies each token and finds the keyphrases based on the 
classification tags. 
"""
import nltk

import itertools
import re


# Tokenization regexp from the NLTK Book
pattern = r"""(?x)
              (?:[A-Z]\.)+           # abbreviations, e.g. U.S.A.
              |\d+(?:\.\d+)?%?       # numbers, incl. currency and percentages
              |\w+(?:[-']\w+)*       # words w/ optional internal hyphens/apostrophe
              |(?:[+/\-@&*])         # special characters with meanings
"""


pos_pattern = r"""
    KP: {(<JJ>* <NN.*>+ <IN>)? <JJ>* <NN.*>+}
"""


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
tokenizer = nltk.tokenize.RegexpTokenizer(pattern)
wnl = nltk.WordNetLemmatizer()


def normalise(word):
    word = word.lower()
    word = wnl.lemmatize(word)
    return word
    
    
def good_phrase(phrase):
    if re.sub('[^A-Za-z0-9]+', '', phrase) in stopwords:
        return False
    if "/" in phrase or "*" in phrase:
        return False
    return True
    
 
def extract_chunks(text):
    """
    Extract possible keyphrases from a text string.
    Returns a list of candidate keyphrases and the count of tokens created overall.
    """
    chunker = nltk.RegexpParser(pos_pattern)
    
    tokens = tokenizer.tokenize(text)
    count = len(tokens)
    pos_tokens = nltk.pos_tag(tokens)
    
    all_chunks = chunker.parse(pos_tokens)
    
    # Get key phrases from all chunks
    kp_chunks = (subtree.leaves() for subtree in 
                 all_chunks.subtrees(filter = lambda t: t.label() == "KP"))
                 
    # Join the words of key phrases, normalising in the process
    kp_candidates = (" ".join(normalise(word) for word, tag in chunk) 
                     for chunk in kp_chunks)

    candidates = [phrase for phrase in kp_candidates if good_phrase(phrase)]
                  
    return candidates, count
    
    
def rank_keyphrases(texts, top_n=50):
    """
    Rank keyphrases with a simple frequency distribution. This approach
    favours unigrams, which is fine since unigrams are better suited 
    for a word cloud.
    Parameters:
    texts - an iterable of strings
    top_n - number of keyphrases returned. If the amount of text is insufficient,
    less than top_n keyphrases might be returned.
    Returns: 
    The keyphrases and a total count of words tokenized.
    """
    kp_lists = [extract_chunks(text) for text in texts]
    words = list(itertools.chain.from_iterable(l for l,_ in kp_lists))
    fd = nltk.FreqDist(words)
    
    # Count the total number of tokens created using keyphrase extraction
    word_count = sum(c for _,c in kp_lists)
    
    # If there are few keyphrases, take top 20% instead of the specified top_n
    n = min(top_n, int(fd.B() / 5))
    
    keyphrases = fd.most_common(n)
    # Return the rank as a frequency among keyphrase candidates
    return keyphrases, word_count
    
    
    