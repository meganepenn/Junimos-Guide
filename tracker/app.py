from flask import Flask, render_template
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="charles23!",   
        database="stardew"
    )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/villagers")
def villagers():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT villager_name, birthday_season, birthdate, can_marry FROM VILLAGER")
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("villagers.html", villagers=rows)

@app.route("/items")
def items():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT name, type, season FROM ITEM")
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("items.html", items=rows)

if __name__ == "__main__":
    app.run(debug=True)
