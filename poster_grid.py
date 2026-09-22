import io
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
from PIL import Image
from sklearn.cluster import KMeans
from moviedata.core.database import pg_connect


def get_dominant_color(url: str, k: int = 3, resize_dim: tuple = (200, 200)) -> tuple:
    """Download an image from a URL and extract its primary dominant color (RGB).

    :param url: Web link to the JPG file.
    :param k: Number of color clusters to compute (higher = more fine-grained).
    :param resize_dim: Resize dimension to speed up clustering calculation.
    :return: (R, G, B) tuple of the dominant color.
    """
    # 1. Download image from URL
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # 2. Open image with Pillow and convert to RGB
    image = Image.open(io.BytesIO(response.content)).convert("RGB")

    # 3. Downsample image to speed up k-means processing
    image = image.resize(resize_dim)

    # 4. Reshape pixel matrix to a list of (R, G, B) vectors
    np_image = np.array(image)
    pixels = np_image.reshape(-1, 3)

    # 5. Fit KMeans to find cluster centers
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(pixels)

    # 6. Find the cluster with the highest number of assigned pixels
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    dominant_cluster_idx = labels[np.argmax(counts)]

    # 7. Convert dominant RGB color values to integer tuple
    dominant_color = tuple(
        int(c) for c in kmeans.cluster_centers_[dominant_cluster_idx]
    )

    return dominant_color

import io
import cv2
import numpy as np
import requests
from PIL import Image
from sklearn.cluster import KMeans

def get_hsv_dominant_color(
    url: str,
    k: int = 4,
    resize_dim: tuple = (150, 150),
    saturation_boost: float = 1.5,
    min_saturation: int = 25,  # 0 to 255 (filters out dull grays/blacks)
    min_value: int = 30,       # 0 to 255 (filters out pitch black background)
) -> tuple:
    """Extract perceptually dominant color using HSV color space and saturation weighting.

    :param url: Image URL.
    :param k: Number of KMeans clusters.
    :param saturation_boost: Exponent to favor saturated/accent colors.
    :param min_saturation: Minimum S value (0-255) to consider a pixel colorful.
    :param min_value: Minimum V value (0-255) to consider a pixel non-black.
    :return: (R, G, B) tuple.
    """
    # 1. Download image
    response = requests.get(url, stream=True)
    response.raise_for_status()

    pil_img = Image.open(io.BytesIO(response.content)).convert("RGB")
    pil_img = pil_img.resize(resize_dim)

    # 2. Convert to OpenCV BGR and then HSV
    img_rgb = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Reshape pixels: shape (N, 3) where columns are [H, S, V]
    # In OpenCV HSV: H in [0, 179], S in [0, 255], V in [0, 255]
    pixels_hsv = img_hsv.reshape(-1, 3)

    # 3. Filter out non-colorful pixels (near black, near white, pure gray)
    # This leaves only pixels that carry actual color information
    color_mask = (pixels_hsv[:, 1] >= min_saturation) & (pixels_hsv[:, 2] >= min_value)
    filtered_pixels = pixels_hsv[color_mask]

    # Fallback if image is completely monochrome/grayscale
    if len(filtered_pixels) < 100:
        filtered_pixels = pixels_hsv

    # 4. K-Means clustering on HSV values
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)

    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    cluster_centers = kmeans.cluster_centers_

    # 5. Score clusters: Count * (Saturation / 255)^boost
    # Value is used mildly so dark warm colors aren't totally discarded
    scores = []
    for idx, count in zip(labels, counts):
        h, s, v = cluster_centers[idx]

        # Normalize S and V to [0.0, 1.0]
        s_norm = s / 255.0
        v_norm = v / 255.0

        # Primary score driver is Saturation, lightly scaled by Value
        # A dark red (high S, medium V) gets a high score.
        score = count * (s_norm ** saturation_boost) * (v_norm ** 0.5)
        scores.append(score)

    # 6. Select winning cluster and convert HSV -> BGR -> RGB
    winning_idx = labels[np.argmax(scores)]
    winning_hsv = np.uint8([[cluster_centers[winning_idx]]])
    winning_bgr = cv2.cvtColor(winning_hsv, cv2.COLOR_HSV2BGR)[0][0]

    dominant_rgb = (int(winning_bgr[2]), int(winning_bgr[1]), int(winning_bgr[0]))
    return dominant_rgb

def rgb_to_hex(rgb: tuple) -> str:
    """Utility to convert (R, G, B) to Hex color code."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


class image_grid:
    """
    Class that distributes movie-posters on a grid
    """
    def __init__(self, size_x=10, size_y=10):
        """
        """
        self.gridsize = (size_x, size_y)
        self.grid = np.ones((size_x, size_y))*(-1)

    def load_moviedata(self, source='database'):
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

        # Store dataframe on self
        self.moviedata = df
        # Derive dataset for image grid creation
        self.make_dataset(df, size='rating', img_path='poster')

    def make_dataset(self, df, size='rating', img_path='poster', distance:str|None=None):
        """
        Creates dataset to use for image grid creation.
        Receives a pandas dataframe containing necessary information.

        - size      Float-column containing values to determine image size-class
        - img_path  String-column with path to image
        - distance  (Optional) Float column to control image-distribution
        """




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
ig.load_moviedata()
# print(ig.moviedata.groupby('rating')['rating'].count().sort_index())
# ig.populate_grid()
# ig.visualize()


# col = get_hsv_dominant_color(url="https://a.ltrbxd.com/resized/film-poster/5/1/3/4/5/51345-se7en-0-600-0-900-crop.jpg")
# print(col)