# Используем официальный образ Python 3.10
FROM python:3.10-slim-buster

# Устанавливаем переменные окружения, чтобы избежать лишних логов и кэширования
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DOCKER=true \
    GIT_PYTHON_REFRESH=quiet

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# --- ГЛАВНОЕ ИСПРАВЛЕНИЕ ---
# Выполняем все системные установки в ОДНОЙ команде, чтобы уменьшить количество слоев и размер образа.
# 1. Обновляем списки пакетов
# 2. Устанавливаем все необходимые системные зависимости через apt-get
# 3. Скачиваем и выполняем скрипт для установки Node.js v18
# 4. Устанавливаем Node.js
# 5. Очищаем временные файлы и кэш apt-get, чтобы образ был меньше
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    ffmpeg \
    gcc \
    git \
    libavcodec-dev \
    libavdevice-dev \
    libavformat-dev \
    libavutil-dev \
    libcairo2 \
    libmagic1 \
    libswscale-dev \
    openssl \
    openssh-server \
    python3-dev \
    wkhtmltopdf && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

# Сначала копируем только файл с зависимостями для кэширования этого слоя
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-warn-script-location -U -r requirements.txt

# Копируем весь остальной код приложения
COPY . .

# Открываем порт, который будет слушать приложение
EXPOSE 8080

# Команда для запуска приложения при старте контейнера
CMD ["python3", "-m", "heroku", "--root"]
