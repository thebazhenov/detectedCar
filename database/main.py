from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Создание базового класса для моделей
Base = declarative_base()

# Определение модели (пример таблицы users)
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Параметры подключения к PostgreSQL
# Формат: postgresql://username:password@host:port/database
DATABASE_URL = "postgresql://username:password@localhost:5432/mydatabase"

try:
    # Создание движка SQLAlchemy
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True для логирования SQL-запросов

    # Создание таблиц в базе данных
    Base.metadata.create_all(engine)

    # Создание сессии для работы с базой
    Session = sessionmaker(bind=engine)
    session = Session()

    # Пример: добавление нового пользователя
    new_user = User(name="John Doe", email="john@example.com")
    session.add(new_user)
    session.commit()

    # Пример: запрос всех пользователей
    users = session.query(User).all()
    for user in users:
        print(f"ID: {user.id}, Name: {user.name}, Email: {user.email}, Created: {user.created_at}")

except Exception as e:
    print(f"Ошибка: {e}")

finally:
    # Закрытие сессии
    session.close()