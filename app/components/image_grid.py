import streamlit as st
import pandas as pd

def render_hover_image(col, vals, descr_length):
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
            <b>{vals['name']}</b>
            <p style="margin:2px 0;">⭐ {vals['meta_score']} (🍅 {vals['critics_score']} 🍿 {vals['audience_score']})</p>
            <p style="font-size:12px; color:#ccc;">{vals['description'][:descr_length]}...</p>
        </div>
    </div>
    """
    return html_code

def display_centered_images(df_in: pd.DataFrame, max_images: int = 5, descr_length: int=120):
    """
    """
    df = df_in.copy().dropna().head(max_images)
    df_list = df.to_dict(orient='records')
    # 1. Edge Case: Handle 0 rows
    if df.empty:
        st.info("No data available to display images.")
        return

    # 2. Extract up to max_images from the DataFrame column
    image_urls = [c['poster'] for c in df_list] #df['poster'].tolist()
    num_images = len(image_urls)

    if num_images == 0:
        st.warning("No valid image URLs found in the selected data.")
        return

    # 3. Handle Centering via Column Ratios
    # If fewer than max_images images, add empty padding columns on the sides
    if num_images == max_images:
        # 5 equal columns spanning full width
        cols = st.columns(max_images)
        img_cols = cols
    else:
        # Calculate left/right padding weight to keep images centered
        padding_weight = (max_images - num_images) / 2
        # Ratio layout: [padding, 1, 1, ..., padding]
        weights = [padding_weight] + [1] * num_images + [padding_weight]
        
        all_cols = st.columns(weights)
        # The middle columns contain the images
        img_cols = all_cols[1:-1]

    # 4. Render images with uniform width
    for col, vals in zip(img_cols, df_list):
        with col:
            html_code = render_hover_image(
                col,
                vals,
                descr_length)
            st.markdown(html_code, unsafe_allow_html=True)
            # st.image(
            #     url, 
            #     use_container_width=True  # Ensures all images scale uniformly
            # )
