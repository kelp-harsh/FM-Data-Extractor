# response_1.py
from openai import OpenAI
import json
import logging
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_openai():
    """Initialize OpenAI client"""
    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def format_url(url):
    """Format and validate URL to ensure proper scheme"""
    try:
        url = url.strip()
        parsed = urlparse(url)
        
        if not parsed.scheme:
            url = 'https://' + url
        
        return url
        
    except Exception as e:
        logger.error(f"Error formatting URL: {e}")
        return None
    
def process_element_with_gpt(element_data, url):
    """Process a single element with GPT"""
    url = format_url(url)
    client = setup_openai()
    base_url = str("/".join(url.split("/")[:-1]))
    prompt = """
    Instructions:
    1. Do not skip any data. If there are 100 results, return all 100.
    2. You are a JSON-only response bot, specialized in processing employee data.

    Please analyze the provided data and structure it in the following format:
    Main Key will be "employees":
    Below are the sub-keys
        - 'Main_URL': {url}
        - 'Name': The name of the individual.
        - 'Title': Their organizational title.
        - 'LinkedIn Profile Link': A valid LinkedIn URL containing "linkedin.com". If absent, return an empty string.
        - 'Individual profile URLs': A unique URL associated with the individual. If absent or invalid, return an empty string.
        - 'Bio': A brief description of the individual. If absent, return an empty string.
        - 'Sector Expertise': Based on 'Bio', summarize the individual's sector expertise (e.g., "Cloud Computing", "Marketing").
        - 'Additional Information'
        - 'Additional Links'

    If a field is missing or cannot be determined, return it as an empty string.

    Raw data:
    {data}

    """

    # - If the link contains the substring "{url}", ensure it is captured.
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data structuring assistant. Convert the provided raw data into a consistent JSON format."},
                {"role": "user", "content": prompt.format(data=json.dumps(element_data, indent=2), url = url)}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate Individual profile URLs
        if 'employees' in result:
            for employee in result['employees']:
                if 'Individual profile URLs' in employee:
                    employee['Individual profile URLs'] = str(employee['Individual profile URLs'])
                elif employee['Individual profile URLs'] == url or len(str(employee['Individual profile URLs']) < len(str(url))) or employee['Individual profile URLs'] == str(base_url) + "/":
                    employee['Individual profile URLs'] = ''
        return result
        
    except Exception as e:
        logger.error(f"Error in GPT processing: {e}")
        return None

def process_element_with_gpt_2(element_data, url):
    """Process a single element with GPT"""
    print("Gettig Response 2")
    url = format_url(url)
    client = setup_openai()
    base_url = str("/".join(url.split("/")[:-1]))
    prompt = """
    Instructions:
    1. Remember the whole data is with respect to only a single employee.
    2. You are a JSON-only response bot, specialized in processing employee data.

    Please analyze the provided data and structure it in the following format:
    Main Key will be "employees":
    Below are the sub-keys
        - 'Main_URL'
        - 'Name': The name of the individual.
        - 'Title': Their organizational title.
        - 'LinkedIn Profile Link': A valid LinkedIn URL containing "linkedin.com". If absent, return an empty string.
        - 'Individual profile URLs': A unique URL associated with the individual. If absent or invalid, return an empty string.
        - 'Bio': A brief description of the individual. If absent, return an empty string.
        - 'Sector Expertise': Based on 'Bio', summarize the individual's sector expertise (e.g., "Cloud Computing", "Marketing").
        - 'Additional Information': Return empty string if nothing is found
        - 'Additional Links': Return empty string if nothing is found

    If a field is missing or cannot be determined, return it as an empty string.

    Raw data:
    {data}

    """

    # - If the link contains the substring "{url}", ensure it is captured.
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data structuring assistant. Convert the provided raw data into a consistent JSON format."},
                {"role": "user", "content": prompt.format(data=element_data, url = url)}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        '''# Validate Individual profile URLs
        if 'employees' in result:
            for employee in result['employees']:
                if 'Individual profile URLs' in employee:
                    employee['Individual profile URLs'] = str(employee['Individual profile URLs'])
                elif employee['Individual profile URLs'] == url or len(str(employee['Individual profile URLs']) < len(str(url))) or employee['Individual profile URLs'] == str(base_url) + "/":
                    employee['Individual profile URLs'] = '''''
        result['employees'] = [dict(result['employees'])]
        return result
        
    except Exception as e:
        logger.error(f"Error in GPT processing: {e}")
        return None

