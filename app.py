import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# Load data from S3
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data_from_s3(bucket_name, prefix):
    """Load COVID-19 data from S3 bucket using Parquet format."""
    try:
        # Construct S3 path
        s3_path = f"s3://{bucket_name}/{prefix}"
        
        # Read Parquet files directly from S3
        df = pd.read_parquet(s3_path, engine="pyarrow")
        
        # Convert time_value to datetime if it exists (format: '2021-01-07')
        df['time_value'] = pd.to_datetime(df['time_value'], format='%Y-%m-%d', errors='coerce')
        
        return df
    
    except Exception as e:
        st.error("Error loading data from database")
        return None

def empty_warning(df):
    if df is None or df.empty:
        st.error("❌ Unable to load data. Please check your db configuration and credentials.")
        return False
    else:
        return True

def draw_positive_geo(df):
    """Draw a choropleth map of positive test rates by county."""
    # Remove rows with missing positive test rate
    df_copy = df.dropna(subset=['smoothed_wtested_positive_14d']).copy()
    
    # Create choropleth map
    fig = px.choropleth(
        df_copy,
        geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
        locations='geo_value',
        color='smoothed_wtested_positive_14d',
        color_continuous_scale="Reds",
        range_color=(0, 100),
        scope="usa",
        labels={'smoothed_wtested_positive_14d': 'Positive Test Rate (%)'},
        title='COVID-19 Positive Test Rate by County'
    )
    
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    return fig

def draw_positive_state(df):
    """Draw a choropleth map of positive test rates by state."""
    # Remove rows with missing positive test rate
    df_copy = df.dropna(subset=['smoothed_wtested_positive_14d']).copy()

    # Aggregate by state_abbr
    state_df = df_copy.groupby('state_abbr')['smoothed_wtested_positive_14d'].mean().reset_index()

    min_rate = state_df['smoothed_wtested_positive_14d'].min()
    max_rate = state_df['smoothed_wtested_positive_14d'].max()
    
    # Create choropleth map
    fig = px.choropleth(
        state_df,
        locations='state_abbr',
        locationmode='USA-states',
        color='smoothed_wtested_positive_14d',
        color_continuous_scale="Reds",
        range_color=(min_rate, max_rate),
        scope="usa",
        labels={'smoothed_wtested_positive_14d': 'Avg Positive Test Rate (%)'},
        title='Average COVID-19 Positive Test Rate by State'
    )
    
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    return fig

def draw_vaccination_state(df):
    """Draw a choropleth map of vaccination rates by state."""
    # Remove rows with missing vaccination rate
    df_copy = df.dropna(subset=['smoothed_wcovid_vaccinated']).copy()
    
    # Aggregate by state_abbr
    state_df = df_copy.groupby('state_abbr')['smoothed_wcovid_vaccinated'].mean().reset_index()

    min_rate = state_df['smoothed_wcovid_vaccinated'].min()
    max_rate = state_df['smoothed_wcovid_vaccinated'].max()

    # Create choropleth map
    fig = px.choropleth(
        state_df,
        locations='state_abbr',
        locationmode='USA-states',
        color='smoothed_wcovid_vaccinated',
        color_continuous_scale="Greens",
        range_color=(min_rate, max_rate),
        scope="usa",
        labels={'smoothed_wcovid_vaccinated': 'Avg Vaccination Rate (%)'},
        title='Average COVID-19 Vaccination Rate by State'
    )
    
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    return fig

# Main app
def main():
    # Header
    st.markdown('<h1 class="main-header">COVID-19 Data Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # S3 configuration from secrets.toml
    try:
        bucket_name = st.secrets["S3_BUCKET"]
        prefix = st.secrets["S3_PREFIX"]
    except KeyError:
        st.error("❌ S3 configuration not found in secrets.toml")
        st.info("""
        **Please add the following to `.streamlit/secrets.toml`:**
        ```
        S3_BUCKET = "your-bucket-name"
        S3_PREFIX = "your-prefix-path/"
        ```
        """)
        return
    
    # Load data
    with st.spinner("Loading data from S3..."):
        df = load_data_from_s3(bucket_name, prefix)
    
    if not empty_warning(df):
        return
    
    # print data intro
    st.write("### Data Intro")
    db_intro = "The dataset used in this study is derived from the COVID-19 Trends and Impact Survey (CTIS), conducted by the Delphi Group at Carnegie Mellon University. This dataset ag gregates responses from a representative sample of Facebook users (aged 18+) at the U.S. county level. Responses were gathered during one-month time frame at the peak of the COVID pandemic (from January 07, 2021 to February 12, 2021), offering rich information to analyze temporal dynamics in health behaviors and perceptions. The dataset contains 25627 instances where each row represents one U.S. county in a given day."
    st.markdown(db_intro)

    # Draw map: "geo_value" is FIPS code for counties; "smoothed_wtested_positive_14d" is positive test rate.
    # Remove rows with missing smoothed_wtested_positive_14d. Use a copy for it.
    # Draw heatmap of positive test rate
    # "smoothed_wtested_positive_14d" range from 0 to 100
    # fig_positive_geo = draw_positive_geo(df)
    # st.plotly_chart(fig_positive_geo, use_container_width=True)
    
    # Draw map："geo_value" is FIPS code for counties; "smoothed_wcovid_vaccinated" is vaccination rate.
    # fig_vaccination_geo = draw_vaccination_geo(df)
    # st.plotly_chart(fig_vaccination_geo, use_container_width=True)
    
    # Draw map: state_name to positive rate
    # state name format: ALABAMA, first make sure it matches plotly state names
    fig_positive_state = draw_positive_state(df)
    st.plotly_chart(fig_positive_state, use_container_width=True)

    # Draw map: state_name to vaccination rate
    fig_vaccination_state = draw_vaccination_state(df)
    st.plotly_chart(fig_vaccination_state, use_container_width=True)
    
if __name__ == "__main__":
    main()
