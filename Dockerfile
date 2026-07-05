# ISLI USR v2.0 skill: Morocco Public Procurement Scanner
# Valid MCR tags use an Ubuntu codename suffix (jammy/noble), not -python3.12.
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Avoid leaving pip cache in the image
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
