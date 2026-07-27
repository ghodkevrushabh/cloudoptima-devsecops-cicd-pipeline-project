# Using an ultra-lightweight 50MB Python base image
FROM python:3.9-slim

# Create a non-root user named 'appuser' for security
RUN useradd -m appuser

WORKDIR /app

# Copy only the requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly copy only the necessary application files
COPY app.py .
COPY templates/ templates/

# Switch away from root to the secure user
USER appuser

EXPOSE 8080
CMD ["python", "app.py"]
