import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from moviedata.core.database import pg_connect

class image_grid:
    """
    Class that distributes movie-posters on a grid
    """
    def __init__(self, size_x=10, size_y=10):
        """
        """
        self.gridsize = (size_x, size_y)
        self.grid = np.zeros((size_x, size_y))

    def init_dataset(self, source='database'):
        """
        Get 'ratings' dataset of Letterboxd from postgres database
        """
        if source=='database':
            pg = pg_connect()
            df = pg.sql_query("""
                SELECT
                a.name,
                a.year,
                a.letterboxd_uri,
                a.rating,
                b.duration,
                b.genres,
                b.poster
                FROM letterboxd.ratings a
                LEFT JOIN letterboxd.lb_all_movies_metadata b
                ON a.letterboxd_uri = b.letterboxd_uri
                ORDER BY rating DESC
            """)

        self.dataset = df

    def populate_grid(self):
        """
        Method to populate the grid, potentially using something like
        - treemap
        - mosaic grid packing
        - frontier packing (organic island expansion)
        """
        self.grid += np.random.random(size=self.grid.shape)

    def visualize(self):
         """
         Visualize the grid
         """
         aspect_ratio = self.gridsize[0]*1.0/self.gridsize[1]
         fig = plt.figure(figsize=(10,10*aspect_ratio))
         sns.heatmap(self.grid)
         plt.show()


ig = image_grid()
# ig.init_dataset()
ig.populate_grid()
ig.visualize()
