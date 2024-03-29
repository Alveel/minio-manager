# syntax=docker/dockerfile:1

# build stage
FROM docker.io/python:3.11-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY README.md pyproject.toml pdm.lock /project/
COPY minio_manager/ /project/minio_manager

# install dependencies and project into the local packages directory
WORKDIR /project
ARG GIT_TAG
ENV PDM_BUILD_SCM_VERSION=$GIT_TAG
RUN mkdir __pypackages__ && pdm sync --prod --no-editable

# run stage
FROM docker.io/python:3.11-alpine

# install bash
RUN apk add --no-cache bash

# install minio client
ADD https://dl.min.io/client/mc/release/linux-amd64/mc /usr/local/bin/mc
RUN chmod +x /usr/local/bin/mc && mkdir .mc && chown 1001 .mc

# retrieve packages from build stage
ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/README.md /project/pyproject.toml /project/pdm.lock /project/
COPY --from=builder /project/__pypackages__/3.11/lib /project/pkgs

# retrieve executables
COPY --from=builder /project/__pypackages__/3.11/bin/* /usr/local/bin/

USER 1001

# command/entrypoint is project cmd, can be overridden in e.g. CD pipeline
CMD [ "minio-manager" ]
