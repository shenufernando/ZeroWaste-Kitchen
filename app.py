from datetime import datetime
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, PantryItem, Recipe, SavedRecipe

# .env file 
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Extensions setup
db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Gemini Client 
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================

# Home / Dashboard Route
@app.route('/')
@app.route('/dashboard')
def home():
    if not current_user.is_authenticated:
        return render_template('index.html')
    
    items = PantryItem.query.filter_by(user_id=current_user.id).order_by(PantryItem.expiration_date.asc()).all()
    
    today = datetime.now().date()
    expiring_soon_count = sum(1 for item in items if 0 <= (item.expiration_date - today).days <= 3)
    expired_count = sum(1 for item in items if (item.expiration_date - today).days < 0)
    
    return render_template('dashboard.html', 
                           items=items, 
                           today=today, 
                           expiring_soon_count=expiring_soon_count, 
                           expired_count=expired_count)

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        plan_type = request.form.get('plan_type', 'Free')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered! Please login.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_pw, plan_type=plan_type)
        
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# ================= PANTRY MANAGEMENT ROUTES =================

# Add Pantry Item
@app.route('/pantry/add', methods=['POST'])
@login_required
def add_pantry_item():
    name = request.form.get('name')
    quantity = request.form.get('quantity')
    unit = request.form.get('unit')
    expiration_date_str = request.form.get('expiration_date')
    category = request.form.get('category')

    if name and expiration_date_str:
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date()
        new_item = PantryItem(
            name=name,
            quantity=float(quantity) if quantity else 1.0,
            unit=unit,
            expiration_date=expiration_date,
            category=category,
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Pantry item added successfully!', 'success')
    else:
        flash('Please fill in all required fields.', 'danger')

    return redirect(url_for('home'))

# Delete Pantry Item
@app.route('/pantry/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed from pantry.', 'info')
    return redirect(url_for('home'))

# Scan Pantry Item Image Route (AI Image Recognition)
@app.route('/pantry/scan', methods=['POST'])
@login_required
def scan_pantry_item():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
        
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    try:
        image_bytes = image_file.read()
        mime_type = image_file.content_type or 'image/jpeg'

        prompt = """
        Analyze this food/grocery item image and extract details. 
        Return ONLY a JSON object with this exact format:
        {
            "name": "Item Name",
            "category": "Produce" or "Dairy" or "Meat" or "Pantry" or "Bakery" or "Beverages" or "Other",
            "unit": "pcs" or "kg" or "g" or "l" or "ml" or "pack"
        }
        """

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ]
        )

        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= APP RUNNER =================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)