import os
import sqlite3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, get_current_date, get_current_time

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "hallo"
Session(app)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")
def get_db_connection():
  conn = sqlite3.connect('finance.db')
  conn.row_factory = sqlite3.Row
  return conn

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        #make shure stock's symbol exists or field is not empty
        symbol = request.form.get("symbol")
        if not symbol or lookup(symbol) is None:
            return apology("Invalid symbol. Pleas enter a valid stock symbol", 403)
        
        #get shares and check if it positive
        shares = float(request.form.get("shares"))
        if not shares or float(shares) < 0:
            return apology("Invalid number of shares. Please enter a positive number", 403)

        dict_lookup = lookup(symbol)
        stock_price = dict_lookup["price"]
        stock_name = dict_lookup["name"]
        stock_symbol = dict_lookup["symbol"]
        
        try:
          conn = get_db_connection()
          cursor = conn.cursor()

          if "user_id" in session:
            user_id = session["user_id"]
            cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
            user_balance_row = cursor.fetchone()
                
            new_balance = user_balance_row[0]
                
            if new_balance < (stock_price * shares):
              conn.close()
              return apology("not enough money on your account", 403)

            new_balance = new_balance - (stock_price * shares)

            conn.execute("UPDATE users SET cash = ? WHERE id = ?", (new_balance, user_id))
                
            #check for duplicates
            try:
              cursor.execute("INSERT INTO stocks (name, symbol) VALUES (?, ?)", (stock_name, stock_symbol))
              conn.commit()
            except sqlite3.IntegrityError:
              print(f"Stock with symbol {stock_symbol} already exists.")

            #Retrieve the stock ID
            cursor.execute("SELECT id FROM stocks WHERE symbol = ?", (stock_symbol,))
            stock_id_row = cursor.fetchone()
            stock_id = stock_id_row[0]

            #Log the transaction
            sort = "buy"
            current_time = get_current_time()
            current_date = get_current_date()
            conn.execute("INSERT INTO transactions (amount, type, buy_price, stock_id, user_id, time, date) VALUES (?, ?, ?, ?, ?, ?, ?)", (shares, sort, stock_price, stock_id, user_id, current_time, current_date))
               
            conn.commit()
            conn.close()
            return redirect("/")

          else:
            return apology("user_id error", 403)
        finally:
          conn.close()
    
    else:
        return render_template("buy.html")




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        username = request.form.get("username")
        password = request.form.get("password")

        # Query database for username
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id, hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

            if row is None: #ceck if user exists
                conn.close()
                return apology("invalid username and/or password", 403)

            if not password: #Check if password is provided
                conn.close()
                return apology("must provide password", 403)

            if check_password_hash(row["hash"], password):
                session["user_id"] = row["id"]
                conn.close()
                return redirect("/")
            else:
                conn.close()
                return apology("invalid username and/or password", 403)
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.close()
            return apology("Database error", 500) # Internal server error
        except TypeError as e:
            print(f"Type error: {e}")
            conn.close()
            return apology("A type error occurred", 500)
        finally:
            conn.close() # Ensure connection is always closed

    else:
        return render_template("login.html")
        #hashed_password = result[0]["hash"]
        

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
      symbol = request.form.get("quote")
      if not symbol:
        return apology("Symbol not found")
      else:
        lookup_dict = lookup(symbol)
        return render_template("quoted.html", data=lookup_dict) 
    else:
      return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    #user reached out via POST
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
           return apology ("username error")
        
        password = request.form.get("password")
        if not password:
            return appology("password error")
        
        check_password = request.form.get("check_password")
        if not check_password:
            return appology("password error")
        
        if check_password == password:

            conn = get_db_connection()
            cur = conn.cursor()

            try:
                hashed_password = generate_password_hash(password)
                conn.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                flash('Registratie succesvol!', 'succes')
                return redirect("/")
            except sqlite3.IntegrityError:
                flash("username already in use.", "error")
                return apology("TODO")
            finally:
                conn.close()
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")
