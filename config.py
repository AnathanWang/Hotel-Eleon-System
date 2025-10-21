import os
from pathlib import Path

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Базовая конфигурация приложения"""
    
    # Секретный ключ для Flask (в продакшене заменить на безопасный)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Конфигурация базы данных SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "hotel_eleon.db"}'
    
    # Отключаем отслеживание изменений (экономит память)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Часовой пояс
    TIMEZONE = 'Europe/Moscow'
    
    # Формат даты
    DATE_FORMAT = '%d.%m.%Y'
    DATETIME_FORMAT = '%d.%m.%Y %H:%M'
    
    # Настройки биллинга
    TAX_PERCENT = 10.0  # НДС 10%
    CURRENCY = 'руб.'
    CURRENCY_CODE = 'RUB'


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False


# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
