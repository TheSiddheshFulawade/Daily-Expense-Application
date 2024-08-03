# Daily Expense Application
This is a Daily Expense Application built using the Django REST Framework. It allows users to track their personal and group expenses, manage friends, send email reminders, and get summaries of their spending habits.

## Features

- User registration and authentication
- Personal and group expense tracking
- Friend management (add/remove friends)
- Expense splitting (Equal, Exact, Percentage)
- Email notifications for pending payments
- Balance sheet and transaction summary

## Technologies Used

- Django REST Framework: For for building the backend and creating RESTful APIs
- Celery: For handling asynchronous tasks and scheduled jobs
- Redis: As a message broker for Celery and for caching
- JWT: For secure authentication
- SQLite: For easy deployment
- Openpyxl: For generating Excel reports

## Setup and Installation

**Step 1: Clone the Repository**

```
git clone git@github.com:TheSiddheshFulawade/Daily-Expense-Application.git
```

**Step 2: Set Up a Virtual Environment**

Create a virtual environment and activate it. Once activated, install the necessary dependencies from the requirements.txt file:

```
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

**Step 3: Run the Django Server**

Navigate to the backend folder and start the server:

```
python manage.py runserver
```
**Step 4: Run the Celery Server**

Create two more terminals, navigate to the backend folder, and execute the following commands to start the Celery worker server and Celery beat server:

1. For Celery Worker:
```
celery -A daily_expense_system worker --pool=solo -l info
```

2. For Celery Beat:
```
celery -A daily_expense_system beat -l info
```
