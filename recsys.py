import pandas as pd
import numpy as np

imdb = pd.read_csv('datasets/imdb.csv', low_memory=False)

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

cv = CountVectorizer(dtype=np.uint8)
MMS = MinMaxScaler()

imdb['genres'] = [genre.replace(',', ' ') for genre in imdb['genres']]
dtm = cv.fit_transform(imdb['genres']).toarray()

# reshape(-1,1) is equivalent to transpose
new_matrix = np.concatenate((dtm, np.array(imdb['averageRating']).reshape(-1, 1)), axis=1)

numVotes = np.array(imdb['numVotes']).reshape(-1, 1)
numVotes = MMS.fit_transform(numVotes)

new_matrix = np.concatenate((new_matrix, numVotes), axis=1)

similarities = cosine_similarity(new_matrix)

# Main Functions to get Recommendations
def get_recoms(titles_ids, type='movie'):
    number_of_titles = len(titles_ids)
    sim = similarities[titles_ids].sum(axis=0).argsort()[::-1][
          number_of_titles:500]  # To omit recommending the input movies
    tv_similar = [(imdb['title'].iloc[index], imdb['tconst'].iloc[index]) for index in sim if
                  imdb['titleType'].iloc[index] == 'series']
    movie_similar = [(imdb['title'].iloc[index], imdb['tconst'].iloc[index]) for index in sim if
                     imdb['titleType'].iloc[index] == 'movie']

    if type == 'movie':
        return movie_similar[:10]
    else:
        return tv_similar[:10]


if __name__=='__main__':
    print(get_recoms([8838, 7600, 134344134, 23442]))
