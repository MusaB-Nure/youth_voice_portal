from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==========================================
# CLUB ADMINISTRATORS LIST
# Add any member username here to grant them 
# full admin and project status control!
# ==========================================
ADMIN_USERNAMES = ['musa', 'co_leader_username', 'another_leader']

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    status = db.Column(db.String(50), nullable=False, default='Under Review')
    votes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    author = db.relationship('User', backref='suggestions')
    comments = db.relationship('Comment', backref='suggestion', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    author = db.relationship('User', backref='comments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    selected_category = request.args.get('category')
    if selected_category and selected_category != 'All':
        suggestions = Suggestion.query.filter_by(category=selected_category).order_by(Suggestion.votes.desc()).all()
    else:
        suggestions = Suggestion.query.order_by(Suggestion.votes.desc()).all()
        
    # Map categories to their corresponding background images inside static/images/
    category_images = {
        'Environment': 'Environment.jpg',
        'Education': 'health.jpg',       
        'Technology': 'Technology.jpg',
        'Community': 'Community.jpg',
        'Sports': 'Sports.jpg'
    }
    
    # Pick the image based on category, default to Environment.jpg if none matches
    bg_image = category_images.get(selected_category, 'Environment.jpg')

    return render_template('index.html', suggestions=suggestions, selected_category=selected_category, bg_image=bg_image)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('register'))
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        # Automatically check if the registered username is in our ADMIN_USERNAMES list
        is_admin = (username.lower() in [admin.lower() for admin in ADMIN_USERNAMES])
        
        hashed_password = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        
        if is_admin:
            flash('Registration successful! Registered as Club Administrator.')
        else:
            flash('Registration successful! Please log in.')
            
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('reset_password'))
            
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Username not found.')
            return redirect(url_for('reset_password'))
            
        user.password = generate_password_hash(new_password, method='scrypt')
        db.session.commit()
        flash('Password successfully updated! Please login.')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category', 'Community')
        
        new_suggestion = Suggestion(
            title=title, 
            description=description, 
            category=category, 
            user_id=current_user.id
        )
        db.session.add(new_suggestion)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('submit.html')

@app.route('/vote/<int:id>', methods=['POST'])
@login_required
def vote(id):
    suggestion = Suggestion.query.get_or_404(id)
    suggestion.votes += 1
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:suggestion_id>', methods=['POST'])
@login_required
def add_comment(suggestion_id):
    body = request.form.get('body')
    if body:
        new_comment = Comment(body=body, suggestion_id=suggestion_id, user_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:id>/<string:status>')
@login_required
def update_status(id, status):
    if not current_user.is_admin:
        flash('Unauthorized action.')
        return redirect(url_for('index'))
    suggestion = Suggestion.query.get_or_404(id)
    suggestion.status = status
    db.session.commit()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)