# ============================================================
# Dockerfile — builds the calculator container image
# ============================================================
# A Dockerfile is a recipe that Docker executes top-to-bottom to
# produce an immutable image. Each instruction creates a new "layer".
# Docker caches layers, so unchanged layers are reused on rebuilds —
# this is why dependencies are installed BEFORE copying app code.
#
# Build:  docker build -t calculator:latest .
# Run:    docker run -p 8080:8080 calculator:latest
# ============================================================

# ---------------------------------------------------------------
# Stage: base image
# ---------------------------------------------------------------
# FROM selects the starting image from Docker Hub.
# python:3.12-slim is the official Python image built on Debian,
# with non-essential packages removed to keep the image small.
# Always pin a specific version (not "latest") for reproducible builds.
FROM python:3.12-slim

# ---------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------
# WORKDIR sets the directory for all subsequent instructions.
# If it doesn't exist, Docker creates it.
# Using /app is a common convention for application code.
WORKDIR /app

# ---------------------------------------------------------------
# Install dependencies (cached layer)
# ---------------------------------------------------------------
# Copy requirements FIRST, before the app code.
# Reason: Docker re-runs a layer only when its inputs change.
# requirements.txt changes rarely; app code changes often.
# By copying requirements first, Docker reuses the pip install
# layer on every code-only change — much faster rebuilds.
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir tells pip not to store downloaded packages locally,
# keeping the image size smaller.

# ---------------------------------------------------------------
# Copy application code
# ---------------------------------------------------------------
# Copy everything from the app/ directory into the container's /app.
# This layer re-runs whenever any source file changes.
COPY app/ .

# ---------------------------------------------------------------
# Runtime user (security best practice)
# ---------------------------------------------------------------
# By default containers run as root, which is a security risk —
# if an attacker escapes the container they get root on the host.
# Creating a non-root user and switching to it limits the blast radius.
RUN useradd --no-create-home appuser
USER appuser

# ---------------------------------------------------------------
# Expose port
# ---------------------------------------------------------------
# EXPOSE documents which port the container listens on.
# It does NOT actually open the port — that's done at runtime with -p.
# Tools like Docker Compose and Kubernetes use this as metadata.
EXPOSE 8080

# ---------------------------------------------------------------
# Start command
# ---------------------------------------------------------------
# CMD is the default command run when the container starts.
# Using the JSON array form (exec form) is preferred — it runs the
# process directly without a shell wrapper, so signals (SIGTERM)
# reach the process correctly (important for graceful shutdown).
#
# gunicorn flags:
#   --workers 2     — 2 worker processes (rule of thumb: 2×CPU + 1)
#   --bind 0.0.0.0  — listen on all interfaces inside the container
#   :8080           — port to bind
#   app:app         — module:variable (app.py → app Flask instance)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "app:app"]
