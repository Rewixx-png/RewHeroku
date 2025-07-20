FROM python:3.10 AS python-base
FROM python-base AS builder-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    AIOHTTP_NO_EXTENSIONS=1 \
    \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    \
    DOCKER=true \
    REWHOST=Lite \
    GIT_PYTHON_REFRESH=quiet

# Устанавливаем системные зависимости, как и раньше
RUN apt-get update && apt-get upgrade -y && apt-get install --no-install-recommends -y \
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
    python3 \
    python3-dev \
    python3-pip \
    wkhtmltopdf
RUN curl -sL https://deb.nodesource.com/setup_18.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get install -y nodejs && \
    rm nodesource_setup.sh
RUN rm -rf /var/lib/apt/lists/ /var/cache/apt/archives/ /tmp/*

# Создаем рабочую директорию
WORKDIR /data/Heroku

# <<< НАЧАЛО ИЗМЕНЕНИЙ >>>

# Удаляем 'RUN git clone' и 'RUN git pull'. Вместо этого:
# Сначала копируем только файл с зависимостями.
# Это позволяет Docker кэшировать установку библиотек, если они не менялись.
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-warn-script-location --no-cache-dir -U -r requirements.txt

# А теперь копируем ВЕСЬ остальной код юзербота.
# Если вы поменяете любой файл в репозитории, этот слой кэша станет недействительным,
# и Docker будет вынужден использовать свежую версию.
COPY . .

# <<< КОНЕЦ ИЗМЕНЕНИЙ >>>

EXPOSE 8080
CMD ["python", "-m", "heroku","--root"]
