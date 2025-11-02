import sqlite3

def databaseMenuInit():
    conn = sqlite3.connect('backend/database/menu.sql')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    conn.commit()
    c.close()

def databaseTransactionInit():
    conn = sqlite3.connect('backend/database/transaction.sql')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS transaction_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_value TEXT NOT NULL,
            adress TEXT NOT NULL,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            createdtime TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            phonenumber TEXT NOT NULL
        )
    ''')

    conn.commit()
    c.close()

def newPizza(pizzaName: str, pizzaPrice: float):
    with sqlite3.connect('backend/database/menu.sql') as conn:
        c = conn.cursor()

        c.execute("INSERT INTO menu (name, price) VALUES (?, ?)", (
            pizzaName,
            pizzaPrice
        ))

        conn.commit()
        c.close()

def writeTransaction(order, adress, firstname, lastname, phoneNumber):
    with sqlite3.connect('backend/database/transaction.sql') as conn:
        c = conn.cursor()

        c.execute("INSERT INTO transaction_table (order_value, adress, firstname, lastname, phonenumber) VALUES (?, ?, ?, ?, ?)", (
            order, adress, firstname, lastname, phoneNumber
        ))

        conn.commit()
        c.close()

def Menu():
    with sqlite3.connect('backend/database/menu.sql') as conn:
        c = conn.cursor()

        c.execute("SELECT * FROM menu")

        value = c.fetchall()
        c.close()
        print(value)
        return value

def gettransaction():
    with sqlite3.connect('backend/database/transaction.sql') as conn:
        c = conn.cursor()

        c.execute("SELECT * FROM transaction_table")

        value = c.fetchall()
        return value