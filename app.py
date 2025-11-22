#Recept-databas med betyg och kommentarer

from flask import Flask, render_template, flash, url_for, session, redirect

app = Flask(__name__)

@app.route('/')
def index():
    if session.get('username'):
        return redirect('recipe')
    return redirect('login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)