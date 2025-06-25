from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database init
def init_db():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password TEXT,
                        role TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        description TEXT,
                        filename TEXT,
                        subject TEXT,
                        semester TEXT,
                        uploaded_by INTEGER,
                        approved INTEGER DEFAULT 1,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        file_id INTEGER,
                        vote_type TEXT)''')
init_db()

# Routes
@app.route('/')
def home():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT f.*, u.username, (SELECT COUNT(*) FROM votes WHERE file_id = f.id AND vote_type='upvote') - (SELECT COUNT(*) FROM votes WHERE file_id = f.id AND vote_type='downvote') as net_votes FROM files f JOIN users u ON f.uploaded_by = u.id WHERE f.approved=1 ORDER BY timestamp DESC")
    files = cur.fetchall()
    return render_template('home.html', files=files)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        try:
            with sqlite3.connect('database.db') as con:
                cur = con.cursor()
                cur.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                            (username, email, password, role))
                con.commit()
                return redirect(url_for('login'))
        except:
            flash('User already exists or invalid input.')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cur.fetchone()
            if user and check_password_hash(user[3], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[4]
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject = request.form['subject']
        semester = request.form['semester']
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute("INSERT INTO files (title, description, filename, subject, semester, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, description, filename, subject, semester, session['user_id']))
            con.commit()
        return redirect(url_for('home'))
    return render_template('upload.html')

@app.route('/delete/<int:file_id>')
def delete_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT filename FROM files WHERE id=? AND uploaded_by=?", (file_id, session['user_id']))
        row = cur.fetchone()
        if row:
            filename = row[0]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            cur.execute("DELETE FROM files WHERE id=?", (file_id,))
            con.commit()
            flash('File deleted successfully.')
    return redirect(url_for('home'))

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/vote/<int:file_id>/<vote_type>')
def vote(file_id, vote_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM votes WHERE user_id=? AND file_id=?", (session['user_id'], file_id))
        if not cur.fetchone():
            cur.execute("INSERT INTO votes (user_id, file_id, vote_type) VALUES (?, ?, ?)",
                        (session['user_id'], file_id, vote_type))
            con.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)