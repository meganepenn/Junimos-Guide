from flask import Flask, render_template, request, redirect, url_for, session, g
import mysql.connector

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "juicyfruit"


# connecting database
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   
        database="stardew"
    )

# getting current user info
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT user_id, email FROM APP_USER WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    return user

# loading user before request
@app.before_request
def load_logged_in_user():
    g.user = get_current_user()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# route to signup page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # finding email if it exists
        cursor.execute("SELECT user_id FROM APP_USER WHERE email = %s", (email,))
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()
            return render_template("signup.html", error="Email already registered.")

        password_hash = generate_password_hash(password)
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO APP_USER (email, password_hash) VALUES (%s, %s)",
            (email, password_hash),
        )
        db.commit()
        user_id = cursor.lastrowid

        # create initial session entry
        cursor.execute(
            """
            INSERT INTO USER_SESSION (user_id, ip_address, user_agent)
            VALUES (%s, %s, %s)
            """,
            (user_id, request.remote_addr, request.headers.get("User-Agent")),
        )
        db.commit()

        cursor.close()
        db.close()

        session["user_id"] = user_id
        return redirect(url_for("home"))

    return render_template("signup.html")

# route to login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # verify user credentials
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, password_hash FROM APP_USER WHERE email = %s",
            (email,),
        )
        user = cursor.fetchone()

        if (user is None) or (not check_password_hash(user["password_hash"], password)):
            cursor.close()
            db.close()
            return render_template("login.html", error="Invalid email or password.")

        # create new session entry
        cursor2 = db.cursor()
        cursor2.execute(
            """
            INSERT INTO USER_SESSION (user_id, ip_address, user_agent)
            VALUES (%s, %s, %s)
            """,
            (user["user_id"], request.remote_addr, request.headers.get("User-Agent")),
        )
        db.commit()

        cursor2.close()
        cursor.close()
        db.close()

        session["user_id"] = user["user_id"]
        return redirect(url_for("home"))

    return render_template("login.html")

# route to logout
@app.route("/logout")
@login_required
def logout():
    user_id = g.user["user_id"]

    db = get_db_connection()
    cursor = db.cursor()

    # update logout time for latest session
    cursor.execute(
        """
        UPDATE USER_SESSION
        SET logout_time = CURRENT_TIMESTAMP
        WHERE user_id = %s
        ORDER BY login_time DESC
        LIMIT 1
        """,
        (user_id,),
    )
    db.commit()

    cursor.close()
    db.close()

    session.clear()
    return redirect(url_for("home"))

# route to profiles page
@app.route("/profiles", methods=["GET", "POST"])
@login_required
def profiles():
    db = get_db_connection()

    # adding new profile
    if request.method == "POST":
        display_name = request.form.get("display_name")
        favorite_farm_name = request.form.get("favorite_farm_name")

        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO PLAYER_PROFILE (user_id, display_name, favorite_farm_name)
            VALUES (%s, %s, %s)
            """,
            (g.user["user_id"], display_name, favorite_farm_name),
        )
        db.commit()
        cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT player_id, display_name, favorite_farm_name, created_at "
        "FROM PLAYER_PROFILE WHERE user_id = %s",
        (g.user["user_id"],),
    )
    profiles = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("profiles.html", profiles=profiles)

# route to select profile
@app.route("/profiles/select/<int:player_id>")
@login_required
def select_profile(player_id):
    db = get_db_connection()
    cursor = db.cursor()

    # verify profile belongs to user
    cursor.execute(
        "SELECT player_id FROM PLAYER_PROFILE WHERE player_id = %s AND user_id = %s",
        (player_id, g.user["user_id"]),
    )
    row = cursor.fetchone()

    cursor.close()
    db.close()

    if not row:
        return redirect(url_for("profiles"))

    session["player_id"] = player_id
    session.pop("farm_id", None)

    return redirect(url_for("farms"))

# route to farms page
@app.route("/farms", methods=["GET", "POST"])
@login_required
def farms():
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("profiles"))

    db = get_db_connection()

    # adding a new farm
    if request.method == "POST":
        farm_name = request.form.get("farm_name")
        current_year = int(request.form.get("current_year"))
        current_season = request.form.get("current_season")
        current_day = int(request.form.get("current_day"))

        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO FARM_SAVE (player_id, farm_name, current_year, current_season, current_day)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (player_id, farm_name, current_year, current_season, current_day),
        )
        db.commit()
        cursor.close()

    # getting existing farms
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT farm_id, farm_name, current_year, current_season, current_day, created_at
        FROM FARM_SAVE
        WHERE player_id = %s
        ORDER BY created_at DESC
        """,
        (player_id,),
    )
    farms = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("farms.html", farms=farms)

# route to select farm
@app.route("/farms/select/<int:farm_id>")
@login_required
def select_farm(farm_id):
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("profiles"))

    db = get_db_connection()
    cursor = db.cursor()

    # verify farm belongs to player
    cursor.execute(
        """
        SELECT farm_id FROM FARM_SAVE
        WHERE farm_id = %s AND player_id = %s
        """,
        (farm_id, player_id),
    )
    row = cursor.fetchone()

    cursor.close()
    db.close()

    if not row:
        return redirect(url_for("farms"))

    session["farm_id"] = farm_id
    return redirect(url_for("progress"))

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

# adding a new villager
@app.route("/villagers/new", methods=["GET", "POST"])
@login_required 
def new_villager():
    if request.method == "POST":
        name = request.form.get("villager_name")
        season = request.form.get("birthday_season") or None
        day = request.form.get("birthday_day") or None
        lives_in = request.form.get("lives_in") or None
        can_marry = 1 if request.form.get("can_marry") == "on" else 0

        # inserting new villager into database
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO VILLAGER (villager_name, birthday_season, birthday_day, lives_in, can_marry)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, season, day, lives_in, can_marry),
        )
        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("villagers"))

    return render_template("new_villager.html")

# accessing rooms page
@app.route("/rooms")
def rooms():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT roomid, name FROM ROOM ORDER BY roomid")
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("rooms.html", rooms=rows)

# accessing bundles page
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

# accessing bundle detail page
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
    cursor = db.cursor(dictionary=True)

    item_type = request.args.get("type", "All")
    season = request.args.get("season", "All")
    search = request.args.get("q", "").strip()

    query = """
        SELECT item_id, name, type, season, source, used_in
        FROM ITEM
        WHERE 1 = 1
    """
    params = []

    # filtering based on type, season, and search
    if item_type and item_type != "All":
        query += " AND type = %s"
        params.append(item_type)

    if season and season != "All":
        query += " AND season LIKE %s"
        params.append(f"%{season}%")

    if search:
        query += " AND (name LIKE %s OR used_in LIKE %s OR source LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY name"

    cursor.execute(query, params)
    items_rows = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT type
        FROM ITEM
        WHERE type IS NOT NULL AND type <> ''
        ORDER BY type
    """)
    type_rows = cursor.fetchall()
    types = [row["type"] for row in type_rows]

    cursor.execute("""
        SELECT DISTINCT season
        FROM ITEM
        WHERE season IS NOT NULL AND season <> ''
        ORDER BY season
    """)
    season_rows = cursor.fetchall()
    seasons = [row["season"] for row in season_rows]

    cursor.close()
    db.close()

    return render_template(
        "items.html",
        items=items_rows,
        item_type=item_type,
        season=season,
        types=types,
        seasons=seasons,
        search=search,
    )

# accessing the progress page
@app.route("/progress")
@login_required
def progress():
    # getting farm and player from session
    farm_id = session.get("farm_id")
    player_id = session.get("player_id")

    if not farm_id or not player_id:
        return redirect(url_for("farms"))

    db = get_db_connection()
    cursor = db.cursor()

    status = request.args.get("status", "")

    query = """
        SELECT P.progress_id,
               P.player_id,
               PP.display_name,
               P.farm_id,
               B.bundleid,
               B.name AS bundle_name,
               R.name AS room_name,
               P.completed,
               P.notes
        FROM USER_BUNDLE_PROGRESS P
        JOIN BUNDLE B ON P.bundleid = B.bundleid
        JOIN ROOM R ON B.roomid = R.roomid
        JOIN PLAYER_PROFILE PP ON P.player_id = PP.player_id
        WHERE P.farm_id = %s AND P.player_id = %s
    """
    params = [farm_id, player_id]

    # filtering by completion status
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
        selected_status=status,
    )

# adding a new progress entry
@app.route("/progress/new", methods=["GET", "POST"])
@login_required
def new_progress():
    farm_id = session.get("farm_id")
    player_id = session.get("player_id")
    if not farm_id or not player_id:
        return redirect(url_for("farms"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT bundleid, name FROM BUNDLE ORDER BY bundleid")
    bundles = cursor.fetchall()

    if request.method == "POST":
        bundleid = request.form.get("bundleid")
        completed = 1 if request.form.get("completed") == "on" else 0
        notes = request.form.get("notes")

        cursor.execute(
            """
            INSERT INTO USER_BUNDLE_PROGRESS (player_id, farm_id, bundleid, completed, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (player_id, farm_id, bundleid, completed, notes),
        )
        db.commit()
        new_id = cursor.lastrowid

        # audit log
        audit_cursor = db.cursor()
        audit_cursor.execute(
            """
            INSERT INTO AUDIT_LOG (user_id, action, table_name, row_pk, details)
            VALUES (%s, %s, %s, %s,
                    JSON_OBJECT('bundleid', %s, 'completed', %s))
            """,
            (g.user["user_id"], "CREATE_PROGRESS", "USER_BUNDLE_PROGRESS",
             str(new_id), bundleid, completed),
        )
        db.commit()
        audit_cursor.close()

        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    cursor.close()
    db.close()

    return render_template(
        "progress_form.html", mode="new", bundles=bundles, progress_row=None
    )

# editing a progress entry
@app.route("/progress/<int:progress_id>/edit", methods=["GET", "POST"])
@login_required
def edit_progress(progress_id):
    farm_id = session.get("farm_id")
    player_id = session.get("player_id")
    if not farm_id or not player_id:
        return redirect(url_for("farms"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT bundleid, name FROM BUNDLE ORDER BY bundleid")
    bundles = cursor.fetchall()

    cursor.execute(
        """
        SELECT progress_id, player_id, farm_id, bundleid, completed, notes
        FROM USER_BUNDLE_PROGRESS
        WHERE progress_id = %s AND farm_id = %s AND player_id = %s
        """,
        (progress_id, farm_id, player_id),
    )
    row = cursor.fetchone()

    if not row:
        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    if request.method == "POST":
        bundleid = request.form.get("bundleid")
        completed = 1 if request.form.get("completed") == "on" else 0
        notes = request.form.get("notes")

        cursor2 = db.cursor()
        cursor2.execute(
            """
            UPDATE USER_BUNDLE_PROGRESS
            SET bundleid = %s,
                completed = %s,
                notes = %s
            WHERE progress_id = %s
            """,
            (bundleid, completed, notes, progress_id),
        )
        db.commit()

        # audit log
        audit_cursor = db.cursor()
        audit_cursor.execute(
            """
            INSERT INTO AUDIT_LOG (user_id, action, table_name, row_pk, details)
            VALUES (%s, %s, %s, %s,
                    JSON_OBJECT('bundleid', %s, 'completed', %s))
            """,
            (g.user["user_id"], "UPDATE_PROGRESS", "USER_BUNDLE_PROGRESS",
             str(progress_id), bundleid, completed),
        )
        db.commit()
        audit_cursor.close()

        cursor2.close()
        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    cursor.close()
    db.close()

    return render_template("progress_form.html", mode="edit", bundles=bundles, progress_row=row)

# deleting a progress entry
@app.route("/progress/<int:progress_id>/delete", methods=["POST"])
@login_required
def delete_progress(progress_id):
    farm_id = session.get("farm_id")
    player_id = session.get("player_id")
    if not farm_id or not player_id:
        return redirect(url_for("farms"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT bundleid
        FROM USER_BUNDLE_PROGRESS
        WHERE progress_id = %s AND farm_id = %s AND player_id = %s
        """,
        (progress_id, farm_id, player_id),
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        return redirect(url_for("progress"))

    bundleid = row[0]

    # deleting the progress entry
    cursor.execute(
        "DELETE FROM USER_BUNDLE_PROGRESS WHERE progress_id = %s",
        (progress_id,),
    )
    db.commit()

    # audit log
    audit_cursor = db.cursor()
    audit_cursor.execute(
        """
        INSERT INTO AUDIT_LOG (user_id, action, table_name, row_pk, details)
        VALUES (%s, %s, %s, %s,
                JSON_OBJECT('bundleid', %s))
        """,
        (g.user["user_id"], "DELETE_PROGRESS", "USER_BUNDLE_PROGRESS",
         str(progress_id), bundleid),
    )
    db.commit()
    audit_cursor.close()

    cursor.close()
    db.close()
    return redirect(url_for("progress"))

# route to feedback page
@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    if request.method == "POST":
        category = request.form.get("category")
        message = request.form.get("message")

        # inserting feedback into database
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO FEEDBACK (user_id, category, message)
            VALUES (%s, %s, %s)
            """,
            (g.user["user_id"], category, message),
        )
        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("home"))

    return render_template("feedback.html")

# route to analytics home
@app.route("/analytics")
@login_required
def analytics_home():
    return render_template("analytics_home.html")

# route to completion analytics
@app.route("/analytics/completion")
@login_required
def analytics_completion():
    farm_id = session.get("farm_id")
    if not farm_id:
        return redirect(url_for("farms"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # getting summary per room
    cursor.execute(
        """
        SELECT
            R.roomid,
            R.name AS room_name,
            COUNT(DISTINCT B.bundleid) AS total_bundles,
            SUM(CASE WHEN P.completed = TRUE THEN 1 ELSE 0 END) AS completed_bundles,
            ROUND(
              100 * SUM(CASE WHEN P.completed = TRUE THEN 1 ELSE 0 END)
              / NULLIF(COUNT(DISTINCT B.bundleid), 0),
              1
            ) AS completion_pct
        FROM BUNDLE B
        JOIN ROOM R ON B.roomid = R.roomid
        LEFT JOIN USER_BUNDLE_PROGRESS P
            ON P.bundleid = B.bundleid AND P.farm_id = %s
        GROUP BY R.roomid, R.name
        ORDER BY R.roomid;
        """,
        (farm_id,),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("analytics_completion.html", rows=rows)

# route to rooms analytics
@app.route("/analytics/rooms")
@login_required
def analytics_rooms():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # get summary per room
    cursor.execute(
        """
        SELECT
            R.roomid,
            R.name AS room_name,
            COUNT(DISTINCT B.bundleid) AS num_bundles,
            COUNT(DISTINCT CCI.item_id) AS num_items,
            ROUND(
                COUNT(DISTINCT CCI.item_id) / NULLIF(COUNT(DISTINCT B.bundleid), 0),
                1
            ) AS avg_items_per_bundle
        FROM ROOM R
        JOIN BUNDLE B ON B.roomid = R.roomid
        JOIN COMMUNITY_CENTER_ITEM CCI ON CCI.bundleid = B.bundleid
        GROUP BY R.roomid, R.name
        ORDER BY num_items DESC;
        """
    )
    room_rows = cursor.fetchall()

    # get hardest bundles 
    cursor.execute(
        """
        SELECT
            B.bundleid,
            B.name AS bundle_name,
            R.name AS room_name,
            COUNT(DISTINCT CCI.item_id) AS num_items
        FROM BUNDLE B
        JOIN ROOM R ON B.roomid = R.roomid
        JOIN COMMUNITY_CENTER_ITEM CCI ON CCI.bundleid = B.bundleid
        GROUP BY B.bundleid, B.name, R.name
        ORDER BY num_items DESC, B.bundleid
        LIMIT 10;
        """
    )
    hardest_bundles = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "analytics_rooms.html",
        room_rows=room_rows,
        hardest_bundles=hardest_bundles,
    )

# route to birthdays analytics
@app.route("/analytics/birthdays")
def analytics_birthdays():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # get birthdays
    cursor.execute(
        """
        SELECT
            birthday_season AS season,
            COUNT(*) AS villager_count,
            GROUP_CONCAT(
              CONCAT(villager_name, ' (', birthday_day, ')')
              ORDER BY birthday_day SEPARATOR ', '
            ) AS villagers
        FROM VILLAGER
        GROUP BY birthday_season
        ORDER BY FIELD(birthday_season, 'Spring', 'Summer', 'Fall', 'Winter');
        """
    )
    by_season = cursor.fetchall()

    # sort birthdays
    cursor.execute(
        """
        SELECT villager_name, birthday_season, birthday_day, lives_in, can_marry
        FROM VILLAGER
        ORDER BY FIELD(birthday_season, 'Spring', 'Summer', 'Fall', 'Winter'),
                 birthday_day;
        """
    )
    upcoming = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "analytics_birthdays.html",
        by_season=by_season,
        upcoming=upcoming,
    )

if __name__ == "__main__":
    app.run(debug=True)
