from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# connecting database
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   
        database="stardew"
    )

# accessing home page
@app.route("/")
def home():
    return render_template("home.html")

# accessing villagers page
@app.route("/villagers")
def villagers():
    db = get_db_connection()
    cursor = db.cursor()
    
    season = request.args.get("season", "")
    can_marry_filter = request.args.get("can_marry", "")

    query = """
        SELECT villager_name, birthday_season, birthday_day, lives_in, can_marry
        FROM VILLAGER
        WHERE 1 = 1
    """
    params = []
    
    if season and season != "All":
        query += " AND birthday_season = %s"
        params.append(season)
        
    if can_marry_filter == "Yes":
        query += " AND can_marry = TRUE"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    # calling html file
    return render_template("villagers.html",
                           villagers=rows,
                           selected_season=season,
                           can_marry_filter=can_marry_filter)

@app.route("/rooms")
def rooms():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT roomid, name FROM ROOM ORDER BY roomid")
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("rooms.html", rooms=rows)

@app.route("/bundles")
def bundles():
    db = get_db_connection()
    cursor = db.cursor()

    room_id = request.args.get("roomid", "")
    seasonal = request.args.get("seasonal", "")

    query = """
        SELECT B.bundleid, B.name, R.name AS room_name, B.seasonal
        FROM BUNDLE B
        JOIN ROOM R ON B.roomid = R.roomid
        WHERE 1 = 1
    """
    params = []

    if room_id and room_id != "All":
        query += " AND B.roomid = %s"
        params.append(room_id)

    if seasonal == "Yes":
        query += " AND B.seasonal = TRUE"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.execute("SELECT roomid, name FROM ROOM ORDER BY roomid")
    rooms_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "bundles.html",
        bundles=rows,
        rooms_list=rooms_list,
        selected_room=room_id,
        seasonal_filter=seasonal,
    )

@app.route("/bundles/<int:bundle_id>")
def bundle_detail(bundle_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT B.name, R.name
        FROM BUNDLE B
        JOIN ROOM R ON B.roomid = R.roomid
        WHERE B.bundleid = %s
        """,
        (bundle_id,),
    )
    bundle_info = cursor.fetchone()

    cursor.execute(
        """
        SELECT I.name, I.type, I.season
        FROM COMMUNITY_CENTER_ITEM CCI
        JOIN ITEM I ON CCI.item_id = I.item_id
        WHERE CCI.bundleid = %s
        """,
        (bundle_id,),
    )
    items = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "bundle_detail.html",
        bundle=bundle_info,
        items=items,
        bundle_id=bundle_id,
    )
    
# accessing items page
@app.route("/items")
def items():
    db = get_db_connection()
    cursor = db.cursor()

    item_type = request.args.get("type", "")
    season = request.args.get("season", "")

    query = "SELECT name, type, season FROM ITEM WHERE 1 = 1"
    params = []

    if item_type and item_type != "All":
        query += " AND type = %s"
        params.append(item_type)

    if season and season != "All":
        query += " AND season = %s"
        params.append(season)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("items.html", items=rows,
                           item_type=item_type,
                           season=season)

@app.route("/villagers/new", methods=["GET", "POST"])
def new_villager():
    if request.method == "POST":
        name = request.form.get("villager_name")
        season = request.form.get("birthday_season")
        day = request.form.get("birthday_day")
        lives_in = request.form.get("lives_in")
        can_marry = 1 if request.form.get("can_marry") == "on" else 0

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO VILLAGER (villager_name, birthday_season, birthday_day, lives_in, can_marry)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, season, day, lives_in, can_marry))
        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("villagers"))

    return render_template("new_villager.html")

@app.route("/progress")
def progress():
    db = get_db_connection()
    cursor = db.cursor()

    player = request.args.get("player_name", "")
    status = request.args.get("status", "")  # "All", "Completed", "Incomplete"

    query = """
        SELECT P.progress_id,
               P.player_name,
               B.bundleid,
               B.name AS bundle_name,
               R.name AS room_name,
               P.completed,
               P.notes
        FROM USER_BUNDLE_PROGRESS P
        JOIN BUNDLE B ON P.bundleid = B.bundleid
        JOIN ROOM R ON B.roomid = R.roomid
        WHERE 1 = 1
    """
    params = []

    if player:
        query += " AND P.player_name = %s"
        params.append(player)

    if status == "Completed":
        query += " AND P.completed = TRUE"
    elif status == "Incomplete":
        query += " AND P.completed = FALSE"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "progress.html",
        progress_rows=rows,
        selected_player=player,
        selected_status=status
    )


@app.route("/progress/new", methods=["GET", "POST"])
def new_progress():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT bundleid, name FROM BUNDLE ORDER BY bundleid")
    bundles = cursor.fetchall()

    if request.method == "POST":
        player_name = request.form.get("player_name")
        bundleid = request.form.get("bundleid")
        completed = 1 if request.form.get("completed") == "on" else 0
        notes = request.form.get("notes")

        cursor.execute("""
            INSERT INTO USER_BUNDLE_PROGRESS (player_name, bundleid, completed, notes)
            VALUES (%s, %s, %s, %s)
        """, (player_name, bundleid, completed, notes))
        db.commit()

        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    cursor.close()
    db.close()

    return render_template("progress_form.html", mode="new", bundles=bundles, progress_row=None)


@app.route("/progress/<int:progress_id>/edit", methods=["GET", "POST"])
def edit_progress(progress_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT bundleid, name FROM BUNDLE ORDER BY bundleid")
    bundles = cursor.fetchall()

    cursor.execute("""
        SELECT progress_id, player_name, bundleid, completed, notes
        FROM USER_BUNDLE_PROGRESS
        WHERE progress_id = %s
    """, (progress_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    if request.method == "POST":
        player_name = request.form.get("player_name")
        bundleid = request.form.get("bundleid")
        completed = 1 if request.form.get("completed") == "on" else 0
        notes = request.form.get("notes")

        cursor.execute("""
            UPDATE USER_BUNDLE_PROGRESS
            SET player_name = %s,
                bundleid = %s,
                completed = %s,
                notes = %s
            WHERE progress_id = %s
        """, (player_name, bundleid, completed, notes, progress_id))
        db.commit()

        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    cursor.close()
    db.close()

    return render_template("progress_form.html", mode="edit", bundles=bundles, progress_row=row)


@app.route("/progress/<int:progress_id>/delete", methods=["POST"])
def delete_progress(progress_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM USER_BUNDLE_PROGRESS WHERE progress_id = %s", (progress_id,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for("progress"))


if __name__ == "__main__":
    app.run(debug=True)
