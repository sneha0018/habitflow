from flask import Flask,render_template,request,redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
import calendar 
import random

app = Flask(__name__)
app.secret_key = "habitflow_secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///habitflow.db"
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    first_login = db.Column(db.Boolean, default=True)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_name = db.Column(db.String(200))
    user_id = db.Column(db.Integer) 
    completed = db.Column(db.Boolean, default=False)

class HabitCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habit.id"))
    date = db.Column(db.Date) 
    note = db.Column(db.String(500))

    

def calculate_streak(habit_id):

    streak = 0

    today = date.today()

    while True:

        record = HabitCompletion.query.filter_by(
            habit_id=habit_id,
            date=today
        ).first()

        if record:
            streak += 1
            today = today - timedelta(days=1)
        else:
            break

    return streak 

def completed_today(habit_id):

    today = date.today()

    record = HabitCompletion.query.filter_by(
        habit_id=habit_id,
        date=today
    ).first()

    if record:
        return True
    else:
        return False   

def calculate_streak(habit_id):

    streak = 0

    completions = HabitCompletion.query.filter_by(
        habit_id=habit_id
    ).order_by(HabitCompletion.date.desc()).all()

    if not completions:
        return 0

    current_day = completions[0].date

    for record in completions:

        if record.date == current_day:
            streak += 1
            current_day = current_day - timedelta(days=1)
        else:
            break

    return streak     

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/register",methods=["GET","POST"])
def register():
    print(request.method)

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        new_user = User(name=name, email=email, password=password)
        

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("register.html")
   
with app.app_context():
    db.create_all()


def get_motivation(total_completed, total_habits):

    messages = [

        "Small progress each day builds powerful habits 🚀",

        "Consistency beats motivation. Keep going 🔥",

        "You’re building a better version of yourself 💪",

        "Your future self will thank you for today’s effort 🌱",

        "Stay focused. Every habit completed counts ⭐"
    ]

    if total_completed == total_habits:
        return "Perfect day! All habits completed 🏆"

    if total_completed == 0:
        return "Start small today. One habit can change everything 🌅"

    return random.choice(messages)
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()

        if user:
           session["user_id"] = user.id
           return redirect(url_for("dashboard"))

        else:
            return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get month & year from URL
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    today = date.today()

    if not year:
        year = today.year

    if not month:
        month = today.month

    # Days in selected month
    days_in_month = calendar.monthrange(year, month)[1]

    days = list(range(1, days_in_month + 1))

    # Month navigation
    prev_month = month - 1
    prev_year = year

    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year

    if next_month == 13:
        next_month = 1
        next_year += 1

    # Get user habits
    habits = Habit.query.filter_by(user_id=user_id).all()

    habit_data = []

    for habit in habits:

        history = []

        for day in days:

            habit_date = date(year, month, day)

            record = HabitCompletion.query.filter_by(
                habit_id=habit.id,
                date=habit_date
            ).first()

            ####completed_count = HabitCompletion.query.filter(
                #HabitCompletion.habit_id == habit.id,
                #db.extract('month', HabitCompletion.date) == month,
                #db.extract('year', HabitCompletion.date) == year
           # ).count()#####

            #progress = int((completed_count / days_in_month) * 100)

            history.append(True if record else False)

        # Calculate streak
        streak = calculate_streak(habit.id)

        completed_count = HabitCompletion.query.filter(
            HabitCompletion.habit_id == habit.id,
            db.extract('month', HabitCompletion.date) == month,
            db.extract('year', HabitCompletion.date) == year
        ).count()

        progress = int((completed_count / days_in_month) * 100) if days_in_month else 0

        habit_data.append({
            "habit": habit,
            "history": history,
            "streak": streak,
            "progress": progress
        })

    # Get user for first login guide
    user = db.session.get(User, user_id)

    today_completed = HabitCompletion.query.filter(
        db.extract('day', HabitCompletion.date) == date.today().day,
        db.extract('month', HabitCompletion.date) == date.today().month,
        db.extract('year', HabitCompletion.date) == date.today().year
    ).count()

    total_habits = len(habits)

    motivation = get_motivation(today_completed, total_habits)

    return render_template(
        "dashboard.html",
        habit_data=habit_data,
        days=days,
        year=year,
        month=month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        first_login=user.first_login,
        motivation=motivation
    )
@app.route("/add-habit", methods=["GET","POST"])
def add_habit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        habit_name = request.form["habit_name"]

        user_id = session["user_id"]

        new_habit = Habit(
        habit_name=habit_name,
        user_id=user_id
)

        db.session.add(new_habit)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_habit.html")


@app.route("/complete/<int:habit_id>")
def complete_habit(habit_id):

    user_id = session["user_id"]

    habit = Habit.query.filter_by(id=habit_id, user_id=user_id).first()

    if habit:

        today = date.today()

        completion = HabitCompletion(
            habit_id=habit_id,
            date=today
        )

        db.session.add(completion)
        db.session.commit()

    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():

    session.pop("user_id", None)

    return redirect(url_for("login"))

@app.route("/toggle-habit/<int:habit_id>/<int:day>")
def toggle_habit(habit_id, day):

    today = date.today()
    year = today.year
    month = today.month

    habit_date = date(year, month, day)

    record = HabitCompletion.query.filter_by(
        habit_id=habit_id,
        date=habit_date
    ).first()

    if record:
        db.session.delete(record)
        db.session.commit()

        return {"status": "removed"}

    else:
        new_record = HabitCompletion(
            habit_id=habit_id,
            date=habit_date
        )

        db.session.add(new_record)
        db.session.commit()

        return {"status": "done"}
@app.route("/guide-seen")
def guide_seen():

    user_id = session["user_id"]

    user = User.query.get(user_id)

    user.first_login = False

    db.session.commit()

    return ""
@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    habits = Habit.query.filter_by(user_id=user_id).all()

    total_habits = len(habits)

    habit_ids = [habit.id for habit in habits]

    completions = HabitCompletion.query.filter(
        HabitCompletion.habit_id.in_(habit_ids)
    ).count()

    habit_names = []
    habit_counts = []

    for habit in habits:

        count = HabitCompletion.query.filter_by(
            habit_id=habit.id
        ).count()

        habit_names.append(habit.habit_name)

        habit_counts.append(count)

    return render_template(
        "analytics.html",
        total_habits=total_habits,
        completions=completions,
        habit_names=habit_names,
        habit_counts=habit_counts
    )

@app.route("/delete-habit/<int:habit_id>")
def delete_habit(habit_id):

    habit = Habit.query.get(habit_id)

    if habit:
        db.session.delete(habit)
        db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/edit-habit/<int:habit_id>", methods=["GET", "POST"])
def edit_habit(habit_id):

    habit = Habit.query.get(habit_id)

    if request.method == "POST":

        habit.habit_name = request.form["habit_name"]

        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("edit_habit.html", habit=habit)

@app.route("/add-note/<int:habit_id>/<int:day>", methods=["GET", "POST"])
def add_note(habit_id, day):

    today = date.today()
    selected_date = today.replace(day=day)

    record = HabitCompletion.query.filter_by(
        habit_id=habit_id,
        date=selected_date
    ).first()

    if request.method == "POST":

        note = request.form["note"]

        if record:
            record.note = note
        else:
            record = HabitCompletion(
                habit_id=habit_id,
                date=selected_date,
                note=note
            )
            db.session.add(record)

        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_note.html")

if __name__ == "__main__":
    app.run(debug=True)