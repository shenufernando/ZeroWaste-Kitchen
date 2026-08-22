from app import app, db, bcrypt
from models import User

with app.app_context():
    hashed_pw = bcrypt.generate_password_hash("admin123").decode('utf-8')
    admin = User(
        name="Admin User", 
        email="admin@gmail.com", 
        password=hashed_pw, 
        role="Admin",       # is_admin වෙනුවට role="Admin" යොදන්න
        plan_type="Pro"
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin account created successfully! 🎉")