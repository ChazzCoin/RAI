# syntax=docker/dockerfile:1
FROM python:3.9

# Set the working directory
WORKDIR /python-docker

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the desired port
EXPOSE 11434

# Start the Quart app with Hypercorn
CMD ["hypercorn", "--bind", "0.0.0.0:11434", "api:app"]
