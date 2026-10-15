from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "your_secret_key_here"
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# User Model
class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(100), unique=True, nullable=False)
  password = db.Column(db.String(200), nullable=False)
  suggestions = db.relationship("Suggestion", backref="author", lazy=True)
  comments = db.relationship("Comment", backref="author", lazy=True)


# Suggestion Model
class Suggestion(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(150), nullable=False)
  category = db.Column(db.String(100), nullable=True, default="General")
  description = db.Column(db.Text, nullable=False)
  votes = db.Column(db.Integer, default=0)
  date_posted = db.Column(db.DateTime, default=datetime.utcnow)
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
  comments = db.relationship(
      "Comment", backref="parent_suggestion", lazy=True, cascade="all, delete"
  )


# Comment Model
class Comment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  body = db.Column(db.Text, nullable=False)
  date_posted = db.Column(db.DateTime, default=datetime.utcnow)
  suggestion_id = db.Column(
      db.Integer, db.ForeignKey("suggestion.id"), nullable=False
  )
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


# Recreate database tables cleanly
with app.app_context():
  db.create_all()


# Routes
@app.route("/")
def index():
  suggestions = Suggestion.query.order_by(Suggestion.votes.desc()).all()
  return render_template("index.html", suggestions=suggestions)


@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not username or not password or not confirm_password:
      flash("Please fill out all fields.")
      return redirect(url_for("register"))

    if password != confirm_password:
      flash("Passwords do not match! Please try again.")
      return redirect(url_for("register"))

    user_exists = User.query.filter_by(username=username).first()
    if user_exists:
      flash("Username already exists. Please choose another.")
      return redirect(url_for("register"))

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    flash("Account created successfully! Please log in.")
    return redirect(url_for("login"))

  return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
      login_user(user)
      return redirect(url_for("index"))
    else:
      flash("Invalid username or password. Please try again.")
      return redirect(url_for("login"))

  return render_template("login.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
  if request.method == "POST":
    username = request.form.get("username")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not username or not new_password or not confirm_password:
      flash("Please fill out all fields.")
      return redirect(url_for("reset_password"))

    user = User.query.filter_by(username=username).first()
    if not user:
      flash("Username not found.")
      return redirect(url_for("reset_password"))

    if new_password != confirm_password:
      flash("New passwords do not match.")
      return redirect(url_for("reset_password"))

    user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
    db.session.commit()

    flash("Password reset successfully! Please log in with your new password.")
    return redirect(url_for("login"))

  return render_template("reset_password.html")


@app.route("/logout")
@login_required
def logout():
  logout_user()
  return redirect(url_for("index"))


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
  if request.method == "POST":
    title = request.form.get("title")
    category = request.form.get("category")
    description = request.form.get("description")

    if title and description:
      new_suggestion = Suggestion(
          title=title,
          category=category,
          description=description,
          author=current_user,
      )
      db.session.add(new_suggestion)
      db.session.commit()
      return redirect(url_for("index"))
    else:
      flash("Please fill in both title and description.")

  return render_template("submit.html")


@app.route("/vote/<int:id>", methods=["POST"])
def vote(id):
  suggestion = Suggestion.query.get_or_404(id)
  suggestion.votes += 1
  db.session.commit()
  return redirect(url_for("index"))


@app.route("/comment/<int:suggestion_id>", methods=["POST"])
@login_required
def add_comment(suggestion_id):
  suggestion = Suggestion.query.get_or_404(suggestion_id)
  body = request.form.get("body")
  if body:
    new_comment = Comment(
        body=body, suggestion_id=suggestion.id, user_id=current_user.id
    )
    db.session.add(new_comment)
    db.session.commit()
  return redirect(url_for("index"))


if __name__ == "__main__":
  app.run(debug=True)