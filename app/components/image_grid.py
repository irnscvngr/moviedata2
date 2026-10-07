import streamlit as st
import pandas as pd

def hover_image_movie_selector(vals):
    descr_length=120
    html_code = f"""
    <style>
        .img-container {{
            position: relative;
            width: 100%;
            margin-bottom: 1.5rem; /* Adds padding/spacing beneath the element */
        }}
        .img-container img {{
            width: 100%;
            border-radius: 10px;
            display: block;
        }}
        .img-container .overlay {{
            position: absolute;
            top: 0; bottom: 0; left: 0; right: 0;
            height: 100%; width: 100%;
            opacity: 0;
            transition: .3s ease;
            background-color: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 12px;
            border-radius: 8px;
            box-sizing: border-box;
            overflow: hidden;
        }}
        .img-container:hover .overlay {{
            opacity: 1;
        }}
    </style>
    <div class="img-container">
        <img src="{vals['poster']}">
        <div class="overlay">
            <p style="font-size:16px; font-weight:bold; margin:0px">{vals['name']}</p>
            <p style="font-size:16px; margin:0px">{vals['year']}</p>
            <p style="font-size:14px; margin:2px 0;">⭐ {vals['meta_score']} (🍅 {vals['critics_score']} 🍿 {vals['audience_score']})</p>
            <p style="font-size:14px; color:#ccc;">{vals['description'][:descr_length]}...</p>
        </div>
    </div>
    """
    return html_code


def hover_image_cinema_overview(vals):
    descr_length=120
    html_code = f"""
    <style>
        .img-container {{
            position: relative;
            width: 100%;
            margin-bottom: 1.5rem; /* Adds padding/spacing beneath the element */
        }}
        .img-container img {{
            width: 100%;
            border-radius: 10px;
            display: block;
        }}
        .img-container .overlay {{
            position: absolute;
            top: 0; bottom: 0; left: 0; right: 0;
            height: 100%; width: 100%;
            opacity: 0;
            transition: .3s ease;
            background-color: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 12px;
            border-radius: 8px;
            box-sizing: border-box;
            overflow: hidden;
        }}
        .img-container:hover .overlay {{
            opacity: 1;
        }}
    </style>
    <div class="img-container">
        <img src="{vals['poster_url']}">
        <div class="overlay">
            <p style="font-size:14px; margin-bottom: 0px"> {vals['runtime']:.0f} min / FSK {vals['fsk']:.0f}</p>
            <p style="font-size:16px; font-weight:bold; margin-bottom: 0px"> {vals['title']}</p>
            <p style="font-size:14px; margin-bottom: 6px"> {vals['year']:.0f}</p>
            <p style="font-size:12px; margin:2px 0;">⭐ {vals['meta_score']} (🍅 {vals['critics_score']:.0f} 🍿 {vals['audience_score']:.0f})</p>
        </div>
    </div>
    """
    return html_code


def display_centered_images(
        df_in: pd.DataFrame, 
        max_images_x: int = 5,
        max_images_y: int = 2,
        col_poster_url = 'poster',
        hover_func=None
        ):
    """
    Function to display centered images based on dataframe.
    Provide handle to custom hover function for markdown hover.
    """

    max_images_total = max_images_x*max_images_y

    # Prepare dataframe
    df = df_in.copy().head(max_images_total)
    df_list = df.to_dict(orient='records')
    
    # Passed dataframe is empty
    if df.empty:
        st.info("No data available to display images.")
        return

    # Get image URLs from the DataFrame column
    # (List shrinks if entries are NULL)
    image_urls = [c[col_poster_url] for c in df_list]
    num_images_total = len(image_urls)

    # All URL entries were NULL
    if num_images_total == 0:
        st.warning("No valid image URLs found in the selected data.")
        return

    # ...........................................................................
    # ARRANGE IMAGES

    for y in range(max_images_y):
        # Make indeces to go through list
        i0 = y*max_images_x
        i1 = i0 + max_images_x
        num_images_tmp = len(image_urls[i0:i1])

        # If fewer than max_images images, add empty padding columns on the sides
        if num_images_tmp == max_images_x:
            # Number of columns is number of images
            cols = st.columns(max_images_x)
            img_cols = cols
        else:
            # Calculate left/right padding weight to keep images centered
            padding_weight = (max_images_x - num_images_tmp) / 2
            # Ratio layout: [padding, 1, 1, ..., padding]
            weights = [padding_weight] + [1]*num_images_tmp + [padding_weight]
            # Use weights to set column widths
            all_cols = st.columns(weights)
            # The middle columns contain the images
            img_cols = all_cols[1:-1]

        # ...........................................................................
        # RENDER IMAGES

        # Render images with uniform width
        for col, vals in zip(img_cols, df_list[i0:i1]):
            with col:
                if hover_func is None:
                    st.image(
                        vals[col_poster_url], 
                        use_container_width=True  # Ensures all images scale uniformly
                    )
                else:
                    html_code = hover_func(vals)
                    st.markdown(html_code, unsafe_allow_html=True)
