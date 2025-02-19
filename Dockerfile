FROM apache/airflow:2.7.1-python3.8

USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements file
COPY --chown=airflow:root requirements.txt /opt/airflow/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt