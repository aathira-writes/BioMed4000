import sqlite3
from database import datetime

db_name = "storage.db"

def get_db():
    return sqlite3.connect(db_name)

def create_db():
    connection = get_db()
    cursor = connection.cursor() #makes "cursor obeject" bc thats how SQL commands are executed

    # primary key is auto incrementing, so it will automatically assign a unique ID to each user and session
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS sessions (
        sessionID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (userID) REFERENCES users (userID) -- can only have sessions for existing users
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS conflicts(
                   conflictID INTEGER PRIMARY KEY AUTOINCREMENT,
                   login_user_id INTEGER NOT NULL,
                   detected_user_id INTEGER,  -- im leaving this not null in case we want to log where no face was detected/an unrecognized face was detected
                   timestamp TEXT NOT NULL, 
                   FOREIGN KEY (login_user_id) REFERENCES users (userID), 
                   FOREIGN KEY (detected_user_id) REFERENCES users (userID)
                   )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXSISTS transactions( 
                   transactionID INTEGER PRIMARY KEY AUTOINCREMENT, 
                   userID INTEGER NOT NULL, 
                   medID INTEGER NOT NULL, 
                   amount REAL NOT NULL, 
                   timestamp TEXT NOT NULL, 
                   FOREIGN KEY (userID) REFERENCES users (userID)
                   FOREIGN KEY (medID) REFERENCES medications (medID)
                   )""")
    
    connection.commit()
    connection.close()
