FROM python:3.11-slim

WORKDIR /app

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV DATA_DIR=/app/data

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create persistence data and connectors directory inside container
RUN mkdir -p /app/data/connectors
RUN mkdir -p /app/connectors

# Copy application files
COPY . /app

EXPOSE 8000

# Run the backend server
CMD ["python", "main.py"]
