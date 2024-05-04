import streamlit as st
import pickle
import requests
import asyncio
import httpx
import base64
import os
from dotenv import load_dotenv,dotenv_values

load_dotenv()
 
# Function to set a background image
def set_background_image(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    encoded = base64.b64encode(image_bytes).decode()
    background_image = f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        .zoomed {{
            transform: scale(1.5);  # Increase default scale
            transition: all 0.3s ease-in-out;  # Smooth transitions
        }}

        .stButton > button {{
            background-color: #1E90FF;
            color: white;
            border-radius: 10px;
            padding: 12px 24px;
        }}
        </style>
    """
    st.markdown(background_image, unsafe_allow_html=True)

# Set background image
set_background_image("background.jpg")

# Load movie data and similarity vector
movies_list = pickle.load(open("movies.pkl", "rb"))
similarity_vector = pickle.load(open("similarity_vector", "rb"))

# Styling for the title and other components
custom_css = """
<style>
    .stMarkdown h1 {
        color: white;
        font-weight: bold;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

st.title("Movie Recommender System")

# Function to recommend movies
def recommend(movie):
    movie_index = movies_list[movies_list['title'] == movie].index[0]
    distances = similarity_vector[movie_index]
    sorted_indices = sorted(
        enumerate(distances),
        key=lambda x: x[1],
        reverse=True
    )[1:7]

    return [movies_list.iloc[i[0]]['title'] for i in sorted_indices]

# Asynchronous function to fetch movie poster and trailer
async def fetch_poster_and_trailer_async(movie_id):
    async with httpx.AsyncClient() as client:
        url_trailer = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?language=en-US"
        url_poster = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"

        headers = {
            "accept": "application/json",
            # "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiZjg1OTEzYzE5YWQ1Mzg2NWFlNmY1ODZkMjIyOTJlYiIsInN1YiI6IjYyZjhkNGFmMWNhYzhjMDA3YTMwNGU1NSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.Nmca7Wa2ChDF_IsKw6X1bsoqQ9IrXlsdxPYa3LoFhoE",
            "Authorization":os.getenv("API_TOKEN")
        }

        trailer_response = await client.get(url_trailer, headers=headers)
        poster_response = await client.get(url_poster, headers=headers)

        data_trailer = trailer_response.json()
        data_poster = poster_response.json()
        # print("            ")
        # print(data_trailer)
        trailer_url = None
        for video in data_trailer["results"]:
            if video["type"] == "Trailer" and video["site"] == "YouTube":
                trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                break

        poster_url = f"https://image.tmdb.org/t/p/original{data_poster['poster_path']}"

        return poster_url, trailer_url

# Select a movie for recommendation
selected_movie_option = st.selectbox(
    "",
    movies_list['title'].values,
    placeholder="Choose a movie..."
)

# Initialize session state for recommendations
if 'show_recommendations' not in st.session_state:
    st.session_state.show_recommendations = False

# Button to fetch recommendations
if st.button("Recommend"):
    st.session_state.show_recommendations = True
    
    # Reset all toggle states to default
    for i in range(6):
        st.session_state[f'is_trailer_{i}'] = False

# Only fetch and display recommendations if "Recommend" is clicked
if st.session_state.show_recommendations:
    recommended_movies = recommend(selected_movie_option)

    # Create two rows with three columns each, with consistent spacing
    row_1 = st.columns(3)  # First row
    row_2 = st.columns(3)  # Second row

    async def load_posters():
        tasks = []
        for i in range(min(3, len(recommended_movies))):
            movie_title = recommended_movies[i]
            movie_id = movies_list[movies_list['title'] == movie_title]['movie_id'].iloc[0]
            tasks.append(fetch_poster_and_trailer_async(movie_id))

        # Get results from all asynchronous tasks
        poster_trailer_results = await asyncio.gather(*tasks)

        # Place posters and trailers in the first row
        for i, result in enumerate(poster_trailer_results):
            poster_url, trailer_url = result
            with row_1[i]:
                with st.popover("Watch Trailer"):
                    st.video(trailer_url)
                st.image(poster_url, width=320)  # Larger poster width
                st.markdown(f"<p style='color:white; font-size:24px;'>Movie: {recommended_movies[i]}</p>", unsafe_allow_html=True)  # Larger text

        tasks = []
        for i in range(3, min(6, len(recommended_movies))):
            movie_title = recommended_movies[i]
            movie_id = movies_list[movies_list['title'] == movie_title]['movie_id'].iloc[0]
            tasks.append(fetch_poster_and_trailer_async(movie_id))

        # Get results from asynchronous tasks for the second row
        poster_trailer_results = await asyncio.gather(*tasks)

        # Place posters and trailers in the second row
        for i, result in enumerate(poster_trailer_results):
            poster_url, trailer_url = result
            with row_2[i - 3]:
                with st.popover("Watch Trailer"):
                    st.video(trailer_url)

                st.image(poster_url, width=320)
                st.markdown(f"<p style='color:white; font-size:24px;'>Movie: {recommended_movies[i]}</p>", unsafe_allow_html=True)  # Larger text

    asyncio.run(load_posters())  # Run asynchronous tasks
