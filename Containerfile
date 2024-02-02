# syntax=docker/dockerfile:1

# build stage
FROM docker.io/python:3.11-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /project/
COPY minio_manager/ /project/minio_manager

# install dependencies and project into the local packages directory
WORKDIR /project
ENV PDM_BUILD_SCM_VERSION=0.1.0-beta
RUN mkdir __pypackages__ && pdm sync --prod --no-editable


# run stage
FROM docker.io/python:3.11-alpine

# install bash
RUN apk add --no-cache bash

# retrieve packages from build stage
ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/3.11/lib /project/pkgs

# retrieve executables
COPY --from=builder /project/__pypackages__/3.11/bin/* /bin/

USER 1001

# set command/entrypoint, adapt to fit your needs
CMD [ "minio-manager" ]
