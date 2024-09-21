# syntax=docker/dockerfile:1
FROM python:3.9
WORKDIR /python-docker
EXPOSE 11434
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
RUN mkdir -p /python-docker/chroma
ENV CHROMADB_CACHE_DIR=/python-docker/chroma
CMD [ "python3", "api.py" ]
