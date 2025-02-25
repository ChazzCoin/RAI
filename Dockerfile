# syntax=docker/dockerfile:1
FROM python:3.9

# Ensure Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /python-docker

# Install system dependencies required for Playwright to run headless browsers
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (using the Python module to ensure proper path resolution)
RUN python -m playwright install
RUN python -m tf-playwright-stealth install

# Pre-download NLTK corpora and SpaCy English model for production readiness
RUN python -c "import nltk; nltk.download('popular', quiet=True)" && \
    python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY . .

# Expose the desired port
EXPOSE 11434

# (Optional) Create and switch to a non-root user for improved security in production
RUN useradd -m appuser && chown -R appuser /python-docker
USER appuser

# Start the Quart app with Hypercorn
CMD ["hypercorn", "--bind", "0.0.0.0:11434", "api:app"]
