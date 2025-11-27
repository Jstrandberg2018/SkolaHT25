#Recept-databas med betyg och kommentarer

from flask import Flask, render_template, flash, url_for, session, redirect, request
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'hemlig_nyckel' #ändra till mer säker senare

DATABASE = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        admin INTEGER NOT NULL DEFAULT 0
                        )
                    """)

def get_user_by_username(username):
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row #gör möjligt att använda user['username']
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        return user

# Ny helper för att hämta användare via id
def get_user_by_id(user_id):
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        return cursor.fetchone()
        
def hash_password(plain_text_password):
    return generate_password_hash(plain_text_password)

def check_password(plain_text_password, hashed_password):
    return check_password_hash(hashed_password, plain_text_password)

@app.route('/')
def index():
    if session.get('username'):
        return redirect('recipe')
    return redirect('login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ''
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = request.form.get('admin')
        
        if username and password:
            user = get_user_by_username(username)
        
            if user and check_password(password, user['password']):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = bool(user['admin'])
                return redirect('recipe')
        
        flash('Fel användarnamn eller lösenord')
        
    return render_template('login.html', username=username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    username = ''
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = request.form.get('admin')
        
        admin = 1 if admin == '1' else 0
        
        if username and password:
            hashed_password = hash_password(password)
            
            with sqlite3.connect('app.db') as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                                   INSERT INTO users(username, password, admin)
                                   VALUES (?, ?, ?)
                                   """, (username, hashed_password, admin))
                    conn.commit()
                    flash('Användare skapad')
                    return redirect(url_for('login'))
                
                except sqlite3.IntegrityError:
                    flash('Användarnamnet upptaget')
                    
    return render_template('register.html', username=username)

@app.route('/admin')
def admin_index():
    if not session.get('username'):
        return redirect(url_for('login'))
    
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, admin FROM users ORDER BY username")
        users = cursor.fetchall()

    return render_template('admin.html', users=users)

@app.route('/admin/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not session.get('is_admin'):
        # redirect istället för render_template(url_for(...))
        return redirect(url_for('login' if not session.get('username') else 'recipe'))
    # använd id-hämtaren istället för get_user_by_username(user_id)
    user = get_user_by_id(user_id)
    if not user:
        return redirect(url_for('admin_index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        is_admin = 1 if request.form.get('admin') == 'on' else 0
        password = request.form.get('password', '').strip()

        if username:
            with sqlite3.connect('app.db') as conn:
                conn.row_factory = sqlite3.Row
            
                if password:
                    # kolumnen heter 'admin' i databasen, inte 'is_admin'
                    conn.execute('UPDATE users SET username = ?, password = ?, admin = ? WHERE id = ?', 
                                (username, hash_password(password), is_admin, user_id))
                else:
                    conn.execute('UPDATE users SET username = ?, admin = ? WHERE id = ?', 
                                (username, is_admin, user_id))
            return redirect(url_for('admin_index'))
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('login' if not session.get('username') else 'todo'))
    # Förhindra att admin raderar sig själv
    if session.get('user_id') == user_id:
        return redirect(url_for('admin_index'))
    
    with sqlite3.connect('app.db') as conn:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    return redirect(url_for('admin_index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/recipe')
def recipe():
    return render_template('recipe.html')

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)