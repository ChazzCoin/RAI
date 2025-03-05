# syntax=docker/dockerfile:1

FROM ubuntu:22.04

ENV PYTHONUNBUFFERED=1

WORKDIR /python-docker

# Install Python and essential packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libsqlite3-dev \
    libpq-dev \
    libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 \
    openssh-server sudo \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH to support SFTP operations using internal-sftp
RUN sed -i 's|^Subsystem sftp.*|Subsystem sftp internal-sftp|' /etc/ssh/sshd_config

# Create the SSH runtime directory
RUN mkdir /var/run/sshd

# Create a non-root user 'developer' with password 'developer' and add to sudoers
RUN useradd -ms /bin/bash developer && \
    echo "developer:developer" | chpasswd && \
    adduser developer sudo

RUN apt-get update && apt-get install sqlite3

# Optional: Verify the SQLite version
RUN python3 -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"

# Copy and install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the desired port
EXPOSE 5180

# (Optional) Create and switch to a non-root user for improved security in production
RUN useradd -m appuser && chown -R appuser /python-docker
USER appuser

# Start the Quart app with Hypercorn
CMD ["hypercorn", "--bind", "0.0.0.0:5180", "api:app"]
