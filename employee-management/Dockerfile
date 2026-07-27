FROM python:3.9-slim

# 1. Create a non-root user for security
RUN useradd -m appuser

WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application files
COPY app.py .
COPY templates/ templates/

# 4. Grant ownership of /app to appuser so SQLite can create ems.db
RUN chown -R appuser:appuser /app

# 5. Switch to non-root user
USER appuser

EXPOSE 8080
CMD ["python", "app.py"]
