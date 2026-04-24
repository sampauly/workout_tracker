from flask import render_template, session, redirect, url_for, request, flash
from app.db import get_db
from app import app


@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        cur.execute('SELECT user_id, username FROM "user" WHERE user_id = %s', (user_id,))
        user = cur.fetchone()
        cur.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    cur.execute('SELECT user_id, username, email FROM "user" ORDER BY username')
    users = cur.fetchall()
    cur.close()
    return render_template('login.html', users=users)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM workout WHERE user_id = %s', (session['user_id'],))
    workout_count = cur.fetchone()[0]
    cur.close()
    return render_template('dashboard.html', workout_count=workout_count)
