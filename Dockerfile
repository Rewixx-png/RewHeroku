# Используем стабильный и поддерживаемый образ Debian 11 "Bullseye"
FROM python:3.10-slim-bullseye

# Устанавливаем переменные окружения
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

# Шаг 1: Принудительно исправляем источники пакетов (репозитории)
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security/ bullseye-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main contrib non-free" >> /etc/apt/sources.list

# Шаг 2: Обновляем списки и ставим базовые утилиты
RUN apt-get update -qq && apt-get install --no-install-recommends -y curl git ca-certificates

# Шаг 3: Устанавливаем Node.js
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends nodejs

# Шаг 4: Устанавливаем остальные тяжелые зависимости
RUN apt-get install --no-install-recommends -y \
    build-essential \
    ffmpeg \
    gcc \
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
    # Финальная очистка
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-warn-script-location -U -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Открываем порт
EXPOSE 8080

# Команда запуска
CMD ["python3", "-m", "heroku", "--root"]
