# Use an official Python runtime as a parent image
FROM python:3.11

# Install curl
RUN apt-get update && \
	apt-get install -y curl && \
	rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5024 available to the world outside this container
EXPOSE 5024

# Define environment variable
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5024
ENV FLASK_ENV=production

# Run app.py when the container launches
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5024", "app:app"]
