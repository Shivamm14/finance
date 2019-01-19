import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("postgres://rtekdmjnrurxxc:99f389156f59eb568a73009af2d1e0ecff4e8c2ed57043abc3f6b4235a2120af@ec2-54-225-89-195.compute-1.amazonaws.com:5432/d6aj8iesi5tvmp")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session['user_id'])[0]

    try:
        portrows = db.execute("SELECT stock, sum(shares) FROM portfolio WHERE user = :username GROUP BY stock", username = rows['username'])
        return render_template("index.html", portfolio = portrows, cash = rows['cash'])

    except IndexError:
        return render_template("index.html", stock = "", shares = "", cash = rows['cash'])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # if not (request.form.get("symbol") and request.form.get("share")):
        #     return apology("Must provide input")
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("invalid symbol");
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("enter positive integer")

        if shares < 0 or shares - round(shares) != 0 :
            return apology("enter positive number of shares to buy")
        rows =  db.execute("SELECT * FROM users where id = :user_id", user_id = session['user_id'] )[0]
        cash = rows['cash']
        reqCash = shares * quote['price']

        if reqCash > cash :
            return apology("Not enough Cash")
        else:

            db.execute("INSERT INTO portfolio VALUES(:user, :stock, :share, :price, datetime('now','localtime'))", user = rows['username'], stock = quote['symbol']
                        , share = shares, price = quote['price'])
            db.execute("UPDATE users SET cash = :cash where id = :user_id", cash = cash - reqCash, user_id = session['user_id'])
            return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user =  db.execute("SELECT * FROM users where id = :user_id", user_id = session['user_id'] )[0]['username']
    rows = db.execute("SELECT * FROM portfolio WHERE user = :username order by dot desc", username = user)
    return render_template("history.html", portfolio = rows)



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

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


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
    if request.method == "GET":
        return render_template("quote.html")
    else:
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("invalid symbol")
        return render_template("quoted.html",name= quote["name"], symbol = quote["symbol"], price = quote["price"])

    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)
        elif  request.form.get("password") != request.form.get("confirmation") :
            return apology(" password do not match", 400)
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username do not exists
        if len(rows) == 1 :
            return apology("username already exists", 400)
        # Insert the new username and hashed password in the database
        db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                          username=request.form.get("username"),hash = generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("invalid symbol");
        shares = int(request.form.get("shares"))
        if shares < 0 :
            return apology("enter positive number of shares to buy")
        rows =  db.execute("SELECT * FROM users where id = :user_id", user_id = session['user_id'] )[0]
        cash = rows['cash']
        reqCash = shares * quote['price']

        db.execute("INSERT INTO portfolio VALUES(:user, :stock, :share, :price, datetime('now','localtime'))", user = rows['username'], stock = quote['symbol']
                        , share = -(shares), price = quote['price'])

        db.execute("UPDATE users SET cash = :cash where id = :user_id", cash = cash + reqCash, user_id = session['user_id'])
        return redirect("/")
    else:
        return render_template("sell.html")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add cash """
    if request.method == "POST":
        amount  = int(request.form.get("cash"))
        Cash = db.execute("SELECT cash FROM users where id = :user_id", user_id = session['user_id'] )[0]
        db.execute("UPDATE users SET cash = :cash where id = :user_id", cash = Cash['cash'] + amount, user_id = session['user_id'])
        return redirect("/")

    else:
        return render_template("addcash.html")






def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
