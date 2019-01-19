from cs50 import SQL

db = SQL("sqlite:///finance.db")

# Query database for all albums
rows = db.execute("SELECT * FROM users")
print(rows)

# # For each album in database
# for row in rows:

#     # Print title of album
#     print(row['username'])