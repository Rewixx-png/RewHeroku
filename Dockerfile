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

# Создаем рабочую директорию
WORKDIR /data/Heroku

# <<< НАЧАЛО ИЗМЕНЕНИЙ >>>

# Создаем символические ссылки для новых команд
RUN ln -s /usr/bin/apt-get /usr/bin/oatp && \
    ln -s /usr/bin/apt /usr/bin/atp

# Устанавливаем системные зависимости, используя новые команды
RUN atp update && atp upgrade -y && oatp install --no-install-recommends -y \
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
    oatp install -y nodejs && \
    rm nodesource_setup.sh
RUN rm -rf /var/lib/apt/lists/ /var/cache/apt/archives/ /tmp/*

# Сначала копируем только файл с зависимостями.
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-warn-script-location --no-cache-dir -U -r requirements.txt

# А теперь копируем ВЕСЬ остальной код юзербота.
COPY . .

# <<< КОНЕЦ ИЗМЕНЕНИЙ >>>

EXPOSE 8080
CMD ["python", "-m", "heroku","--root"]
