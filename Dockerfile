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

# --- ИЗМЕНЕНИЕ: Разделяем установку на логические шаги для надежности ---

# Шаг 1: Обновляем репозитории и ставим базовые утилиты, необходимые для следующих шагов
RUN apt-get update -qq && apt-get install --no-install-recommends -y \
    curl \
    git \
    ca-certificates

# Шаг 2: Устанавливаем Node.js (этот шаг теперь кешируется отдельно)
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends nodejs

# Шаг 3: Добавляем ветки 'contrib' и 'non-free' для wkhtmltopdf и устанавливаем остальные зависимости
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list && \
    apt-get update -qq && \
    apt-get install --no-install-recommends -y \
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
