# Automated Contract Scraping and Data Processing System

## 🔍 Overview

This project automates the extraction of contract data from [SAM.gov](https://sam.gov/), processes it, and delivers the results through:
- Email notifications via AWS SES
- Storage in an AWS RDS PostgreSQL database
- CSV file export

The system achieves up to **93% time savings** compared to manual collection methods and significantly reduces errors when collecting contract details such as:
- Contract names
- Notice IDs
- Departments
- Attachments
- Key dates

### 📚 Documentation

- **Detailed System Documentation**: See `Automated Contract Scraping and Data Processing System.pdf` in the project directory
- **AI Insights Documentation**: `Deriving Insights from Scraped Contract Data Using AI.pdf` (Future work sample)

> **Note**: This script is specifically tailored for SAM.gov with site-specific selectors. To adapt it for other websites, you'll need to modify the code's selectors and logic.

## 🛠️ Technologies Used

- **Selenium**: Web scraping and browser automation
- **Pandas**: Data manipulation and processing
- **AWS SES**: Email notification delivery
- **AWS RDS**: PostgreSQL database for persistent storage

## 📋 Prerequisites

Before running this project, ensure you have:

- **Python**: Version 3.6 or higher
- **Firefox Browser**: Required for Selenium automation
- **geckodriver**: [Download here](https://github.com/mozilla/geckodriver/releases) and place it in your system's PATH
- **AWS Account**: With SES and RDS services configured
- **Required Python Libraries**:
  - selenium
  - pandas
  - boto3
  - psycopg2-binary
  - python-dotenv

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Abhishekn1947/RFP-Web-Scraper.git
cd RFP-Web-Scraper
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Add the following configuration to your `.env` file (replace placeholder values with your actual credentials):

```
# Path to the geckodriver executable
GECKO_DRIVER_PATH=/path/to/geckodriver

# URL to start scraping contracts (preconfigured for IT & Telecom contracts)
TARGET_URL=https://sam.gov/search/?page=1&pageSize=100&sort=-modifiedDate&index=opp&sfm%5BsimpleSearch%5D%5BkeywordRadio%5D=ALL&sfm%5Bstatus%5D%5Bis_active%5D=true&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B0%5D%5Bkey%5D=7&sfm%5BserviceClassificationWrapper%5D%5Bpsc%5D%5B0%5D%5Bvalue%5D=7%20-%20IT%20AND%20TELECOM%20-%20INFORMATION%20TECHNOLOGY%20AND%20TELECOMMUNICATIONS&sfm%5BtypeOfNotice%5D%5B0%5D%5Bkey%5D=p&sfm%5BtypeOfNotice%5D%5B0%5D%5Bvalue%5D=Presolicitation&sfm%5BtypeOfNotice%5D%5B1%5D%5Bkey%5D=o&sfm%5BtypeOfNotice%5D%5B1%5D%5Bvalue%5D=Solicitation

# Comma-separated list of NAICS codes to filter contracts
NAICS_CODES=your-naics-codes

# Directory paths
FINAL_OUTPUT_DIRECTORY=/path/to/output
LOGS=/path/to/logs

# AWS SES configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
EMAIL_SENDER=your-email@example.com
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# AWS RDS PostgreSQL configuration
RDS_HOST=your-rds-host
RDS_DBNAME=your-db-name
RDS_USERNAME=your-db-username
RDS_PASSWORD=your-db-password
RDS_PORT=5432
```

> **Note**: For AWS security best practices, never commit the `.env` file to version control. Add it to your `.gitignore` file.

### 4. Run the Scraper

```bash
python Main.py
```

## 🔄 Process Flow

When executed, the script will:
1. Scrape contract data from SAM.gov based on the URL in your configuration
2. Filter contracts by the NAICS codes specified
3. Process and clean the data
4. Generate a CSV file in your specified output directory
5. Store the data in your AWS RDS database
6. Send the CSV file via email to your specified recipients

## 📊 Sample Output

For an example of the extracted data format, refer to `Sample_data.csv` in the Final CSV folder of the repository.

## ⚠️ Troubleshooting

### Selenium Issues
- Ensure geckodriver and Firefox are properly installed and in your PATH
- For debugging, disable headless mode by commenting out `options.add_argument("--headless")` in the `initialize_driver()` function to see browser actions

### AWS SES Errors
- Verify your AWS credentials are correct
- Ensure your sender email is verified in AWS SES
- Check AWS SES sending limits and region settings

### RDS Connection Problems
- Check that your RDS security group allows connections from your IP address
- Verify your RDS credentials and database existence
- Test connection using the `test_rds_connection()` utility function

### Website Structure Changes
- If SAM.gov updates its structure, the script may fail due to selector changes
- Update the CSS selectors/XPaths in the code to match the new structure

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
