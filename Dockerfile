# syntax=docker/dockerfile:1

FROM registry.access.redhat.com/ubi9/python-311@sha256:8a067206cbdbf73a39261f11c028a6fa55369d44b6c08f3d5f4d5194bfad69a5

# Set work directory
WORKDIR /code

# Install PDM
RUN pip install pdm

# Copy only requirements to cache them in docker layer
COPY pdm.lock pyproject.toml /code/

# Project initialization:
RUN pdm install --no-self

# Copy Python code to the Docker image
COPY minio_manager/ /code/minio_manager//

CMD [ "python", "minio_manager"]
