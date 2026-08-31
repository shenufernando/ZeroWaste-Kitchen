import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from datetime import datetime, timedelta
import os
import json
import io
from functools import wraps
from PIL import Image
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, PantryItem, Recipe, SavedRecipe, ShoppingItem

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Upload Folder Configuration for Profile Pictures & Recipe Images
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_message_category = 'info'

# Gemini AI Client Setup
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin Access Custom Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash("Access denied! Admin privileges required.", "danger")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor for Global Notifications
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

# Helper Function for Dynamic Redirects
def get_next_redirect(default_endpoint='pantry'):
    next_page = request.args.get('next') or request.referrer or url_for(default_endpoint)
    return redirect(next_page)

# ================= ROUTES =================

@app.route('/')
@app.route('/dashboard', endpoint='dashboard')
def home():
    if not current_user.is_authenticated:
        return render_template('index.html')
    
    # Filter strictly for the current logged-in user
    items = PantryItem.query.filter_by(user_id=current_user.id).order_by(PantryItem.expiration_date.asc()).all()
    today = datetime.now().date()
    
    expiring_soon_items = [item for item in items if item.expiration_date and 0 <= (item.expiration_date - today).days <= 3]
    expired_items = [item for item in items if item.expiration_date and (item.expiration_date - today).days < 0]
    
    featured_recipes = Recipe.query.order_by(Recipe.id.desc()).limit(5).all()
    
    # User-specific Money Saved calculation
    user_items_count = len(items)
    if user_items_count > 0:
        consumed_saved_count = user_items_count * 2
        est_money_saved = round(consumed_saved_count * 350.0, 2)
    else:
        est_money_saved = 0.0
    
    return render_template('dashboard.html',
                           items=items,
                           today=today,
                           expiring_soon_count=len(expiring_soon_items),
                           expired_count=len(expired_items),
                           est_money_saved=est_money_saved,
                           featured_recipes=featured_recipes)

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
    cuisine_type = data.get('cuisine_type', 'Any')
    max_time = data.get('max_time', '30')

    if not selected_ingredients:
        return jsonify({'error': 'Please select at least one ingredient!'}), 400

    prompt = f"""
    Act as a Zero-Waste Professional Chef and Nutritionist.
    Generate 2 creative, delicious, and healthy recipes using these primary ingredients from the user's pantry: {', '.join(selected_ingredients)}.
    
    Filters:
    - Meal Type: {meal_type}
    - Cuisine Style: {cuisine_type}
    - Max Prep/Cook Time: {max_time} minutes
    
    Return ONLY a JSON object containing an array of recipes with this exact structure:
    {{
      "recipes": [
        {{
          "id": 1,
          "title": "Recipe Name",
          "time": "15 mins",
          "match_score": "95%",
          "health_match": 92,
          "nutrition": {{
            "calories": "320 kcal",
            "sugar": "4g",
            "cholesterol": "15mg"
          }},
          "used_ingredients": ["Ingredient 1 from pantry", "Ingredient 2 from pantry"],
          "missing_ingredients": ["Basic Pantry Staple 1", "Staple 2"],
          "instructions": [
            "Step 1 instruction",
            "Step 2 instruction"
          ],
          "youtube_query": "Recipe Name how to make"
        }}
      ]
    }}
    Ensure the recipes prioritize zero-waste, nutrition accuracy (health_match as an integer score out of 100 based on overall healthiness), and efficient use of the provided ingredients.
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

# ================= ADVANCED USER ANALYTICS ROUTE =================

@app.route('/analytics')
@login_required
def analytics():
    items = PantryItem.query.filter_by(user_id=current_user.id).all()
    today = datetime.now().date()
    
    total_items = len(items)
    expired_items = sum(1 for item in items if item.expiration_date and (item.expiration_date - today).days < 0)
    expiring_soon = sum(1 for item in items if item.expiration_date and 0 <= (item.expiration_date - today).days <= 3)
    fresh_items = max(0, total_items - (expired_items + expiring_soon))
    
    if total_items > 0:
        consumed_saved_count = total_items * 2
        est_money_saved = round(consumed_saved_count * 350.0, 2)
        est_co2_reduced = round(consumed_saved_count * 1.2, 1)
    else:
        est_money_saved = 0.0
        est_co2_reduced = 0.0

    waste_prevention_rate = round(((total_items - expired_items) / total_items * 100), 1) if total_items > 0 else 100.0

    categories = {}
    for item in items:
        cat = item.category if item.category else 'Pantry'
        categories[cat] = categories.get(cat, 0) + 1

    insights = []
    if expired_items > 0:
        insights.append(f"⚠️ You have {expired_items} expired item(s). Consider clearing them to keep your pantry organized.")
    if expiring_soon > 0:
        insights.append(f"🔥 {expiring_soon} item(s) are expiring in 3 days! Head to AI Recipes to use them before they go bad.")
    if waste_prevention_rate >= 80:
        insights.append("🌟 Excellent job! Your Zero-Waste score is above 80%. You are actively saving money and reducing footprint.")
    else:
        insights.append("💡 Tip: Plan meals using 'AI Recipe Generator' to increase your pantry consumption rate.")

    return render_template('analytics.html',
                           total_items=total_items,
                           expired_items=expired_items,
                           expiring_soon=expiring_soon,
                           fresh_items=fresh_items,
                           categories_json=json.dumps(categories),
                           est_money_saved=est_money_saved,
                           est_co2_reduced=est_co2_reduced,
                           waste_prevention_rate=waste_prevention_rate,
                           insights=insights)

# ================= SETTINGS ROUTE =================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        new_password = request.form.get('password')
        profile_picture = request.files.get('profile_picture') or request.files.get('profile_pic')

        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('This email address is already in use by another account.', 'danger')
            return redirect(url_for('settings'))

        current_user.name = name
        current_user.email = email

        if new_password:
            current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        if profile_picture and profile_picture.filename != '':
            filename = secure_filename(f"user_{current_user.id}_{profile_picture.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(filepath)
            
            if hasattr(current_user, 'profile_image'):
                current_user.profile_image = filename
            if hasattr(current_user, 'profile_pic'):
                current_user.profile_pic = filename

        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html')

# ================= SHOPPING LIST ROUTES =================

@app.route('/shopping-list')
@login_required
def shopping_list():
    items = ShoppingItem.query.filter_by(user_id=current_user.id).order_by(ShoppingItem.id.desc()).all()
    return render_template('shopping_list.html', items=items)

@app.route('/shopping-list/add', methods=['POST'])
@login_required
def add_shopping_item():
    name = request.form.get('name')
    if name:
        new_item = ShoppingItem(name=name, user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added to Shopping List!', 'success')
    return redirect(url_for('shopping_list'))

@app.route('/add-to-shopping-list', methods=['POST'])
@login_required
def add_missing_to_shopping_list():
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    added_count = 0
    for item_name in items:
        existing = ShoppingItem.query.filter_by(user_id=current_user.id, name=item_name, is_bought=False).first()
        if not existing:
            new_item = ShoppingItem(name=item_name, user_id=current_user.id)
            db.session.add(new_item)
            added_count += 1
            
    db.session.commit()
    return jsonify({'success': True, 'message': f'{added_count} items added to Shopping List!'})

@app.route('/shopping-list/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_shopping_item(item_id):
    item = ShoppingItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item.is_bought = not item.is_bought
        db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/shopping-list/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_shopping_item(item_id):
    item = ShoppingItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed.', 'info')
    return redirect(url_for('shopping_list'))

@app.route('/shopping-list/move-to-pantry/<int:item_id>', methods=['POST'])
@login_required
def move_to_pantry(item_id):
    shop_item = ShoppingItem.query.get_or_404(item_id)
    if shop_item.user_id == current_user.id:
        default_exp = datetime.now().date() + timedelta(days=7)
        new_pantry_item = PantryItem(
            name=shop_item.name,
            quantity=1.0,
            unit='pcs',
            expiration_date=default_exp,
            category='Pantry',
            user_id=current_user.id
        )
        db.session.add(new_pantry_item)
        db.session.delete(shop_item)
        db.session.commit()
        flash(f'"{shop_item.name}" moved to My Pantry!', 'success')
    return redirect(url_for('shopping_list'))

@app.route('/shopping-list/clear-completed', methods=['POST'])
@login_required
def clear_completed_shopping_items():
    ShoppingItem.query.filter_by(user_id=current_user.id, is_bought=True).delete()
    db.session.commit()
    flash('Completed items cleared!', 'info')
    return redirect(url_for('shopping_list'))

# ================= ADMIN ROUTES =================

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_items = PantryItem.query.count()
    users = User.query.order_by(User.id.desc()).all()
    featured_recipes = Recipe.query.all() if 'Recipe' in globals() else []

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_items=total_items,
                           users=users,
                           featured_recipes=featured_recipes)

@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    total_users = User.query.count()
    total_pantry_items = PantryItem.query.count()
    total_recipes = Recipe.query.count()

    today = datetime.now().date()
    all_pantry_items = PantryItem.query.all()

    fresh_items = sum(1 for item in all_pantry_items if item.expiration_date and (item.expiration_date - today).days > 3)
    expiring_soon = sum(1 for item in all_pantry_items if item.expiration_date and 0 <= (item.expiration_date - today).days <= 3)
    expired_items = sum(1 for item in all_pantry_items if item.expiration_date and (item.expiration_date - today).days < 0)

    ai_recipes = Recipe.query.filter_by(is_ai_generated=True).count()
    admin_recipes = Recipe.query.filter_by(is_ai_generated=False).count()

    return render_template('admin/analytics.html',
                           total_users=total_users,
                           total_pantry_items=total_pantry_items,
                           total_recipes=total_recipes,
                           fresh_items=fresh_items,
                           expiring_soon=expiring_soon,
                           expired_items=expired_items,
                           ai_recipes=ai_recipes,
                           admin_recipes=admin_recipes)

@app.route('/admin/recipes')
@login_required
@admin_required
def admin_recipes():
    featured_recipes = Recipe.query.all()
    return render_template('admin/recipes.html', featured_recipes=featured_recipes)

@app.route('/admin/edit-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    user.is_admin = bool(int(request.form.get('is_admin', 0)))
    
    db.session.commit()
    flash('User details updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own admin account!", "danger")
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(user)
    db.session.commit()
    flash("User account deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-featured-recipe', methods=['POST'])
@login_required
@admin_required
def add_featured_recipe():
    title = request.form.get('title')
    meal_type = request.form.get('meal_type', 'Any')
    cooking_time = request.form.get('cooking_time', '20 mins')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    image_file = request.files.get('image')

    image_filename = None
    if image_file and image_file.filename != '':
        filename = secure_filename(f"recipe_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(filepath)
        image_filename = filename

    if title:
        new_recipe = Recipe(
            title=title,
            meal_type=meal_type if meal_type else "Any",
            cooking_time=cooking_time if cooking_time else "20 mins",
            description=description,
            ingredients=ingredients if ingredients else "See detailed instructions",
            instructions=instructions if instructions else "See details",
            image_url=image_filename,
            is_ai_generated=False
        )
            
        db.session.add(new_recipe)
        db.session.commit()
        flash("Featured recipe published successfully!", "success")
    else:
        flash("Please provide a recipe title.", "danger")
        
    return redirect(url_for('admin_recipes'))

@app.route('/admin/edit-featured-recipe/<int:recipe_id>', methods=['POST'])
@login_required
@admin_required
def edit_featured_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    recipe.title = request.form.get('title')
    
    if hasattr(recipe, 'meal_type'):
        recipe.meal_type = request.form.get('meal_type')
    if hasattr(recipe, 'cooking_time'):
        recipe.cooking_time = request.form.get('cooking_time')
        
    recipe.description = request.form.get('description')
    recipe.ingredients = request.form.get('ingredients')
    recipe.instructions = request.form.get('instructions')

    image_file = request.files.get('image')
    if image_file and image_file.filename != '':
        filename = secure_filename(f"recipe_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(filepath)
        
        if hasattr(recipe, 'image_url'):
            recipe.image_url = filename
        elif hasattr(recipe, 'image'):
            recipe.image = filename

    db.session.commit()
    flash("Recipe updated successfully!", "success")
    return redirect(url_for('admin_recipes'))

@app.route('/admin/delete-featured-recipe/<int:recipe_id>', methods=['POST'])
@login_required
@admin_required
def delete_featured_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash("Featured recipe removed.", "info")
    return redirect(url_for('admin_recipes'))

# ================= AUTHENTICATION & PANTRY ROUTES =================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin_dashboard'))
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
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            
            if getattr(user, 'is_admin', False):
                return redirect(url_for('admin_dashboard'))
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

    return get_next_redirect('pantry')

@app.route('/pantry/consume/<int:item_id>', methods=['POST'])
@login_required
def consume_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item_name = item.name
        db.session.delete(item)
        db.session.commit()
        flash(f'Great job! "{item_name}" consumed successfully.', 'success')
    return get_next_redirect('pantry')

@app.route('/pantry/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_pantry_item(item_id):
    item = PantryItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed from pantry.', 'info')
    return get_next_redirect('pantry')

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
    return get_next_redirect('pantry')

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