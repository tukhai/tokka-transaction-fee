FROM python:3.10.14-slim-bookworm

### Set environment variables
ENV K8S_DJANGO_SETTINGS_MODULE tokka_txns
ENV PYTHONUNBUFFERED=1

### Install nginx and pip requirements
RUN apt-get -y update && \
    apt-get -y install gcc && \
    apt-get install -y curl build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/* /root/.cache /requirements.txt

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

### Add requirements
ADD requirements.txt .
RUN pip3 install -r requirements.txt

### Set WORKDIR and pack code into images
WORKDIR /app
ADD . /app

EXPOSE 8000
