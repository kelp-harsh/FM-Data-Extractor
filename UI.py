import streamlit as st
import pandas as pd
from io import BytesIO
import pyperclip
import json
import re
from response_1 import process_element_with_gpt
from streamlit_option_menu import option_menu

class UI:
    """Class to handle UI components and styling"""
    @staticmethod
    def apply_custom_css():
        st.markdown("""
            <style>
            .block-container {
                padding-top: 3rem !important;
                padding-bottom: 0rem;
            }
            
            [data-testid="stSidebar"] {
                padding-top: 0rem;
                background-color: white;
            }
            
            [data-testid="stSidebar"] > div:first-child {
                padding-top: 0rem;
            }
            
            .main-menu {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem;
                border-bottom: 1px solid #e6e6e6;
            }
            
            .stTextInput, .stTextArea {
                margin-bottom: 0.3rem !important;
            }
            
            .stMarkdown {
                margin-bottom: 0.1rem !important;
            }
            
            .stMarkdown h5 {
                margin-bottom: 0.1rem !important;
                font-size: 0.9rem;
            }
            
            div[data-testid="stVerticalBlock"] > div {
                padding: 0.1rem 0;
            }
            
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea {
                font-size: 0.8rem;
            }
            
            .stButton > button {
                font-size: 0.8rem;
                padding: 0.2rem 0.8rem;
            }
            .stCodeBlock {
                font-size: 8px; /* Adjust the font size as needed */
            }
            
            /* Remove label space */
            .stTextInput > label,
            .stTextArea > label {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def get_preview_text(formatted_data):
        """Generate preview text from formatted data"""
        if not formatted_data or '1' not in formatted_data:
            return "No data available for preview"
        
        instance = formatted_data['1']
        return f"""text: {instance['text']},
Links: {', '.join(link['href'] for link in instance['links'])}"""

class DataProcessor:
    """Class to handle data processing and API interactions"""
    @staticmethod
    def process_data(formatted_data, url):
        """Process formatted data and generate response"""
        input_data = {
            "containers": [
                instance 
                for container in formatted_data.values() 
                for instance in container.values()
            ]
        }
        
        return process_element_with_gpt(input_data, url)
    
    @staticmethod
    def create_dataframe(response):
        """Create DataFrame from API response"""
        if not response or 'employees' not in response:
            raise ValueError("Invalid response format")
        return pd.DataFrame(response['employees'])