import pandas as pd
from io import BytesIO
import pyperclip
import json
import re
import logging
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin
import os
from openpyxl import load_workbook
from streamlit_option_menu import option_menu
from requests.exceptions import RequestException
from response_1 import process_element_with_gpt, process_element_with_gpt_2
from DataFormatter import DataFormatter
from UI import UI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_request(url: str) -> Optional[str]:
    """Make HTTP request with proper headers and error handling"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {str(e)}")
        return None

def is_valid_link(link: str, base_url: str) -> bool:
    """Validate if a link is valid and relevant"""
    if not link:
        return False
        
    absolute_link = urljoin(base_url, link)
    return ('linkedin.com' in absolute_link or absolute_link.startswith(base_url))

def extract_data_from_url(url: str, employee_name: str) -> List[Dict]:
    html_content = make_request(url)
    if not html_content:
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Instead of searching for 'main' class, get all elements
        elements = soup.find_all()
        
        seen_content = set()
        results = []
        
        for element in elements:
            if not isinstance(element, Tag):
                continue
            
            # Skip script, style, and other non-content tags
            if element.name in ['script', 'style', 'meta', 'link', 'noscript']:
                continue
                
            full_text = element.get_text(strip=True, separator=' ')
            
            # Skip empty elements
            if not full_text:
                continue
            
            # Find the starting position of employee name in the text
            name_position = full_text.find(employee_name)
            
            # Skip if employee name not found in this element
            if name_position == -1:
                continue
                
            # Extract text starting from employee name
            filtered_text = full_text[name_position:]
            
            # Collect links that appear after the employee name
            links = []
            cumulative_text = ''
            
            for a_tag in element.find_all('a', href=True):
                # Get the text position of this link in the full content
                link_text = a_tag.get_text(strip=True)
                link_position = full_text.find(link_text)
                
                # Only include links that appear after the employee name
                if link_position >= name_position:
                    href = a_tag.get('href')
                    if is_valid_link(href, url):
                        full_url = urljoin(url, href)
                        links.append(full_url)
            
            content_hash = hash(f"{filtered_text}{''.join(sorted(links))}")
            
            if content_hash not in seen_content and (filtered_text or links):
                seen_content.add(content_hash)
                results.append({
                    'text': filtered_text,
                    'links': links
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing URL '{url}': {str(e)}")
        return []
    
def merge_employee_data(original_data: dict, new_data: dict) -> dict:
    """Merge original and new employee data, preserving specific fields"""
    merged_data = original_data.copy()
    preserve_cols = {'Name', 'Individual profile URLs', 'Main_URL'}
    
    for col, value in new_data.items():
        if col not in preserve_cols:
            merged_data[col] = value
    
    return merged_data

def validate_employee_data(data: dict) -> bool:
    """Validate the structure of employee data"""
    if not isinstance(data, dict):
        logger.error(f"Expected dict, got {type(data)}")
        return False
    
    if 'employees' not in data:
        logger.error("Missing 'employees' key in data")
        return False
        
    if not isinstance(data['employees'], list):
        logger.error(f"Expected list for 'employees', got {type(data['employees'])}")
        return False
        
    return True

def get_base_url(url: str) -> str:
    # Split URL by dots and get components
    url_parts = url.split('/')
    if len(url_parts) >= 3:  # Make sure we have protocol and domain
        return '/'.join(url_parts[:3])  # This gets us 'https://www.domain.com'
    return url

def normalize_url(url: str, base_url: str) -> str:
    if url.startswith('/'):
        return f"{base_url.rstrip('/')}{url}"
    return url

def format_additional_links(links) -> str:
    if links is None:
        return ""
    if isinstance(links, list):
        return '; '.join(str(link) for link in links if link)
    if isinstance(links, str):
        return links
    return str(links)

def process_employee_data(employee_data: dict) -> dict:
    processed_data = employee_data.copy()
    
    # Handle Additional Links
    if 'Additional Links' in processed_data:
        processed_data['Additional Links'] = format_additional_links(processed_data['Additional Links'])
    
    # Ensure all other fields are strings
    for key, value in processed_data.items():
        if value is None:
            processed_data[key] = ""
        elif not isinstance(value, str):
            processed_data[key] = str(value)
            
    return processed_data

def extract_clean_text(html_content):
    """Extract and clean text from HTML content"""
    if not html_content or pd.isna(html_content):
        return ""
    
    if isinstance(html_content, (float, int)):
        return str(html_content)
    
    soup = BeautifulSoup(str(html_content), 'html.parser')
    
    # Remove script and style elements
    for element in soup(['script', 'style']):
        element.decompose()
    
    # Get text and clean it
    text = ' '.join(soup.stripped_strings)
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_links(html_content, base_url=""):
    """Extract all links from HTML content"""
    if not html_content or pd.isna(html_content):
        return []
    
    soup = BeautifulSoup(str(html_content), 'html.parser')
    links = []
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Make relative URLs absolute
        if base_url and not href.startswith(('http://', 'https://')):
            href = urljoin(base_url, href)
        links.append(href)
    
    return links


