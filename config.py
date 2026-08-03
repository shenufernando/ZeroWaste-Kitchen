import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    

    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:1234@localhost/zerowaste_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False