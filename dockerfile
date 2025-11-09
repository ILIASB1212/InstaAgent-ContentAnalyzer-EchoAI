# Use a lightweight official Python image suitable for web applications
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# 1. Copy only the requirements file first to take advantage of Docker layer caching
COPY requirements.txt .

# 2. Install all dependencies from the provided requirements.txt
# We use --no-cache-dir for smaller image size
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the application files into the container
# This includes app.py, the Agents/ and Tools/ directories
COPY . .

# Expose Streamlit's default port (8501)
EXPOSE 8501

# Command to run the Streamlit application
# We use 0.0.0.0 to bind to all interfaces inside the container, making it accessible externally.
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]