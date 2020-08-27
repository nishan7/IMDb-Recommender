It is the python software used to recommend movies/tv-series based on other movie/
tv-series your like.

It is based on the imdb dataset. https://datasets.imdbws.com/

It uses cosine similarity between movies/tv-series to find similarity between the movies.

Then based on user's personal movies choice and cosine similarity of those movies, it generates the recommenadations.

It uses PyQt5 for the GUI interfaces.


### Features
<ul>Gui interface to interact</ul>
<ul>Recommended movies have link to google/imdb </ul>


## How to run
```
pip install -r requirements.txt
python gui.py
```

##
### Screenshot

<img src="https://github.com/nishan7/IMDb-Recommender/blob/master/demo.jpg" alt="sample" width="500"/>
<img src="https://github.com/nishan7/IMDb-Recommender/blob/master/demo_series.jpg" alt="sample2" width="500"/>



