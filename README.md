# Automated Contract Scraping and Data Processing System

## Overview

This project is an automated web scraper designed to extract contract data from [https://sam.gov/](https://sam.gov/), process it, and deliver the results via email while storing them in an AWS RDS PostgreSQL database. It leverages the following technologies:

- **Selenium**: For web scraping
- **Pandas**: For data manipulation
- **AWS SES**: For email notifications
- **AWS RDS**: For data storage

The system saves significant time (up to 93% compared to manual methods) and reduces errors in collecting contract details such as names, notice IDs, departments, attachments, and key dates. The output is a CSV file emailed to specified recipients and stored in a database.

Check Pdf in Directory for Documentation: `Automated Contract Scraping and Data Processing System.pdf`

AI Insights from Output CSV (Future work sample): `Deriving Insights from Scraped Contract Data Using AI.pdf`
> **Note**: This script is tailored for [https://sam.gov/](https://sam.gov/) with specific selectors. To scrape other websites, you’ll need to modify the code’s selectors and logic.

---

## Prerequisites

Before using this project, ensure you have the following:

- **Python**: Version 3.6 or higher
- **Firefox Browser**: Required for Selenium automation
- **geckodriver**: Download from [here](https://github.com/mozilla/geckodriver/releases) and place it in a directory in your system’s PATH
- **AWS Account**: Set up with SES (Simple Email Service) and RDS (Relational Database Service) configured
- **Python Libraries**: Listed in `requirements.txt`:
  - `selenium`
  - `pandas`
  - `boto3`
  - `psycopg2-binary`
  - `python-dotenv`

---

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Abhishekn1947/RFP-Web-Scraper.git
   cd RFP-Web-Scraper
   
2. **Install Dependencies:**:
   ```bash
   pip install -r requirements.txt
   
3. **Configure the `.env` File, copy paste below and paste into your .env:**
    ```bash
   # Path to the geckodriver executable (download from https://github.com/mozilla/geckodriver/releases)
    GECKO_DRIVER_PATH=/path/to/geckodriver
    
    # URL to start scraping contracts
    TARGET_URL=https://sam.gov/search/?page=1&pageSize=100&sort=-modifiedDate&index=opp&sfm%5BsimpleSearch%5D%5BkeywordRadio%5D=ALL&sfm%5Bstatus%5D%5Bis_active%5D=true&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B0%5D%5Bkey%5D=7&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B0%5D%5Bvalue%5D=7%20-%20IT%20AND%20TELECOM%20-%20INFORMATION%20TECHNOLOGY%20AND%20TELECOMMUNICATIONS&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B1%5D%5Bkey%5D=7A&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B1%5D%5Bvalue%5D=7A%20-%20IT%20AND%20TELECOM%20-%20APLLICATIONS&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B2%5D%5Bkey%5D=7B&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B2%5D%5Bvalue%5D=7B%20-%20IT%20AND%20TELECOM%20-%20COMPUTE&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B3%5D%5Bkey%5D=7C&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B3%5D%5Bvalue%5D=7C%20-%20IT%20AND%20TELECOM%20-%20DATA%20CENTER&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B4%5D%5Bkey%5D=7D&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B4%5D%5Bvalue%5D=7D%20-%20IT%20AND%20TELECOM%20-%20DELIVERY&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B5%5D%5Bkey%5D=7E&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B5%5D%5Bvalue%5D=7E%20-%20IT%20AND%20TELECOM%20-%20END%20USER&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B6%5D%5Bkey%5D=7F&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B6%5D%5Bvalue%5D=7F%20-%20IT%20AND%20TELECOM%20-%20IT%20MANAGEMENT&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B7%5D%5Bkey%5D=7G&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B7%5D%5Bvalue%5D=7G%20-%20IT%20AND%20TELECOM%20-%20NETWORK&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B8%5D%5Bkey%5D=7H&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B8%5D%5Bvalue%5D=7H%20-%20IT%20AND%20TELECOM%20-%20PLATFORM&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B9%5D%5Bkey%5D=7J&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B9%5D%5Bvalue%5D=7J%20-%20IT%20AND%20TELECOM%20-%20SECURITY%20AND%20COMPLIANCE&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B10%5D%5Bkey%5D=7K&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B10%5D%5Bvalue%5D=7K%20-%20IT%20AND%20TELECOM%20-%20STORAGE&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B11%5D%5Bkey%5D=D&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B11%5D%5Bvalue%5D=D%20-%20IT%20AND%20TELECOM%20-%20INFORMATION%20TECHNOLOGY%20AND%20TELECOMMUNICATIONS&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B12%5D%5Bkey%5D=DA&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B12%5D%5Bvalue%5D=DA%20-%20IT%20AND%20TELECOM%20-%20APLLICATIONS&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B13%5D%5Bkey%5D=DB&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B13%5D%5Bvalue%5D=DB%20-%20IT%20AND%20TELECOM%20-%20COMPUTE&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B14%5D%5Bkey%5D=DC&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B14%5D%5Bvalue%5D=DC%20-%20IT%20AND%20TELECOM%20-%20DATA%20CENTER&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B15%5D%5Bkey%5D=DD&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B15%5D%5Bvalue%5D=DD%20-%20IT%20AND%20TELECOM%20-%20DELIVERY&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B16%5D%5Bkey%5D=DE&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B16%5D%5Bvalue%5D=DE%20-%20IT%20AND%20TELECOM%20-%20END%20USER&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B17%5D%5Bkey%5D=DF&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B17%5D%5Bvalue%5D=DF%20-%20IT%20AND%20TELECOM%20-%20IT%20MANAGEMENT&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B18%5D%5Bkey%5D=DG&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B18%5D%5Bvalue%5D=DG%20-%20IT%20AND%20TELECOM%20-%20NETWORK&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B19%5D%5Bkey%5D=DH&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B19%5D%5Bvalue%5D=DH%20-%20IT%20AND%20TELECOM%20-%20PLATFORM&sfm%5BtypeOfNotice%5D%5B0%5D%5Bkey%5D=p&sfm%5BtypeOfNotice%5D%5B0%5D%5Bvalue%5D=Presolicitation&sfm%5BtypeOfNotice%5D%5B1%5D%5Bkey%5D=o&sfm%5BtypeOfNotice%5D%5B1%5D%5Bvalue%5D=Solicitation
    
    # Comma-separated list of NAICS codes to filter contracts (e.g., 518210,541511)
    NAICS_CODES=your-naics-codes
    
    # Directory to save the final CSV output (e.g., /path/to/output)
    FINAL_OUTPUT_DIRECTORY=/path/to/output
    
    # Directory to save log files (e.g., /path/to/logs)
    LOGS=/path/to/logs
    
    # AWS SES configuration (get these from your AWS account)(Comment out this part in the code if you dont want SES)
    AWS_REGION=us-east-1
    AWS_ACCESS_KEY_ID=your-aws-access-key
    AWS_SECRET_ACCESS_KEY=your-aws-secret-key
    EMAIL_SENDER=your-email@example.com
    EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
    
    # AWS RDS PostgreSQL configuration (get these from your RDS instance)
    RDS_HOST=your-rds-host
    RDS_DBNAME=your-db-name
    RDS_USERNAME=your-db-username
    RDS_PASSWORD=your-db-password
    RDS_PORT=5432


- Open .env in a text editor and fill in the required values (see for details), to create an .env run `touch .env`

- Must Have Firefox browser and coreesponding gecko driver for your pc specs (Mine is for an Apple macbook pro m3 max)

---

**Run Script**: `Python Main.py`

The script will:

- Scrape contract data from the specified `TARGET_URL.`
- Filter contracts using the provided `NAICS_CODES`.
- Process the data and generate a CSV file in `FINAL_OUTPUT_DIRECTORY`.
- Save the data to the specified `AWS RDS` database.
- Send the CSV file via email to `EMAIL_RECIPIENTS`.

---

## Output Example
- To see an example of the extracted data CSV, visit the `Sample_data.csv` in Final Csvs Folder.

---

## Troubleshooting

- Selenium Errors: Ensure geckodriver and Firefox are installed and in your PATH. For debugging, disable headless mode by commenting out options.add_argument("--headless") in initialize_driver() to see browser actions.
- AWS SES Errors: Verify AWS credentials and SES setup (e.g., verified sender email).
- RDS Issues: Check RDS security group settings to allow your IP. Test the connection with test_rds_connection().
- Website Changes: If https://sam.gov/ updates its structure, it will cause errors and script wont run,  update the CSS selectors/XPaths in the code.


