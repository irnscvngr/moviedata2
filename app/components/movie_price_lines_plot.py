import plotly.express as px
import pandas as pd
from moviedata.core.database import pg_connect



class medimops_price_analyzer:
    """
    """
    def __init__(self, movie_titles: list=None):
        self.movie_titles = movie_titles
        self.pg = None
        self.df_movie_prices = None

    def analyze_price_lines(self):
        """
        Get product lines from up to 8 weeks back and analyze prices
        """
        if self.pg is None:
            pg = pg_connect()

        # ------------------------------------------------------------
        # GET ALL PRICES FROM UP TO 8 WEEKS BACK

        df_recent_prices = pg.sql_query(f"""
            SELECT *
            FROM medimops.product_lines
            WHERE load_timestamp >= NOW() - INTERVAL '8 weeks';
            """
        )
        self.df_recent_prices = df_recent_prices
        # ------------------------------------------------------------
        # GET AVERAGE PRICES OF FULL DF PER PRODUCT (=8 weeks)

        df_recent_prices_avg = (
            df_recent_prices
            .groupby('product_link')
            .agg(
                row_count=('product_link', 'count'),
                product_title=('product_title', 'first'),
                price_8w_avg=('product_price_desktop', 'mean'),
                letterboxd_name=('letterboxd_name', 'first'),
                letterboxd_uri=('letterboxd_uri','first')
                )
        )
        # ------------------------------------------------------------
        # GET LATEST PRICES OF FULL DF PER PRODUCT

        df_recent_prices_latest = (
            df_recent_prices
            .sort_values(['product_link','load_timestamp'],ascending=False)
            .groupby('product_link')
            .agg({
                'product_title':'first',
                'product_price_desktop':'first'
            })
            .rename(columns={'product_price_desktop':'price_latest'})
        )
        # ------------------------------------------------------------
        # JOIN DFs AND DIVIDE LATEST PRICE BY 8 WEEK AVERAGE

        df_price_compare = (
            df_recent_prices_avg
            .join(df_recent_prices_latest.drop(columns=['product_title']))
        )

        df_price_compare['price_ratio'] = df_price_compare['price_latest']/df_price_compare['price_8w_avg']

        self.df_price_compare = df_price_compare


        return df_price_compare


    def plot_price_lines(self, df, x='date', y='price_desktop_min', color='letterboxd_uri', hover_data='letterboxd_name'):
        fig = px.line(
            data_frame=df,
            x=x,
            y=y,
            color=color,
            hover_data=hover_data,
            markers=True
            )

        # Build a lookup dictionary to rename legend items
        label_map = dict(zip(df[color].astype(str), df[hover_data]))

        fig.for_each_trace(lambda trace: trace.update(name=label_map.get(trace.name, trace.name)))

        fig.update_layout(
            legend=dict(
                orientation="h",  # Horizontal layout
                yanchor="bottom",  # Anchor legend's bottom edge to 'y'
                y=1.02,  # Position slightly above the plot area (1.0 = top boundary)
                xanchor="center",  # Center horizontally
                x=0.5,  # Place at 50% width
                title_text=None
            ),
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(
                b=0,  # Reduce bottom margin (default is around 80px)
                t=20,  # Top margin (optional)
                l=20,  # Left margin (optional)
                r=20   # Right margin (optional)
            )
        )
        return fig