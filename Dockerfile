# syntax=docker/dockerfile:1

FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

ENV PYTHONUNBUFFERED=1

WORKDIR /python-docker

# Install Python, essential packages, and Playwright dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3.11-venv python3-pip \
    libsqlite3-dev libpq-dev libdatrie-dev build-essential \
    libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libasound2 libpangocairo-1.0-0 \
    libatk1.0-0 libcairo2 libpango-1.0-0 libx11-xcb1 libxcursor1 \
    libxi6 libxtst6 openssh-server sudo sqlite3 \
    && rm -rf /var/lib/apt/lists/*


# Configure SSH for SFTP
RUN sed -i 's|^Subsystem sftp.*|Subsystem sftp internal-sftp|' /etc/ssh/sshd_config
RUN mkdir /var/run/sshd

# Create non-root user 'developer'
RUN useradd -ms /bin/bash developer && \
    echo "developer:developer" | chpasswd && \
    adduser developer sudo


# Set Python 3.11 as the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
# Install SQLite3
RUN apt-get update && apt-get install -y sqlite3
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libasound2 libpangocairo-1.0-0 libatk1.0-0 libcairo2 libpango-1.0-0 libx11-xcb1 libxcursor1 libxi6 libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies including Playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install browser_use
# Install Playwright browsers
RUN playwright install --with-deps chromium
RUN pip install browser_use
# Copy application code
COPY . .

# Adjust permissions
RUN chown -R developer:developer /python-docker

# Expose the required port
EXPOSE 5180

# Switch to non-root user
USER developer

# Start the Quart app with Hypercorn
CMD ["hypercorn", "--bind", "0.0.0.0:5180", "rapi:app"]
