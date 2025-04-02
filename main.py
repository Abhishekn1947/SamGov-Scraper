import os
import time
import pandas as pd
from datetime import datetime
import logging
import boto3
import psycopg2
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from psycopg2 import sql

# Load environment variables
load_dotenv()

# Paths and configuration from .env
GECKO_DRIVER_PATH = os.getenv("GECKO_DRIVER_PATH")
TARGET_URL = os.getenv("TARGET_URL")
NAICS_CODES = os.getenv("NAICS_CODES", "").split(",")
FINAL_OUTPUT_DIRECTORY = os.getenv("FINAL_OUTPUT_DIRECTORY")
LOGS_DIRECTORY = os.getenv("LOGS")

# AWS SES configuration
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "Abhishek.nandakumar@aditillc.com")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")

# Basic validation of environment variables
if not all([
    GECKO_DRIVER_PATH, TARGET_URL, NAICS_CODES, FINAL_OUTPUT_DIRECTORY,
    LOGS_DIRECTORY, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    EMAIL_SENDER, EMAIL_RECIPIENTS
]):
    raise ValueError("Missing environment variables. Check your .env file.")

# Ensure logs directory exists
os.makedirs(LOGS_DIRECTORY, exist_ok=True)
os.makedirs(FINAL_OUTPUT_DIRECTORY, exist_ok=True)

# Set up log file with timestamp and numbering
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_number = len(os.listdir(LOGS_DIRECTORY)) + 1
log_file_path = os.path.join(LOGS_DIRECTORY, f"log_{log_file_number}_{timestamp}.txt")

# Configure logging to output to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

def initialize_driver():
    """Initialize a new Selenium WebDriver, with window size adjustments."""
    logging.info("Initializing the Selenium WebDriver.")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")

    service = Service(GECKO_DRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)

    # Optional: Maximize or set a larger window size so elements are less likely out-of-bounds
    driver.set_window_size(1920, 1080)

    logging.info("WebDriver initialized successfully.")
    return driver

def close_main_page_popups(driver):
    """
    Attempt to close any pop-ups on the main page.
    Adjust selectors or timeouts as needed if the site has specific pop-ups.
    """
    try:
        logging.info("Attempting to close main page pop-ups (if any).")
        # Example: wait for a generic close button and click it
        popup_close = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".close"))
        )
        driver.execute_script("arguments[0].click();", popup_close)
        logging.info("Main page popup closed.")
    except:
        # No pop-up or unexpected pop-up
        pass

def safely_enter_naics_codes(driver, naics_list):
    """
    A safer approach to entering NAICS codes:
      1) Wait for #naics to be present & visible
      2) Scroll the element into view (centered)
      3) Attempt normal clear + send_keys
      4) If that fails, fallback to JS .value assignment
    """
    wait = WebDriverWait(driver, 30)
    naics_search_box = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#naics")))

    # Scroll the #naics box into the middle of the screen
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", naics_search_box)
    time.sleep(1)

    # Press ESC to possibly close any overlay
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
    time.sleep(1)

    # Enter each code
    for code in naics_list:
        try:
            # Attempt normal approach
            naics_search_box.clear()
            time.sleep(0.5)
            naics_search_box.send_keys(code.strip())
            time.sleep(1)
            naics_search_box.send_keys(Keys.RETURN)
            time.sleep(2)
        except Exception as e:
            logging.warning(f"Normal send_keys failed on NAICS {code}. Trying JS fallback. Error: {e}")

            # JavaScript fallback
            driver.execute_script("arguments[0].value='';", naics_search_box)
            driver.execute_script("arguments[0].value=arguments[1];", naics_search_box, code.strip())
            driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", naics_search_box)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", naics_search_box)
            # Press ENTER
            naics_search_box.send_keys(Keys.RETURN)
            time.sleep(2)

def scrape_contracts(driver):
    """
    Scrape contracts from the target URL.
    Returns a pandas DataFrame of all contracts scraped or None on failure.
    """
    try:
        logging.info("Navigating to the target URL.")
        driver.get(TARGET_URL)
        logging.info("Opened target URL.")

        # Attempt to close any pop-ups on the main page
        close_main_page_popups(driver)

        wait = WebDriverWait(driver, 30)
        logging.info("Looking for the accordion container (#usa-accordion-item-7).")

        # Expand the accordion that contains #naics
        try:
            accordion_container = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#usa-accordion-item-7"))
            )
            driver.execute_script("arguments[0].click();", accordion_container)
            time.sleep(3)  # wait a bit for the accordion to fully expand
            logging.info("#usa-accordion-item-7 clicked (expanded).")
        except Exception as e:
            logging.warning(f"Could not find or click #usa-accordion-item-7: {e}")

        logging.info("Locating NAICS search box (#naics).")
        safely_enter_naics_codes(driver, NAICS_CODES)
        logging.info("NAICS codes entered.")

        # Now wait for pagination or results to appear
        total_pages_elem = wait.until(
            EC.presence_of_element_located((By.ID, "bottomPagination-currentPage"))
        )
        total_pages = int(total_pages_elem.get_attribute("max"))
        logging.info(f"Total pages to process: {total_pages}")

        all_contracts = []
        current_page = 1

        while current_page <= total_pages:
            logging.info(f"Processing page {current_page}...")
            time.sleep(5)

            # Each result in the list
            result_list = driver.find_elements(
                By.CSS_SELECTOR,
                "#main-container > app-frontend-search-home > div > "
                "div > div > div.desktop\\:grid-col-8.tablet-lg\\:grid-col-12.mobile-lg\\:grid-col-12 "
                "> search-list-layout > div:nth-child(2) > div > div > sds-search-result-list > div"
            )

            contracts_in_page = 0
            for idx, result in enumerate(result_list, start=1):
                try:
                    notice_id_raw = result.find_element(
                        By.CSS_SELECTOR,
                        "app-opportunity-result > div > div.grid-col-12.tablet\\:grid-col-9 > div:nth-child(2)"
                    ).text.strip()
                    notice_id = notice_id_raw.replace("Notice ID:", "").strip()

                    department_raw = result.find_element(
                        By.CSS_SELECTOR,
                        "div.grid-row.grid-gap.ng-star-inserted > div:nth-child(1) > div"
                    ).text.strip()
                    department = department_raw.replace("Department/Ind.Agency", "").strip()

                    contract_data = {
                        "Contract Name": result.find_element(
                            By.CSS_SELECTOR,
                            "app-opportunity-result > div > div.grid-col-12.tablet\\:grid-col-9 > div:nth-child(1)"
                        ).text.strip(),
                        "Notice ID": notice_id,
                        "Department": department,
                        "Contract Link": result.find_element(By.CSS_SELECTOR, "a[href]").get_attribute("href"),
                        "Failed Row": False,
                        "Incomplete Data": False,
                        "Total Attachments": 0,
                        "Date Scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    all_contracts.append(contract_data)
                    contracts_in_page += 1
                except Exception as e:
                    logging.error(f"Error extracting data for result {idx} on page {current_page}: {e}")
                    all_contracts.append({
                        "Contract Name": "Error extracting",
                        "Notice ID": "",
                        "Department": "",
                        "Contract Link": "",
                        "Failed Row": True,
                        "Incomplete Data": True,
                        "Total Attachments": 0,
                        "Date Scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

            logging.info(f"Scraped {contracts_in_page} contracts from page {current_page}.")

            # Go to the next page if any
            if current_page < total_pages:
                next_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "bottomPagination-nextPage"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
                current_page += 1
            else:
                break

        logging.info(f"Scraped a total of {len(all_contracts)} contracts.")
        return pd.DataFrame(all_contracts)

    except Exception as e:
        logging.error(f"Error during contract scraping: {e}")
        return None  # Return None so we can handle it gracefully

def clean_date_field(text_value, prefix):
    """
    Given the full text with a prefix, remove the prefix and return just the date/time part.
    If the prefix is not found, return the text_value as is.
    """
    if text_value and prefix in text_value:
        return text_value.replace(prefix, "").strip()
    return text_value.strip() if text_value else ""

def scrape_attachments(contract_link):
    """
    Scrape attachment details and required date fields from a contract link using a new Selenium session.
    Returns a tuple: (documents, general_published_date, original_published_date, updated_offers_due_date, original_offers_due_date)
    """
    driver = initialize_driver()
    documents = []
    general_published_date = ""
    original_published_date = ""
    updated_offers_due_date = ""
    original_offers_due_date = ""

    try:
        driver.get(contract_link)
        logging.info(f"Processing contract link: {contract_link}")

        # Handle potential pop-up in detail page
        try:
            pop_up_close_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "usa-icon.ng-tns-c1762404166-1 > i-bs:nth-child(1) > svg:nth-child(1) > path:nth-child(1)")
                )
            )
            pop_up_close_button.click()
        except Exception:
            pass  # No pop-up detected or different selector

        # General Published Date
        try:
            gen_pub_date_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="general-published-date"]'))
            )
            general_published_date = clean_date_field(gen_pub_date_elem.text, "Updated Published Date:")
        except Exception as e:
            logging.warning(f"Could not find the general published date for {contract_link}: {e}")

        # Original Published Date
        try:
            orig_pub_date_elem = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="general-original-published-date"]'))
            )
            original_published_date = clean_date_field(orig_pub_date_elem.text, "Original Published Date:")
        except Exception as e:
            logging.warning(f"Could not find the original published date for {contract_link}: {e}")

        # Updated Date Offers Due
        try:
            upd_offers_date_elem = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="general-response-date"]'))
            )
            updated_offers_due_date = clean_date_field(upd_offers_date_elem.text, "Updated Date Offers Due:")
        except Exception as e:
            logging.warning(f"Could not find the updated offers due date for {contract_link}: {e}")

        # Original Date Offers Due
        try:
            orig_offers_date_elem = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="general-original-response-date"]'))
            )
            original_offers_due_date = clean_date_field(orig_offers_date_elem.text, "Original Date Offers Due:")
        except Exception as e:
            logging.warning(f"Could not find the original offers due date for {contract_link}: {e}")

        # Scroll to attachments
        attachments_section = None
        scroll_pause_time = 1
        scroll_height = 300
        current_position = 0

        while not attachments_section:
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(scroll_pause_time)
            current_position += scroll_height

            try:
                attachments_section = driver.find_element(
                    By.XPATH, '//*[@id="button-opp-view-attachments-accordion-section"]'
                )
            except Exception:
                pass

            # If we've scrolled to the bottom and can't find attachments, break
            if current_position > driver.execute_script("return document.body.scrollHeight"):
                logging.warning("Attachments section not found.")
                break

        # If found, gather attachments
        if attachments_section:
            index = 0
            attachments_found = 0
            while True:
                try:
                    name_xpath = f'//*[@id="opp-view-attachments-fileLinkId{index}"]'
                    date_xpath = f'//*[@id="opp-view-attachments-date{index}"]'
                    attachment = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, name_xpath))
                    )
                    updated_date = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, date_xpath))
                    )
                    documents.append({
                        "File Name": attachment.text.strip(),
                        "File Link": attachment.get_attribute("href"),
                        "Updated Date": updated_date.text.strip()
                    })
                    index += 1
                    attachments_found += 1
                except Exception:
                    break
            logging.info(f"Found {attachments_found} attachments for the contract.")

    except Exception as e:
        logging.error(f"Error processing {contract_link}: {e}")
    finally:
        driver.quit()

    return (
        documents,
        general_published_date,
        original_published_date,
        updated_offers_due_date,
        original_offers_due_date
    )

def send_email_with_attachment(output_path):
    """
    Send an email with the output CSV file attached using AWS SES.
    """
    ses_client = boto3.client(
        'ses',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    msg['Subject'] = f"Scraping Results - {timestamp}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = ", ".join(EMAIL_RECIPIENTS)

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Email body.
    text_part = MIMEText(
        f"Dear Recipient,\n\nPlease find attached the scraping results generated on {timestamp}.\n\nBest regards,\nYour Automated Scraper",
        'plain'
    )

    html_part = MIMEText(
        f"""\
        <html>
            <body>
                <p>Dear Recipient,<br><br>
                Please find attached the scraping results generated on {timestamp}.<br><br>
                Best regards,<br>
                Your Automated Scraper
                </p>
            </body>
        </html>
        """,
        'html'
    )

    # Attach the text and HTML parts to msg_body
    msg_body.attach(text_part)
    msg_body.attach(html_part)

    # Attach the multipart/alternative child container to the multipart/mixed parent container.
    msg.attach(msg_body)

    # Attachment
    try:
        with open(output_path, 'rb') as file:
            part = MIMEApplication(file.read(), Name=os.path.basename(output_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(output_path)}"'
        msg.attach(part)
    except Exception as e:
        logging.error(f"Failed to attach file: {e}")
        return

    # Send the email
    try:
        response = ses_client.send_raw_email(
            Source=EMAIL_SENDER,
            Destinations=EMAIL_RECIPIENTS,
            RawMessage={'Data': msg.as_string()}
        )
        logging.info("Email sent successfully.")
    except ClientError as e:
        logging.error(f"Failed to send email: {e.response['Error']['Message']}")

def test_rds_connection():
    """
    Test the connection to the AWS RDS PostgreSQL database.
    Returns True if the connection is successful, False otherwise.
    """
    RDS_HOST = os.getenv("RDS_HOST")
    RDS_DBNAME = os.getenv("RDS_DBNAME")
    RDS_USERNAME = os.getenv("RDS_USERNAME")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD")
    RDS_PORT = os.getenv("RDS_PORT")

    if not all([RDS_HOST, RDS_DBNAME, RDS_USERNAME, RDS_PASSWORD, RDS_PORT]):
        logging.error("Missing RDS credentials in .env file.")
        return False

    try:
        # Attempt to connect to the database
        conn = psycopg2.connect(
            host=RDS_HOST,
            database=RDS_DBNAME,
            user=RDS_USERNAME,
            password=RDS_PASSWORD,
            port=RDS_PORT,
        )
        conn.close()
        logging.info("Successfully connected to the RDS PostgreSQL database.")
        return True
    except Exception as e:
        logging.error(f"Failed to connect to RDS: {e}")
        return False

def save_to_rds(dataframe, timestamp):
    """
    Save the provided dataframe to an AWS RDS PostgreSQL database.
    A new table is created with a unique name for each run based on the timestamp.
    """
    # Test the database connection first
    if not test_rds_connection():
        logging.error("Aborting save operation due to failed database connection.")
        return

    # Database credentials from environment variables
    RDS_HOST = os.getenv("RDS_HOST")
    RDS_DBNAME = os.getenv("RDS_DBNAME")
    RDS_USERNAME = os.getenv("RDS_USERNAME")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD")
    RDS_PORT = os.getenv("RDS_PORT")

    try:
        conn = psycopg2.connect(
            host=RDS_HOST,
            database=RDS_DBNAME,
            user=RDS_USERNAME,
            password=RDS_PASSWORD,
            port=RDS_PORT,
        )
        cursor = conn.cursor()
        logging.info("Successfully connected to the RDS PostgreSQL database.")

        # Generate a unique table name
        table_name = f"scraped_data_{timestamp.replace('-', '_').replace(':', '_').replace(' ', '_')}"

        # Create the table dynamically based on the dataframe columns
        columns = dataframe.columns
        create_table_query = sql.SQL(
            "CREATE TABLE {table} ({fields});"
        ).format(
            table=sql.Identifier(table_name),
            fields=sql.SQL(", ").join(
                sql.Identifier(col) + sql.SQL(" TEXT") for col in columns
            ),
        )
        cursor.execute(create_table_query)
        conn.commit()
        logging.info(f"Table {table_name} created successfully.")

        # Insert the data into the table
        insert_query = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        ).format(
            table=sql.Identifier(table_name),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )

        for row in dataframe.itertuples(index=False, name=None):
            cursor.execute(insert_query, row)

        conn.commit()
        logging.info(f"Data successfully inserted into {table_name}.")
    except Exception as e:
        logging.error(f"Failed to save data to RDS: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            logging.info("Database connection closed.")

def process_combined_output():
    """
    Combine contracts and their attachments into a single cleaned CSV.
    """
    logging.info("Starting the data processing workflow.")
    driver = initialize_driver()
    contracts_df = scrape_contracts(driver)
    driver.quit()

    # If scraping failed or returned None, stop
    if contracts_df is None:
        logging.error("No contract data found (None returned). Exiting.")
        return

    combined_data = []
    total_attachments = 0
    failed_contracts = 0
    contracts_with_missing_data = 0
    contract_number = 1  # Start contract numbering

    for idx, row in contracts_df.iterrows():
        logging.info(f"Processing contract number {contract_number}.")
        contract_data = row.to_dict()
        contract_data["Contract Number"] = contract_number
        contract_link = contract_data["Contract Link"]

        # Scrape attachments & date fields
        (
            attachments,
            general_published_date,
            original_published_date,
            updated_offers_due_date,
            original_offers_due_date
        ) = scrape_attachments(contract_link)

        # Add the scraped dates to the contract data
        contract_data["General Published Date"] = general_published_date
        contract_data["Original Published Date"] = original_published_date
        contract_data["Updated Date Offers Due"] = updated_offers_due_date
        contract_data["Original Date Offers Due"] = original_offers_due_date

        # If no attachments found
        if not attachments:
            # Check if the Notice ID is missing => incomplete
            if not contract_data["Notice ID"]:
                contract_data["Incomplete Data"] = True
                contracts_with_missing_data += 1
                logging.warning(f"Contract {contract_number} has incomplete data.")
            combined_data.append(contract_data)
        else:
            # We have attachments
            contract_data["Total Attachments"] = len(attachments)
            for i, attachment in enumerate(attachments):
                if i == 0:
                    # First attachment row includes full contract info
                    combined_data.append({**contract_data, **attachment})
                else:
                    # Additional attachment rows replicate minimal data + the attachment
                    combined_data.append({
                        "Contract Number": contract_number,
                        "Contract Name": "",
                        "Notice ID": "",
                        "Department": "",
                        "Contract Link": "",
                        "Total Attachments": len(attachments),
                        "Failed Row": False,
                        "Incomplete Data": False,
                        "Date Scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "General Published Date": general_published_date,
                        "Original Published Date": original_published_date,
                        "Updated Date Offers Due": updated_offers_due_date,
                        "Original Date Offers Due": original_offers_due_date,
                        **attachment
                    })
            total_attachments += len(attachments)
            logging.info(f"Contract {contract_number} processed with {len(attachments)} attachments.")

        # Check if this row was flagged as failed
        if contract_data["Failed Row"]:
            failed_contracts += 1
            logging.warning(f"Contract {contract_number} failed to scrape properly.")

        contract_number += 1

    # Summary row
    summary = {
        "Contract Number": "Summary",
        "Contract Name": f"Total Contracts: {len(contracts_df)}",
        "Notice ID": f"Failed Contracts: {failed_contracts}",
        "Department": f"Contracts with Missing Data: {contracts_with_missing_data}",
        "Total Attachments": f"Total Attachments: {total_attachments}",
        "Date Scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "General Published Date": "",
        "Original Published Date": "",
        "Updated Date Offers Due": "",
        "Original Date Offers Due": ""
    }
    combined_data.append(summary)
    logging.info("Data processing completed.")

    # Save the final combined data with timestamp and unique numbering
    csv_file_number = len(os.listdir(FINAL_OUTPUT_DIRECTORY)) + 1
    output_path = os.path.join(
        FINAL_OUTPUT_DIRECTORY,
        f"final_combined_data_{csv_file_number}_{timestamp}.csv"
    )
    pd.DataFrame(combined_data).to_csv(output_path, index=False)
    logging.info(f"Final combined data saved to {output_path}")

    # Save to AWS RDS PostgreSQL
    save_to_rds(pd.DataFrame(combined_data), timestamp)

    # Send email with attachment
    send_email_with_attachment(output_path)

if __name__ == "__main__":
    process_combined_output()
