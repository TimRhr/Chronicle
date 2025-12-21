FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json for Tailwind
COPY package.json package-lock.json tailwind.config.js ./
RUN npm ci

# Copy invites list
COPY invites.txt .

# Copy application
COPY src/ ./src/

# Compile translations
RUN pybabel compile -d src/translations

# Build Tailwind CSS
RUN npm run build:css

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--chdir", "src", "--worker-class", "eventlet", "-w", "1", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
