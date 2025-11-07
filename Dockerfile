FROM python:3.10

WORKDIR /app

COPY . .

# Install dependencies at build time
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Make script executable
RUN chmod +x start.sh

# Start bot using your script
CMD ["bash", "start.sh"]
