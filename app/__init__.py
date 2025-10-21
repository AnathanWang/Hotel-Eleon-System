from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

# Инициализация расширений
db = SQLAlchemy()


def create_app(config_name='default'):
    """Фабрика приложений Flask"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Инициализация расширений с приложением
    db.init_app(app)
    
    # Регистрация blueprint'ов
    with app.app_context():
        from app.modules import rooms, bookings
        
        app.register_blueprint(rooms.bp)
        app.register_blueprint(bookings.bp)
        
        # Создание таблиц базы данных
        db.create_all()
    
    return app
