FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium jest już w base image — rejestruje tylko ścieżkę
RUN playwright install chromium

COPY . .

EXPOSE 8000

CMD ["python", "run_panel.py", "--host", "0.0.0.0", "--port", "8000"]
