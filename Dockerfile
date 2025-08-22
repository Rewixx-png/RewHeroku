# Используем стабильный и поддерживаемый образ Debian 11 "Bullseye"
FROM python:3.10-slim-bullseye

# Устанавливаем переменные окружения для автоматической установки пакетов
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DOCKER=true \
    GIT_PYTHON_REFRESH=quiet

# Устанавливаем рабочую директорию
WORKDIR /app

# <<< ГЛАВНОЕ ИЗМЕНЕНИЕ: Принудительно исправляем источники пакетов (репозитории) >>>
# Это гарантирует, что apt-get будет искать пакеты в правильных, рабочих местах
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security/ bullseye-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main contrib non-free" >> /etc/apt/sources.list && \
    # Устанавливаем все системные зависимости в одной команде для оптимизации
    apt-get update -qq && apt-get install --no-install-recommends -y \
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
    # Устанавливаем Node.js
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    # Очищаем временные файлы и кэш apt-get, чтобы образ был меньше
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
