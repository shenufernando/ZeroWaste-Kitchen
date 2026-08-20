from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='User')
    plan_type = db.Column(db.String(20), default='Free')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    pantry_items = db.relationship('PantryItem', backref='owner', lazy=True, cascade="all, delete-orphan")
    saved_recipes = db.relationship('SavedRecipe', backref='user', lazy=True, cascade="all, delete-orphan")
    shopping_items = db.relationship('ShoppingItem', backref='user', lazy=True, cascade="all, delete-orphan")

class PantryItem(db.Model):
    __tablename__ = 'pantry_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='General')
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), nullable=True)
    added_date = db.Column(db.Date, default=datetime.utcnow().date)
    expiration_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Fresh')

class ShoppingItem(db.Model):
    __tablename__ = 'shopping_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), default="1")
    is_bought = db.Column(db.Boolean, default=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)

class Recipe(db.Model):
    __tablename__ = 'recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    
    # Nutrition Analytics
    calories = db.Column(db.Integer, nullable=True)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fats_g = db.Column(db.Float, nullable=True)
    
    is_ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedRecipe(db.Model):
    __tablename__ = 'saved_recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    recipe = db.relationship('Recipe')