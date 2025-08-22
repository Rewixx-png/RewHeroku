# <<< ГЛАВНОЕ ИСПРАВЛЕНИЕ: Используем более новую и поддерживаемую версию Debian (Bullseye) >>>
FROM python:3.10-slim-bullseye

# Устанавливаем переменную, чтобы избежать интерактивных диалогов при установке пакетов
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем остальные переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DOCKER=true \
    GIT_PYTHON_REFRESH=quiet

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Выполняем все системные установки в ОДНОЙ команде для оптимизации
# Эта команда теперь будет работать, так как репозитории Bullseye активны
RUN apt-get update -qq && apt-get install --no-install-recommends -y \
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
    # Очищаем кэш apt-get, чтобы образ был меньше
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
