'''
Project: Ghibli Movie Discussion Forum
Purpose: A web application for users to discuss Ghibli movies.
Author: Jeetendra Karki
Date: 2025-05-29
Version: 1.0
This code is a Flask application that allows users to log in, register, and discuss Ghibli movies.
'''
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import pymysql
import re

# Install PyMySQL as MySQLdb
pymysql.install_as_MySQLdb()

# Flask app setup
app = Flask(__name__)
app.secret_key = 'totoro'

# MySQL database config
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://jeet:jeet@localhost/ghibli'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://jeet:jeet@localhost:3307/ghibli'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        try:
            with db.engine.connect() as conn:
                query = text('SELECT memberID, member_name, email, usrid FROM member WHERE usrid = :username AND usrpwd = :password')
                result = conn.execute(query, {"username": username, "password": password}).fetchone()
                if result:
                    session['loggedin'] = True
                    session['memberID'] = result.memberID
                    session['member_name'] = result.member_name
                    session['username'] = result.usrid
                    return redirect(url_for('movies'))
                else:
                    msg = 'Incorrect username or password!'
        except Exception as e:
            msg = f'Database error: {type(e).__name__}: {e}'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if not fullname or not username or not password or not email:
            msg = 'All fields are required.'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address.'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only letters and numbers.'
        else:
            try:
                with db.engine.connect() as conn:
                    check = text('SELECT * FROM member WHERE usrid = :username OR email = :email')
                    existing = conn.execute(check, {"username": username, "email": email}).fetchone()
                    if existing:
                        msg = 'Username or email already exists.'
                    else:
                        insert = text('INSERT INTO member (member_name, email, usrid, usrpwd) VALUES (:fullname, :email, :username, :password)')
                        conn.execute(insert, {
                            "fullname": fullname,
                            "email": email,
                            "username": username,
                            "password": password
                        })
                        conn.commit()
                        # msg = 'Registration successful! Please log in.'
                        # return redirect(url_for('login'))
                        msg = 'Registration successful! Please log in.'
                        return render_template('login.html', msg=msg)
            except Exception as e:
                msg = f'Registration error: {type(e).__name__}: {e}'
    return render_template('register.html', msg=msg)

@app.route('/movies')
def movies():
    if 'loggedin' in session:
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT movieID, title, releaseYear, director, length, rating FROM movie"))
                movies = result.fetchall()
                return render_template('movies.html', data=movies)
        except Exception as e:
            return render_template('logout.html', msg=f"Database error: {type(e).__name__}: {e}")
    return redirect(url_for('login'))

@app.route('/discussion/<int:movieNbr>')
def discussion(movieNbr):
    if 'loggedin' in session:
        try:
            with db.engine.connect() as conn:
                movie = conn.execute(text("SELECT title FROM movie WHERE movieID = :id"), {"id": movieNbr}).fetchone()
                movieTitle = movie.title if movie else 'Unknown'

                comments = conn.execute(text("""
                    SELECT d.discussionID, d.memberID, d.movieID, d.commentDate, d.comments, m.usrid
                    FROM discussion d
                    JOIN member m ON d.memberID = m.memberID
                    WHERE d.movieID = :id
                    ORDER BY d.commentDate DESC
                """), {"id": movieNbr}).fetchall()

                return render_template('discussion.html',
                                       movieID=movieNbr,
                                       movieTitle=movieTitle,
                                       comments=comments,
                                       memberID=session['memberID'])
        except Exception as e:
            return f"<h2 style='color:red;'>Database Error: {type(e).__name__}: {e}</h2>"
    return redirect(url_for('login'))

@app.route('/add_new_comment', methods=['POST'])
def add_new_comment():
    if 'loggedin' in session:
        try:
            movieID = request.form['movieID']
            comment_text = request.form['comment_text']
            memberID = session['memberID']

            with db.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO discussion (movieID, memberID, commentDate, comments)
                    VALUES (:movieID, :memberID, CURDATE(), :comments)
                """), {
                    "movieID": movieID,
                    "memberID": memberID,
                    "comments": comment_text
                })
                conn.commit()
        except Exception as e:
            return f"<h2 style='color:red;'>Failed to add comment: {e}</h2>"
        return redirect(url_for('discussion', movieNbr=movieID))
    return redirect(url_for('login'))

@app.route('/update_comment', methods=['POST'])
def update_comment():
    if 'loggedin' in session:
        try:
            commentID = request.form['commentID']
            movieID = request.form['movieID']
            updated = request.form['updated_comment']
            with db.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE discussion SET comments = :updated
                    WHERE discussionID = :commentID AND memberID = :memberID
                """), {
                    "updated": updated,
                    "commentID": commentID,
                    "memberID": session['memberID']
                })
                conn.commit()
        except Exception as e:
            return f"<h2 style='color:red;'>Update failed: {e}</h2>"
        return redirect(url_for('discussion', movieNbr=movieID))
    return redirect(url_for('login'))

@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    if 'loggedin' in session:
        try:
            commentID = request.form['commentID']
            movieID = request.form['movieID']
            with db.engine.connect() as conn:
                conn.execute(text("""
                    DELETE FROM discussion WHERE discussionID = :commentID AND memberID = :memberID
                """), {
                    "commentID": commentID,
                    "memberID": session['memberID']
                })
                conn.commit()
        except Exception as e:
            return f"<h2 style='color:red;'>Delete failed: {e}</h2>"
        return redirect(url_for('discussion', movieNbr=movieID))
    return redirect(url_for('login'))

# ----------------------------------------------------------
# Start the Flask server
# ----------------------------------------------------------

def main():
    app.run(debug=True)

if __name__ == '__main__':
    main()
