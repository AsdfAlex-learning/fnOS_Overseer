# core/behavior/analyzer.py

import logging
from datetime import datetime

# Configure a specific logger for user behavior
logger = logging.getLogger("user_behavior")
logger.setLevel(logging.INFO)

# File handler for raw behavior logs
file_handler = logging.FileHandler("logs/user_behavior.log")
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_raw_behavior(data):
    """
    Log raw user behavior data to a file for later analysis.
    """
    try:
        logger.info(str(data))
    except Exception as e:
        print(f"Error logging behavior data: {e}")

def process_user_behavior(data):
    """
    Process user behavior data received from webhook.
    
    This function is intended to be customized by the user to define
    what constitutes "abnormal behavior".
    
    Args:
        data (dict): The raw JSON data received from the webhook.
    """
    # Step 1: Log the raw data
    log_raw_behavior(data)
    
    # Step 2: Custom Logic (To be implemented by user)
    # TODO: User to implement custom logic here
    # Example:
    # user_id = data.get('user_id')
    # action = data.get('action')
    # if action == 'delete_all_files':
    #     trigger_alert(user_id, action)
    
    print(f"Received user behavior data: {data}")
    # Return value is not currently used by the webhook API, but could be.
    return True
