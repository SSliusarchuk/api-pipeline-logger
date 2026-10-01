# API → Google Sheets Pipeline

This project automates the process of collecting data from an API, processing it, storing it in a PostgreSQL database, and uploading daily statistics to Google Sheets. It also sends a daily report by email.

## Features

- Collects data from the API for the last 24 hours
- Processes and filters received records
- Stores data in a local PostgreSQL database
- Calculates daily statistics:
  - Total number of attempts
  - Number of correct answers
  - Number of unique users
- Uploads daily statistics to Google Sheets
- Sends an email report with the results
- Logs all actions and removes logs older than 3 days

---

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/SSliusarchuk/api-pipeline-logger.git
cd api-pipeline-logger
```
## 2. Install dependencies

```bash
pip install requests python-dotenv psycopg2-binary google-api-python-client google-auth
```
## 3. Create a .env file

Create a .env file in the root directory of the project and add the following variables.
Database settings
```bash
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=your_db_port
```
API settings
```bash
API_URL=https://your-api.com
CLIENT=your_client
CLIENT_KEY=your_client_key
```
Google Sheets settings
```bash
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
SPREADSHEET_ID=your_google_sheet_id
```
Email settings
```bash
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
SENDER_EMAIL=you@example.com
EMAIL_PASSWORD=your_email_password
RECEIVER_EMAILS=receiver1@example.com,receiver2@example.com
```
## Usage

Run the main script:
```bash
python mainv.py
```


The script will automatically:

Create the database table if it does not exist
Collect data from the API
Process the received data
Calculate daily statistics
Save the data to PostgreSQL
Upload the statistics to Google Sheets
Send an email report
Create logs and remove logs older than 3 days
