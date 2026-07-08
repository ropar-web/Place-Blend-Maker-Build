import streamlit as st

st.set_page_config(
    page_title="Place Blend Maker — Local Style Transfer",
    page_icon="🎨",
    layout="wide",
)

from place_blend_core import render_app

render_app()
