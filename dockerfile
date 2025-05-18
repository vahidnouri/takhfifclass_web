# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set build arguments for DNS (optional)
ARG DNS1=8.8.8.8
ARG DNS2=8.8.4.4
RUN echo "nameserver ${DNS1}" > /etc/resolv.conf && \
    echo "nameserver ${DNS2}" >> /etc/resolv.conf

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --retries 10 -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "workers", "4"]
# CMD ["flask", "run", "--host=0.0.0.0"]
