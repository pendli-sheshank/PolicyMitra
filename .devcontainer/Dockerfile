FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client

WORKDIR /workspaces/PolicyMitra
