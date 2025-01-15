import streamlit as st
import pandas as pd
import json
import logging
import os
from streamlit_option_menu import option_menu
from response_1 import process_element_with_gpt, process_element_with_gpt_2
from DataFormatter import DataFormatter
from UI import UI
from helper_functions import make_request, is_valid_link, extract_data_from_url, merge_employee_data, format_additional_links, validate_employee_data, get_base_url, normalize_url, process_employee_data
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import numpy as np
from dotenv import load_dotenv
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
# Load environment variables from .env file
load_dotenv()

gcp_service_account = os.getenv("GCP_SERVICE_ACCOUNT")
gcp_credentials = json.loads(gcp_service_account)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
APP_TITLE = "FM Data Extractor"
DEFAULT_EXCEL_FILENAME = "employee_data_results.xlsx"

class SessionManager:
    """Improved session state manager with proper initialization and type hints"""
    
    @staticmethod
    def initialize_session_state():
        """Initialize all session state variables with default values"""
        default_states = {
            'formatted_data': {},
            'raw_text': "",
            'url': "",
            'text_area': "",
            'response_data': None,
            'processing': False
        }
        
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    @staticmethod
    def reset_session():
        """Reset all session state variables to their default values"""
        st.session_state.formatted_data = {}
        st.session_state.raw_text = ""
        st.session_state.url = ""
        st.session_state.text_area = ""
        st.session_state.response_data = None
        st.session_state.processing = False
    
    @staticmethod
    def update_formatted_data(data: dict):
        """Safely update formatted data in session state"""
        st.session_state.formatted_data = data
    
    @staticmethod
    def update_response_data(data: dict):
        """Safely update response data in session state"""
        st.session_state.response_data = data
    
    @staticmethod
    def is_processing() -> bool:
        """Check if data is currently being processed"""
        return st.session_state.processing
    
    @staticmethod
    def set_processing(state: bool):
        """Set the processing state"""
        st.session_state.processing = state

def handle_data_processing(url: str, formatted_data: dict):
    """Handle data processing with proper error handling and state management"""
    try:
        SessionManager.set_processing(True)
        response = process_element_with_gpt(formatted_data, url)
        SessionManager.update_response_data(response)
        return True
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return False
    finally:
        SessionManager.set_processing(False)


def display_preview_results(preview_data: dict):
    """Display preview of initial results"""
    if preview_data and 'employees' in preview_data:
        st.subheader("Initial Results Preview")
        
        # Format the data before creating DataFrame
        formatted_employees = []
        for employee in preview_data['employees']:
            formatted_employee = employee.copy()
            if 'Additional Links' in formatted_employee:
                formatted_employee['Additional Links'] = format_additional_links(formatted_employee['Additional Links'])
            formatted_employees.append(formatted_employee)
            
        preview_df = pd.DataFrame(formatted_employees)
        st.dataframe(preview_df, use_container_width=True, height=200)

def display_processing_status(current: int, total: int, message: str = "Processing individual profiles"):
    """Display processing status with progress bar"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    progress = float(current) / total
    progress_bar.progress(progress)
    status_text.text(f"{message}: {current}/{total}")
    
    return progress_bar, status_text


def handle_data_processing(url: str, formatted_data: dict):
    """Handle data processing with proper error handling and state management"""
    try:
        SessionManager.set_processing(True)
        base_url = get_base_url(url)
        
        # Normalize URLs in the formatted data
        if isinstance(formatted_data, dict):
            for key in formatted_data:
                if isinstance(formatted_data[key], dict):
                    for subkey, value in formatted_data[key].items():
                        if 'url' in value.lower() and isinstance(value, str):
                            formatted_data[key][subkey] = normalize_url(value, base_url)
        
        response = process_element_with_gpt(formatted_data, url)
        SessionManager.update_response_data(response)
        return True
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return False
    finally:
        SessionManager.set_processing(False)


def process_individual_urls(preview_results: dict) -> dict:
    if not validate_employee_data(preview_results):
        st.error("Invalid data format received from initial processing")
        return {"employees": []}
        
    updated_results = {"employees": []}
    total_urls = len(preview_results['employees'])
    
    progress_bar = st.progress(0)
    status_container = st.empty()
    
    try:
        for i, employee in enumerate(preview_results['employees']):
            if not isinstance(employee, dict):
                logger.error(f"Invalid employee data format: {type(employee)}")
                continue
            
            # Process employee data for consistent types
            employee = process_employee_data(employee)
                
            progress = (i + 1) / total_urls
            progress_bar.progress(progress)
            status_container.text(f"Processing profile {i+1}/{total_urls}")
            
            try:
                individual_url = employee.get('Individual profile URLs', '')
                if not individual_url:
                    logger.warning(f"No URL found for employee {i+1}")
                    updated_results['employees'].append(employee)
                    continue
                
                main_url = employee.get('Main_URL', '')
                base_url = get_base_url(main_url) if main_url else get_base_url(individual_url)
                individual_url = normalize_url(individual_url, base_url)
                employee['Individual profile URLs'] = individual_url
                employee_name = employee['Name']
                scraped_content = extract_data_from_url(individual_url, employee_name)
                if not scraped_content:
                    logger.warning(f"No content extracted from URL: {individual_url}")
                    updated_results['employees'].append(employee)
                    continue
                
                individual_result = process_element_with_gpt_2(scraped_content, individual_url)
                
                if validate_employee_data(individual_result) and individual_result['employees']:
                    processed_employee = process_employee_data(individual_result['employees'][0])
                    merged_data = merge_employee_data(employee, processed_employee)
                    updated_results['employees'].append(merged_data)
                else:
                    logger.warning(f"Invalid GPT response for URL: {individual_url}")
                    updated_results['employees'].append(employee)
                    
            except Exception as e:
                logger.error(f"Error processing employee {i+1}: {str(e)}")
                updated_results['employees'].append(employee)
                
    except Exception as e:
        logger.error(f"Error in main processing loop: {str(e)}")
    finally:
        progress_bar.empty()
        status_container.empty()
    
    return updated_results


def get_google_sheets_service():
    """Initialize Google Sheets service with proper credentials"""
    try:
        # Load credentials from environment variable
        if gcp_service_account:
            # Create temporary credentials file
            with open('temp_credentials.json', 'w') as f:
                json.dump(gcp_credentials, f)
            
            credentials = service_account.Credentials.from_service_account_file(
                'temp_credentials.json',
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Clean up temporary file
            os.remove('temp_credentials.json')
        else:
            raise ValueError("GCP service account credentials not found in environment variables")
        
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets service: {str(e)}")
        return None

def find_first_empty_row(sheet, spreadsheet_id):
    """Find the first empty row in column A"""
    try:
        # Get all values in column A
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A:A'
        ).execute()
        
        values = result.get('values', [])
        
        # If sheet is empty, return 1 (first row)
        if not values:
            return 1
        
        # Return the length + 1 for next empty row
        return len(values) + 1
        
    except Exception as e:
        st.error(f"Error finding first empty row: {str(e)}")
        return 1


def display_results(df: pd.DataFrame, spreadsheet_id='13Z3SomiihUpaikt4HFbDnLsoEel-IQmhjxK22EQqJ4k'):
    """Display and append results to Google Sheet with improved error handling"""
    if df.empty:
        st.warning("No data available to display")
        return
    
    # Clean and process the DataFrame
    df = df.copy()
    df = df.replace({np.nan: '', None: ''})
    df = df.astype(str)
    
    # Display current data
    st.dataframe(df, use_container_width=True, height=300)
    
    try:
        service = get_google_sheets_service()
        if not service:
            return
        
        sheet = service.spreadsheets()
        
        try:
            # Test permissions by trying to read the sheet first
            sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A1:A1'
            ).execute()
        except Exception as e:
            st.error("""
                Permission error: Please ensure that:
                1. The service account has Editor access to the spreadsheet
                2. The spreadsheet ID is correct
                3. The service account credentials are properly configured
            """)
            raise e
        
        # Find the first empty row
        first_empty_row = find_first_empty_row(sheet, spreadsheet_id)
        
        # If it's the first row, include headers
        values = [df.columns.tolist()] if first_empty_row == 1 else []
        values.extend(df.values.tolist())
        
        # Proceed with writing data
        if values:
            # Update in batches to handle large datasets
            batch_size = 1000
            for i in range(0, len(values), batch_size):
                batch = values[i:i + batch_size]
                
                # Calculate the starting row for this batch
                start_row = first_empty_row + i
                
                body = {
                    'values': batch
                }
                
                range_name = f'Sheet1!A{start_row}'
                
                sheet.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            
            st.success(f"Successfully appended {len(df)} rows to Google Sheet starting from row {first_empty_row}")
        
    except Exception as e:
        st.error(f"Error accessing Google Sheets: {str(e)}")


def main():
    """Main application function"""
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    SessionManager.initialize_session_state()
    UI.apply_custom_css()
    
    with st.sidebar:
        selected = option_menu(
            menu_title="Main Menu",
            options=[APP_TITLE],
            icons=["file-earmark"],
            menu_icon="cast",
            default_index=0,
        )
    
    if selected == APP_TITLE:
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        with col1:
            st.button("Reset", key="reset_button", on_click=SessionManager.reset_session)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("##### URL")
            url = st.text_input("Enter URL", key="url", placeholder="e.g., https://www.astorg.com/team")
        
        with col2:
            st.markdown("##### Input Text")
            text_input = st.text_area("Enter Text", height=50, key="text_area")
        
        if text_input:
            try:
                formatted_data = DataFormatter.format_extracted_text(text_input)
                base_url = get_base_url(url) if url else ""
                
                
                SessionManager.update_formatted_data(formatted_data['1'])
                st.markdown("##### Preview")
                if '1' in formatted_data:
                    with st.expander("Container 1", expanded=True):
                        st.code(UI.get_preview_text(formatted_data['1']), language="text")
                if '2' in formatted_data:
                    with st.expander("Container 2", expanded=False):
                        st.code(UI.get_preview_text(formatted_data['2']), language="text")
                if '3' in formatted_data:
                    with st.expander("Container 3", expanded=False):
                        st.code(UI.get_preview_text(formatted_data['3']), language="text")
                if '4' in formatted_data:
                    with st.expander("Container 4", expanded=False):
                        st.code(UI.get_preview_text(formatted_data['4']), language="text")
                if '5' in formatted_data:
                    with st.expander("Container 5", expanded=False):
                        st.code(UI.get_preview_text(formatted_data['5']), language="text")

                selected_container = st.selectbox(
                            "Choose a container to Generate Response:",
                            options=["Container 1", "Container 2", "Container 3", "Container 4", "Container 5"]
                        )
                formatted_data = formatted_data[selected_container[-1:]]
                print("Formatted Data", formatted_data)
                if url and st.button("Generate Response", type="primary", disabled=SessionManager.is_processing()):
                    try:
                        with st.spinner("Processing initial data..."):
                            initial_results = {'employees': []}
                            for data in formatted_data.values():
                                # Process each employee data for consistent types
                                employee_results = process_element_with_gpt(data, url)['employees']
                                initial_results['employees'].extend([
                                    process_employee_data(emp) for emp in employee_results
                                ])
                            
                            if validate_employee_data(initial_results):
                                st.subheader("Initial Results")
                                # Create DataFrame with processed data
                                initial_df = pd.DataFrame([
                                    process_employee_data(emp) for emp in initial_results['employees']
                                ])
                                st.dataframe(initial_df, use_container_width=True, height=200)
                                
                                with st.spinner("Processing individual profiles..."):
                                    updated_results = process_individual_urls(initial_results)
                                    
                                    if validate_employee_data(updated_results):
                                        st.subheader("Final Results")
                                        final_df = pd.DataFrame([
                                            process_employee_data(emp) for emp in updated_results['employees']
                                        ])
                                        display_results(final_df)
                                        SessionManager.update_response_data(updated_results)
                                    else:
                                        st.error("Error processing individual profiles")
                            else:
                                st.error("Error in initial data processing")
                                
                    except Exception as e:
                        st.error(f"Error during processing: {str(e)}")
                        logger.error(f"Processing error: {str(e)}")
                
            except Exception as e:
                st.error(f"Error formatting data: {str(e)}")
                logger.error(f"Formatting error: {str(e)}")
        else:
            st.info("Enter text to see preview")

if __name__ == "__main__":
    main()