import os
import logging
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import ast
from googleapiclient.discovery import build
from google.oauth2 import service_account
import smtplib, ssl
from email.message import EmailMessage
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

class LoggerManager:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.clean_old_logs()

        log_filename = os.path.join(self.log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        logging.basicConfig(
            filename=log_filename,
            filemode="a",
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.INFO,
            encoding="utf-8"
        )

    def clean_old_logs(self):
        now = datetime.now()
        for file in os.listdir(self.log_dir):
            if file.endswith(".log"):
                try:
                    log_date = datetime.strptime(file.replace(".log", ""), "%Y-%m-%d")
                    if (now - log_date).days > 3:
                        os.remove(os.path.join(self.log_dir, file))
                except ValueError:
                    pass

class DatabaseManager:
    def __init__(self):
        self.conn_params = dict(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )

    def create_table(self):
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS api_logs (
                            user_id TEXT,
                            oauth_consumer_key TEXT,
                            lis_result_sourcedid TEXT,
                            lis_outcome_service_url TEXT,
                            is_correct BOOLEAN,
                            attempt_type TEXT,
                            created_at TIMESTAMP
                        );
                    """)
                    conn.commit()
            logging.info("Таблиця перевірена або створена.")
        except Exception as e:
            logging.error(f"Помилка при створенні таблиці: {e}")

    def insert_records(self, records):
        if not records:
            logging.warning("Немає даних для вставки.")
            return
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(
                        cur,
                        """INSERT INTO api_logs (
                            user_id, oauth_consumer_key, lis_result_sourcedid,
                            lis_outcome_service_url, is_correct, attempt_type, created_at
                        ) VALUES %s;""",
                        records
                    )
                conn.commit()
            logging.info(f"Успішно вставлено {len(records)} записів у базу.")
        except Exception as e:
            logging.error(f"Помилка при вставці в базу: {e}")

    def get_daily_stats(self):
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            COUNT(*) AS total_attempts,
                            SUM(CASE WHEN is_correct = TRUE THEN 1 ELSE 0 END) AS correct_attempts,
                            COUNT(DISTINCT user_id) AS unique_users
                        FROM api_logs
                        WHERE created_at::date = CURRENT_DATE;
                    """)
                    stats = cur.fetchone()
                    return {
                        "total_attempts": stats[0],
                        "correct_attempts": stats[1] or 0,
                        "unique_users": stats[2]
                    }
        except Exception as e:
            logging.error(f"Помилка при агрегації даних: {e}")
            return None

class APIClient:
    def __init__(self):
        self.url = os.getenv("API_URL")
        self.client = os.getenv("CLIENT")
        self.client_key = os.getenv("CLIENT_KEY")

    def fetch_data(self):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        params = {
            "client": self.client,
            "client_key": self.client_key,
            "start": start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "end": end_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        try:
            logging.info("Початок запиту до API.")
            response = requests.get(self.url, params=params)
            response.raise_for_status()
            data = response.json()
            logging.info(f"Отримано {len(data)} записів з API.")
            return data
        except Exception as e:
            logging.error(f"Помилка при запиті до API: {e}")
            return []

class DataProcessor:
    @staticmethod
    def process(raw_data):
        records = []
        for row in raw_data:
            try:
                pb = ast.literal_eval(row.get("passback_params") or "{}")
                created_at = row.get("created_at")
                try:
                    created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                except Exception:
                    created_at_dt = None

                if not row.get("lti_user_id") or not row.get("attempt_type") or not created_at:
                    logging.warning(f"Пропущено запис через нестачу даних: {row}")
                    continue

                records.append((
                    row.get("lti_user_id"),
                    pb.get("oauth_consumer_key"),
                    pb.get("lis_result_sourcedid"),
                    pb.get("lis_outcome_service_url"),
                    bool(row.get("is_correct")) if row.get("is_correct") is not None else None,
                    row.get("attempt_type"),
                    created_at_dt
                ))
            except Exception as e:
                logging.error(f"Помилка при обробці запису: {e}")
        return records

class GoogleSheetsClient:
    def __init__(self):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        self.service = build("sheets", "v4", credentials=service_account.Credentials.from_service_account_file(credentials_file, scopes=scopes))
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")

    def ensure_headers(self):
        headers = ["date", "total_attempts", "correct_attempts", "unique_users"]
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Лист1!A1:D1"
            ).execute()
            values = result.get("values", [])
            if not values or values[0] != headers:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range="Лист1!A1:D1",
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()
                logging.info("Заголовки додані у Google Sheets.")
        except Exception as e:
            logging.error(f"Помилка при перевірці/додаванні заголовків: {e}")

    def upload(self, data):
        try:
            values = [[
                datetime.now().strftime("%Y-%m-%d"),
                data["total_attempts"],
                data["correct_attempts"],
                data["unique_users"]
            ]]
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Лист1!A:D",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": values}
            ).execute()
            logging.info("Дані успішно завантажені у Google Sheets.")
        except Exception as e:
            logging.error(f"Помилка при завантаженні у Google Sheets: {e}")

class EmailNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.port = int(os.getenv("SMTP_PORT"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.receivers = os.getenv("RECEIVER_EMAILS").split(",")

    def send(self, stats):
        try:
            subject = "Щоденний звіт: API → Google Sheets ✅"
            message = (
                f"Дата: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"Всього спроб: {stats['total_attempts']}\n"
                f"Правильних відповідей: {stats['correct_attempts']}\n"
                f"Унікальних користувачів: {stats['unique_users']}\n\n"
                f"Дані також завантажені у Google Sheets."
            )
            msg = EmailMessage()
            msg.set_content(message)
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(self.receivers)

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
                server.login(self.sender_email, self.password)
                server.send_message(msg)
            logging.info("Повідомлення успішно відправлено на пошту.")
        except Exception as e:
            logging.error(f"Помилка при відправці e-mail: {e}")

class Pipeline:
    def __init__(self, api_client, db, processor, sheets, emailer):
        self.api_client = api_client
        self.db = db
        self.processor = processor
        self.sheets = sheets
        self.emailer = emailer

    def run(self):
        self.db.create_table()
        raw_data = self.api_client.fetch_data()
        records = self.processor.process(raw_data)
        self.db.insert_records(records)
        stats = self.db.get_daily_stats()
        if stats:
            self.sheets.ensure_headers()
            self.sheets.upload(stats)
            self.emailer.send(stats)
        logging.info("Процес завершено.")

if __name__ == "__main__":
    LoggerManager()
    db = DatabaseManager()
    api = APIClient()
    sheets = GoogleSheetsClient()
    emailer = EmailNotifier()
    processor = DataProcessor()
    app = Pipeline(api, db, processor, sheets, emailer)
    app.run()