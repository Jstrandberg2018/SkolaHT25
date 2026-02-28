# Flask applikation för att hantera en receptdatabas med användare och administratörspanel

from flask import Flask, render_template, flash, url_for, session, redirect, request, jsonify
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# Initierar Flask applikationen
app = Flask(__name__)
# Genererar en säker slumpmässig nyckel för sessionhantering (64 tecken i hexadecimal)
app.secret_key = secrets.token_hex(32)

def create_tables():
    """
    Skapar databastabeller vid första körningen av applikationen.
    Tabellen 'users' lagrar användaruppgifter med hashade lösenord.
    Tabellen 'recipes' lagrar receptinformation med titel, ingredienser och kalorier.
    """
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        
        # Skapar användaratabellen med stöd för administratörsrättigheter
        cursor.execute(""" 
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        admin INTEGER NOT NULL DEFAULT 0
                        )
                    """)
        
        # Skapar recepttabellen med möjlighet att lagra ingredienser och kalorier
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recipes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        ingredients TEXT,
                        calories INTEGER
                    )
                    """)
        conn.commit()

def get_user_by_username(username):
    """
    Hämtar en användare från databasen baserat på användarnamn.
    Returnerar ett Row objekt som fungerar både som tuple och dictionary.
    """
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        return user

def get_user_by_id(user_id):
    """
    Hämtar en användare från databasen baserat på användarens ID.
    Används främst i administratörspanelen för att redigera användare.
    """
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        return cursor.fetchone()
        
def hash_password(plain_text_password):
    """
    Hashar ett lösenord med Werkzeug säkerhetsbibliotek.
    Detta skyddar användarnas lösenord i databasen.
    """
    return generate_password_hash(plain_text_password)

def check_password(plain_text_password, hashed_password):
    """
    Verifierar att ett angivet lösenord matchar det hashade lösenordet.
    Används vid inloggning för att kontrollera användarens identitet.
    """
    return check_password_hash(hashed_password, plain_text_password)

def get_all_recipes():
    """
    Hämtar alla recept från databasen sorterade efter ID.
    Returnerar en lista med Row objekt som innehåller receptinformation.
    """
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, ingredients, calories FROM recipes ORDER BY id")
        return cursor.fetchall()

def get_recipe_by_id(recipe_id):
    """
    Hämtar ett specifikt recept baserat på dess ID.
    Används för att visa eller redigera ett enskilt recept.
    """
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, ingredients, calories FROM recipes WHERE id = ?", (recipe_id,))
        return cursor.fetchone()

def create_recipe(title, ingredients=None, calories=None):
    """
    Skapar ett nytt recept i databasen.
    Tar titel som obligatoriskt argument samt valfria ingredienser och kalorier.
    Returnerar det nya receptets ID.
    """
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO recipes(title, ingredients, calories) VALUES (?, ?, ?)",
                       (title, ingredients, calories))
        conn.commit()
        return cursor.lastrowid

def update_recipe_db(recipe_id, title=None, ingredients=None, calories=None):
    """
    Uppdaterar ett befintligt recept i databasen.
    Använder COALESCE för att endast uppdatera de fält som skickas in.
    """
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE recipes
            SET title = COALESCE(?, title),
                ingredients = COALESCE(?, ingredients),
                calories = COALESCE(?, calories)
            WHERE id = ?
        """, (title, ingredients, calories, recipe_id))
        conn.commit()

def delete_recipe_db(recipe_id):
    """
    Raderar ett recept från databasen baserat på ID.
    Används när användaren vill ta bort ett recept permanent.
    """
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        conn.commit()

def ensure_recipe_columns():
    """
    Migrerar databasen för att lägga till kolumner för ingredienser och kalorier.
    Detta gör att äldre databaser kan uppdateras utan att förlora data.
    """
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        # Kontrollerar vilka kolumner som finns i recepttabellen
        cursor.execute("PRAGMA table_info(recipes)")
        cols = [r[1] for r in cursor.fetchall()]
        # Lägger till saknade kolumner om de inte redan finns
        if 'ingredients' not in cols:
            cursor.execute("ALTER TABLE recipes ADD COLUMN ingredients TEXT")
        if 'calories' not in cols:
            cursor.execute("ALTER TABLE recipes ADD COLUMN calories INTEGER")
        conn.commit()

@app.route('/')
def index():
    """
    Startsidan som omdirigerar användare beroende på inloggningsstatus.
    Inloggade användare går till receptsidan, annars till inloggning.
    """
    if session.get('username'):
        return redirect('recipe')
    return redirect('login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Hanterar användarinloggning med stöd för både formulär och JSON förfrågningar.
    Verifierar användaruppgifter och skapar en session vid lyckad inloggning.
    Lagrar användarens ID, användarnamn och adminrättigheter i sessionen.
    """
    if request.method == 'POST':
        # Stödjer både JSON från JavaScript och vanliga formulär
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

        if username and password:
            user = get_user_by_username(username)

            # Kontrollerar om användaren finns och lösenordet stämmer
            if user and check_password(password, user['password']):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = bool(user['admin'])
                
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "redirect": url_for("recipe")
                    })
                return redirect(url_for('recipe'))

        # Hanterar misslyckad inloggning
        if request.is_json:
            return jsonify({"success": False, "message": "Fel användarnamn eller lösenord"}), 400

        flash('Fel användarnamn eller lösenord')

    return render_template('login.html', hide_nav=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Hanterar registrering av nya användare.
    Hashar lösenordet innan det sparas i databasen för säkerhet.
    Kontrollerar att användarnamnet är unikt och ger felmeddelande vid konflikt.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = request.form.get('admin')
        
        # Konverterar checkboxvärde till 1 eller 0 för databas
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
                    # Hanterar fel när användarnamnet redan finns
                    flash('Användarnamnet upptaget')
                    
    return render_template('register.html', hide_nav=True)

@app.route('/admin')
def admin_index():
    """
    Administratörspanel som visar alla användare i systemet.
    Kräver att användaren är inloggad och har administratörsrättigheter.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('recipe'))
    
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, admin FROM users ORDER BY username")
        users = cursor.fetchall()

    return render_template('admin.html', users=users)

@app.route('/admin/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    """
    Möjliggör redigering av användare via administratörspanelen.
    Administratörer kan ändra användarnamn, lösenord och administratörsrättigheter.
    Om lösenordsfältet lämnas tomt behålls det gamla lösenordet.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('recipe'))
        
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
                cursor = conn.cursor()
            
                # Uppdaterar användaruppgifter beroende på om nytt lösenord angivits
                if password:
                    cursor.execute('UPDATE users SET username = ?, password = ?, admin = ? WHERE id = ?', 
                                (username, hash_password(password), is_admin, user_id))
                else:
                    cursor.execute('UPDATE users SET username = ?, admin = ? WHERE id = ?', 
                                (username, is_admin, user_id))
                conn.commit()
            return redirect(url_for('admin_index'))
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """
    Raderar en användare från systemet via administratörspanelen.
    Innehåller säkerhetscheck som förhindrar att admin raderar sitt eget konto.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('recipe'))
    
    # Förhindrar att administratören raderar sitt eget konto
    if session.get('user_id') == user_id:
        return redirect(url_for('admin_index'))
    
    with sqlite3.connect('app.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    return redirect(url_for('admin_index'))

@app.route('/logout')
def logout():
    """
    Loggar ut användaren genom att rensa all sessiondata.
    Omdirigerar sedan till inloggningssidan.
    """
    session.clear()
    return redirect(url_for('login'))

@app.route('/recipe', methods=['GET', 'POST'])
def recipe():
    """
    Huvudsidan för recept där användare kan lägga till nya recept.
    Visar ett formulär för att skapa recept med titel, ingredienser och kalorier.
    Kräver inloggning för att kunna använda funktionen.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('recipe', '').strip()
        ingredients = request.form.get('ingredients', '').strip() or None
        calories_raw = request.form.get('calories', '').strip()
        print(title, ingredients, calories_raw)
        
        # Konverterar kalorier till heltal med felhantering
        try:
            calories = int(calories_raw) if calories_raw != '' else None
        except ValueError:
            calories = None
            
        if title:
            create_recipe(title, ingredients=ingredients, calories=calories)
            
    recipes = get_all_recipes()
    return render_template('recipe.html', recipes=recipes)

@app.route('/recipe_collection/edit/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    """
    Möjliggör redigering av ett befintligt recept.
    Hämtar receptet från databasen och visar ett förifyllt formulär.
    Vid POST sparas de uppdaterade värdena i databasen.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    r = get_recipe_by_id(recipe_id)
    if not r:
        return redirect(url_for('recipe_collection'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip() or None
        ingredients = request.form.get('ingredients', '').strip() or None
        calories_raw = request.form.get('calories', '').strip()
        
        # Konverterar kalorier med felhantering
        try:
            calories = int(calories_raw) if calories_raw != '' else None
        except ValueError:
            calories = None
            
        update_recipe_db(recipe_id, title=title, ingredients=ingredients, calories=calories)
        return redirect(url_for('recipe_collection'))

    return render_template('edit_recipe.html', recipe=r)

@app.route('/delete/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    """
    Raderar ett recept från databasen.
    Använder POST metod för säkerhet och omdirigerar till receptsamlingen.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    delete_recipe_db(recipe_id)
    return redirect(url_for('recipe_collection'))

@app.route('/recipe_collection')
def recipe_collection():
    """
    Visar alla recept i en samlingsvy.
    Hämtar alla recept från databasen och presenterar dem i ett rutnät.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    recipes = get_all_recipes()
    return render_template('recipe_collection.html', recipes=recipes)

if __name__ == '__main__':
    # Skapar databastabeller vid applikationsstart
    create_tables()
    # Migrerar databasen för att säkerställa att alla kolumner finns
    ensure_recipe_columns()
    # Startar utvecklingsservern med debug läge aktiverat
    app.run(debug=True)