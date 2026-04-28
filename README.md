# Workout Tracker

A Flask web application for logging workouts, browsing an exercise catalog, and receiving AI-style workout recommendations based on your training history.

## Features

- **User accounts** — select a user to log in (no password required; designed for personal/demo use)
- **Exercise catalog** — browse, filter by muscle group or equipment, and add custom exercises
- **Workout logging** — create workouts with multiple exercises, sets, reps, and optional weight (kg or lb)
- **Workout management** — view, edit, and delete past workouts
- **Stats** — total workouts, average exercises per session, top lifts, and most-trained muscle groups
- **Recommendations** — after logging 6+ workouts, get a suggested workout targeting your least-recently-trained muscle groups based on your history

## Tech Stack

- **Backend:** Python / Flask
- **Database:** PostgreSQL (via [Supabase](https://supabase.com)) + psycopg2
- **Frontend:** Jinja2 templates, plain HTML/CSS

## Project Structure

```
workout_tracker/
├── app/
│   ├── __init__.py        # App factory, secret key, teardown
│   ├── db.py              # psycopg2 connection helpers
│   ├── routes.py          # All route handlers
│   ├── static/
│   │   └── styles.css
│   ├── templates/         # Jinja2 HTML templates
│   └── tests/
│       └── test_catalog.py
├── sql/
│   ├── schema.sql         # Table definitions
│   ├── seed.sql           # Sample users / data
│   └── seed_exercise_catalog.sql
├── workoutTracker.py      # Flask entry point
├── run.py
├── .flaskenv              # FLASK_APP=workoutTracker.py
└── .env                   # DATABASE_URL (not committed)
```

## Database Schema

| Table | Purpose |
|---|---|
| `user` | App users |
| `workout` | Named workout plans per user |
| `exercise` | Global exercise catalog (name, muscle group, equipment) |
| `workout_exercise` | Exercises within a workout (sets, reps, weight) |

## Setup

### Prerequisites

- Python 3.10+
- A PostgreSQL database (local or hosted, e.g. Supabase)

### Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install flask psycopg2-binary python-dotenv
```

### Configure

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
SECRET_KEY=your-secret-key
```

### Initialize the database

```bash
psql $DATABASE_URL -f sql/schema.sql
psql $DATABASE_URL -f sql/seed_exercise_catalog.sql
psql $DATABASE_URL -f sql/seed.sql # Seeds base user, change username to your name. 
```

### Run

```bash
flask run
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

To stop the server: `Ctrl+C`  
To exit the virtual environment: `deactivate`

## Routes

| Method | Path | Description |
|---|---|---|
| GET/POST | `/login` | Select a user to log in |
| GET | `/logout` | Clear session |
| GET | `/dashboard` | Home — workout count summary |
| GET/POST | `/exercises` | Browse and add exercises |
| GET/POST | `/workouts/new` | Create a new workout |
| GET | `/workouts` | List all workouts |
| GET/POST | `/workouts/<id>/edit` | Edit a workout |
| POST | `/workouts/<id>/delete` | Delete a workout |
| GET/POST | `/recommend` | Get and log a recommended workout |
| GET | `/stats` | Personal training statistics |
