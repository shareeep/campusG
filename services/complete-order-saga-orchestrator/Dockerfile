# Use official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy all files to the working directory
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Flask will run on
EXPOSE 5000

# CMD instruction removed - command will be specified in docker-compose.yml
