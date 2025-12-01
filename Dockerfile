# Базовый образ Python
FROM python:3.10-slim

# Установите рабочую директорию внутри контейнера
WORKDIR /app

# Копируйте файл зависимостей
COPY requirements.txt requirements.txt
# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируйте остальные файлы проекта
COPY . .

# Команда, которая будет запускаться при старте контейнера
CMD ["python", "main.py"]
