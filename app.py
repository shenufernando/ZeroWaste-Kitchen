import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from datetime import datetime
import os
import json
import io
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, PantryItem, Recipe, SavedRecipe

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Gemini AI Client Setup
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context Processor for Global Notifications (Shows notification on ALL pages)
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        items = PantryItem.query.filter_by(user_id=current_user.id).all()
        today = datetime.now().date()
        notifications = []
        for item in items:
            if item.expiration_date:
                days_left = (item.expiration_date - today).days
                if days_left < 0:
                    notifications.append(f"❌ {item.name} has expired!")
                elif days_left == 0:
                    notifications.append(f"⚠️ {item.name} expires today!")
                elif days_left <= 3:
                    notifications.append(f"📦 {item.name} expires in {days_left} days")
        return dict(notifications=notifications)
    return dict(notifications=[])

# ================= ROUTES =================

@app.route('/')
@app.route('/dashboard')
def home():
    if not current_user.is_authenticated:
        return render_template('index.html')
    
    items = PantryItem.query.filter_by(user_id=current_user.id).order_by(PantryItem.expiration_date.asc()).all()
    today = datetime.now().date()
    
    expiring_soon_items = [item for item in items if item.expiration_date and 0 <= (item.expiration_date - today).days <= 3]
    expired_items = [item for item in items if item.expiration_date and (item.expiration_date - today).days < 0]
    
    return render_template('dashboard.html', 
                           items=items, 
                           today=today, 
                           expiring_soon_count=len(expiring_soon_items), 
                           expired_count=len(expired_items))

@app.route('/pantry')
@login_required
def pantry():
    items = PantryItem.query.filter_by(user_id=current_user.id).order_by(PantryItem.expiration_date.asc()).all()
    today = datetime.now().date()
    return render_template('pantry.html', items=items, today=today)

@app.route('/recipes')
@login_required
def recipes():
    items = PantryItem.query.filter_by(user_id=current_user.id).order_by(PantryItem.expiration_date.asc()).all()
    today = datetime.now().date()
    return render_template('recipes.html', items=items, today=today)

@app.route('/generate-recipes', methods=['POST'])
@login_required
def generate_recipes():
    data = request.get_json()
    selected_ingredients = data.get('ingredients', [])
    meal_type = data.get('meal_type', 'Any')
    max_time = data.get('max_time', '30')

    if not selected_ingredients:
        return jsonify({'error': 'Please select at least one ingredient!'}), 400

    prompt = f"""
    Act as a Zero-Waste Professional Chef. 
    Generate 2 creative, delicious recipes using these primary ingredients from the user's pantry: {', '.join(selected_ingredients)}.
    
    Filters:
    - Meal Type: {meal_type}
    - Max Prep/Cook Time: {max_time} minutes
    
    Return ONLY a JSON object containing an array of recipes with this exact structure:
    {{
      "recipes": [
        {{
          "id": 1,
          "title": "Recipe Name",
          "time": "15 mins",
          "match_score": "95%",
          "used_ingredients": ["Ingredient 1 from pantry", "Ingredient 2 from pantry"],
          "missing_ingredients": ["Basic Pantry Staple 1", "Staple 2"],
          "instructions": [
            "Step 1 instruction",
            "Step 2 instruction"
          ]
        }}
      ]
    }}
    Ensure the recipes prioritize zero-waste and efficient use of the provided ingredients.
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        recipes_json = json.loads(response.text.strip())
        return jsonify(recipes_json)

    except Exception as e:
        return jsonify({'error': f'AI Generation failed: {str(e)}'}), 500

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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

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

    return redirect(url_for('pantry'))

@app.route('/pantry/consume/<int:item_id>', methods=['POST'])
@login_required
def consume_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item_name = item.name
        db.session.delete(item)
        db.session.commit()
        flash(f'Great job! "{item_name}" consumed successfully.', 'success')
    return redirect(url_for('pantry'))

@app.route('/pantry/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed from pantry.', 'info')
    return redirect(url_for('pantry'))

@app.route('/pantry/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item.name = request.form.get('name')
        item.category = request.form.get('category')
        item.quantity = float(request.form.get('quantity')) if request.form.get('quantity') else item.quantity
        item.unit = request.form.get('unit')
        
        exp_date_str = request.form.get('expiration_date')
        if exp_date_str:
            item.expiration_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            
        db.session.commit()
        flash('Item updated successfully!', 'success')
    return redirect(url_for('pantry'))

@app.route('/pantry/scan', methods=['POST'])
@login_required
def scan_pantry_item():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
        
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    try:
        raw_image = Image.open(image_file.stream)
        if raw_image.mode != 'RGB':
            raw_image = raw_image.convert('RGB')

        img_byte_arr = io.BytesIO()
        raw_image.save(img_byte_arr, format='JPEG')
        clean_image_bytes = img_byte_arr.getvalue()

        prompt = """
        Analyze this food/grocery item image and extract details. 
        Return ONLY a JSON object with this exact format:
        {
            "name": "Item Name",
            "category": "Produce",
            "unit": "pcs",
            "expiration_days": 7
        }
        Valid categories: Produce, Dairy, Meat, Pantry, Bakery, Beverages, Other
        Valid units: pcs, kg, g, l, ml, pack
        Provide estimated expiration_days based on freshness.
        """

        response = ai_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[
                types.Part.from_bytes(data=clean_image_bytes, mime_type='image/jpeg'),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text.strip())
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)