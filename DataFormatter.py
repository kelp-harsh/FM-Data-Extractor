import streamlit as st
import pandas as pd
from io import BytesIO
import pyperclip
import json
import re
from response_1 import process_element_with_gpt
from streamlit_option_menu import option_menu

import re

class DataFormatter:
    """Class to handle data formatting operations"""
    @staticmethod
    def format_extracted_text(text):
        """Format extracted text from containers into structured data."""
        if not text.strip():
            return {}
            
        container_pattern = r"=== CONTAINER #(\d+) - Instance #(\d+) ==="
        sections = re.split(container_pattern, text)
        if not sections or (len(sections) < 3):
            return {}
            
        sections = sections[1:] if sections[0].strip() == "" else sections
        formatted_data = {}
        
        for i in range(0, len(sections)-2, 3):
            try:
                container_num, instance_num, content = sections[i:i+3]
                if not content.strip():
                    continue
                    
                instance_data = DataFormatter._process_container_content(
                    content.strip(), 
                    container_num, 
                    formatted_data
                )
                
                if container_num not in formatted_data:
                    formatted_data[container_num] = {}
                formatted_data[container_num][instance_num] = instance_data
                
            except Exception as e:
                st.error(f"Error processing container {i//3 + 1}: {str(e)}")
                continue

        # print("Formatted Data : ", formatted_data.keys())
        # print("Formatted_Data, ", formatted_data['2']['1'])

        return formatted_data
    
    @staticmethod
    def _process_container_content(content, container_num, formatted_data):
        """Process individual container content"""
        lines = content.split('\n')
        content_lines = []
        links = []

        for line_1 in lines:
            line_1 = line_1.strip()
            line_1 = line_1.split("  ")
            for line in line_1:
                line = line.strip()
                if line:
                    
                    if line[:3] == "## ":
                        line = line[3:]
                    if not line:
                        continue
                    
                    words = line.split()  
                    flag = False
                    for word in words:
                        link_data = DataFormatter._extract_link_data(word)
                        if link_data:
                            flag = True
                        if link_data and link_data not in links:
                            links.append(link_data)
                            
                    if not flag:
                        if line != "Links:":
                            content_lines.append(line)
                    
            
        return DataFormatter._create_instance_data(
            content_lines, 
            links, 
            container_num, 
            formatted_data
        )
    
    @staticmethod
    def _extract_link_data(line):
        """Extract link data from a line"""
        link_match = re.search(r'(?:Link \d+: )?(https?://[^\s]+)', line)
        if link_match:
            return {
                'href': link_match.group(1)
            }
        return None
    
    @staticmethod
    def _create_instance_data(content_lines, links, container_num, formatted_data):
        """Create structured instance data"""
        instance_data = {
            'text': '\n'.join(content_lines),
            'links': links
        }
        
        return instance_data