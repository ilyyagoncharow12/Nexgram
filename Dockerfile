FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем папки для загрузок
RUN mkdir -p static/uploads/avatars static/uploads/files static/uploads/photos static/uploads/videos static/uploads/audio static/uploads/favorites

# Открываем порт
ENV PORT=8080
EXPOSE 8080

# Запускаем приложение
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT main:app