# API → Google Sheets Pipeline

Проект автоматизирует сбор данных с API, их обработку и загрузку в Google Sheets, а также отправку ежедневного отчёта на электронную почту.


## Функционал

- Сбор данных с API за последние 24 часа
- Обработка и фильтрация полученных записей
- Сохранение данных в локальную PostgreSQL базу
- Агрегация ежедневной статистики:
  - Всего попыток
  - Правильных ответов
  - Уникальных пользователей
- Загрузка статистики в Google Sheets
- Отправка email-отчёта с результатами
- Логирование всех действий и очистка старых логов (старше 3 дней)

---

## Установка и настройка

1. Клонировать репозиторий:

```bash
git clone https://github.com/your_username/your_repo.git
cd your_repo
```
2. Установить зависимости
```bash
pip install -r requirements.txt
```


3. Создать файл .env в корне проекта с переменными:

Настройки базы данных
```bash
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=your_db_port
```
Настройки API
```bash
API_URL=https://your-api.com
CLIENT=your_client
CLIENT_KEY=your_client_key
```
Настройки Google Sheets
```bash
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
SPREADSHEET_ID=your_google_sheet_id
```
Настройки Email
```bash
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
SENDER_EMAIL=you@example.com
EMAIL_PASSWORD=your_email_password
RECEIVER_EMAILS=receiver1@example.com,receiver2@example.com
```
## Использование

Просто запустите скрипт:
```bash
python mainv.py
```


Скрипт автоматически:
Создаст таблицу в базе (если её ещё нет)
Соберёт данные с API
Обработает данные и соберёт статистику
Загрузит данные в Google Sheets
Отправит email-отчёт

Логи
Логи сохраняются в папке logs/.
Старые логи (старше 3 дней) удаляются автоматически.
