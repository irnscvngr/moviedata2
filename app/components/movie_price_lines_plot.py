import plotly.express as px
import pandas as pd
from moviedata.core.database import pg_connect



class medimops_price_analyzer:
    """
    """
    def __init__(self, movie_titles: list):
        self.movie_titles = movie_titles
        self.pg = None
        self.df_movie_prices = None

    def get_movie_prices(self, movie_select: list):
        """
        Get price lines dataframe for selected movies
        """
        self.movie_select = movie_select

        # Escape single quotes in strings to avoid syntax errors/SQL injection
        safe_list = [s.replace("'", "''") for s in movie_select]
        # Format as comma-separated single-quoted values
        formatted_items = ", ".join(f"'{item}'" for item in safe_list)

        if self.pg is None:
            pg = pg_connect()

        df_movie_prices = pg.sql_query(f"""
            SELECT *
            FROM medimops.movie_price_lines
            WHERE letterboxd_name IN ({formatted_items});
            """
        )

        self.df_movie_prices = df_movie_prices
        return df_movie_prices

    def get_cheap_movies(self, cnt=5):
        """
        Gets price data of movies whose price is below 4 week average
        """
        if self.pg is None:
            pg = pg_connect()

        df_movies_cheap = pg.sql_query(f"""
        SELECT *
        FROM medimops.movie_price_evaluation
        LIMIT {cnt};
        """
        )

        self.df_movies_cheap = df_movies_cheap
        return df_movies_cheap

    def plot_price_lines(self):
        fig = px.line(
            data_frame=self.df_movie_prices,
            x="date",
            y="price_desktop_min",
            color="letterboxd_name",
            markers=True
            )

        fig.update_layout(
            legend=dict(
                orientation="h",  # Horizontal layout
                yanchor="bottom",  # Anchor legend's bottom edge to 'y'
                y=1.02,  # Position slightly above the plot area (1.0 = top boundary)
                xanchor="center",  # Center horizontally
                x=0.5,  # Place at 50% width
                title_text=None
            )
        )
        return fig