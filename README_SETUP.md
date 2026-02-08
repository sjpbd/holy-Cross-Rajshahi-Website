# Holy Cross School and College, Rajshahi - Setup Guide

This guide will help you set up and run the Holy Cross School and College website project on your local machine.

## Prerequisites

- **Python**: Version 3.10 or higher is recommended.
- **Environment**: Access to a terminal/command prompt.

## Setup Instructions

### 1. Extract and Navigate
Extract the project files and open your terminal in the root directory:
```bash
cd "Final Website 29 Jan copy"
```

### 2. Create a Virtual Environment (Recommended)
It is recommended to use a virtual environment to keep dependencies isolated.
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
Install the required Python packages using the provided `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 4. Database Setup
The project uses SQLite for the database (pre-configured). Run the migrations to ensure the schema is up to date:
```bash
python manage.py migrate
```

### 5. Create a Superuser (Optional)
To access the admin panel (`/admin`), create a superuser account:
```bash
python manage.py createsuperuser
```

### 6. Run the Development Server
Start the Django development server:
```bash
python manage.py runserver
```

Once the server is running, you can access the website at:
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

## Project Structure

- `holy_cross/`: Project configuration and settings.
- `core/`: Main website logic and context processors.
- `notices/`, `news/`, `people/`, `clubs/`, `resources/`, `contact/`: Specific application modules.
- `templates/`: HTML templates (Base, Navbar, Footer, etc.).
- `static/`: CSS, JavaScript, and static image assets.
- `media/`: User-uploaded content (photos, documents).
- `requirements.txt`: List of Python dependencies.

## Key Technologies
- **Backend**: Django (Python)
- **Frontend**: Tailwind CSS, Alpine.js, htmx
- **Database**: SQLite3
- **Slider**: Swiper.js
