# minio-manager

[![Release](https://img.shields.io/github/v/release/alveel/minio-manager)](https://img.shields.io/github/v/release/alveel/minio-manager)
[![Build status](https://img.shields.io/github/actions/workflow/status/alveel/minio-manager/main.yml?branch=main)](https://github.com/alveel/minio-manager/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/alveel/minio-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/alveel/minio-manager)
[![Commit activity](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)
[![License](https://img.shields.io/github/license/alveel/minio-manager)](https://img.shields.io/github/license/alveel/minio-manager)

Declare what MinIO buckets, IAM policies, ILM policies you want, and let MinIO Manager do the work.

- **GitHub repository**: <https://github.com/alveel/minio-manager/>
- **Documentation** <https://alveel.github.io/minio-manager/>

## Description

The concept for management is to have so-called "bucket groups".

Each bucket group is managed by an account that only has access to buckets in that group.

This application authenticates to multiple accounts.

For illustration:

```
├── user1
│  └─ sa-user1-bucketgroup
│    ├─── sa-user1-bucketABC
│    │   └── bucketABC
│    └─── sa-user1-bucketXYZ
│        └── bucketXYZ
└── user2
   └─ sa-user2-bucketgroup
     ├── sa-user2-bucketDEF
     │  └── bucketDEF
     └── sa-user2-bucketUWV
        └── bucketUWV
```

## Requirements

- [Python](https://www.python.org/) (3.8.1 or newer)
- [PDM](https://pdm-project.org/)

## Getting started with your project

Install the environment and the pre-commit hooks with

```bash
make install
```

You are now ready to start development on your project! The CI/CD
pipeline will be triggered when you open a pull request, merge to main,
or when you create a new release.

To finalize the set-up for publishing to PyPi or Artifactory, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-pdm/features/codecov/).

## Releasing a new version

## Configuration

### MinIO

Unfortunately, not everything can be automated (unless you use the superuser for everything, which you probably don't.)

#### Secret backend

A user and bucket must be configured where the secret backend will be stored.

Using the default bucket name as an example, the following minimal IAM policy must be created:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
              "s3:GetBucketLocation",
              "s3:GetBucketVersioning",
              "s3:GetObject",
              "s3:GetObjectRetention",
              "s3:GetObjectVersion",
              "s3:ListAllMyBuckets",
              "s3:ListBucket",
              "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::minio-manager-secrets",
                "arn:aws:s3:::minio-manager-secrets/*"
            ]
        }
    ]
}
```

You can further restrict access by specifying specific files instead of using a wildcard.

### Keepass

The Keepass database's root group must be named "Passwords".

You must have a group called "s3" and subgroups with the name of each MinIO cluster.

Usernames and entry names must be identical.

Entry names must be unique.

### Environment variables

- `MINIO_MANAGER_LOG_LEVEL` The log level of the application. Defaults to `INFO`, may also use `DEBUG`
- `MINIO_MANAGER_MINIO_ENDPOINT` What host:port to use as MinIO/S3 endpoint
- `MINIO_MANAGER_MINIO_ENDPOINT_SECURE` Whether to use HTTPS for the endpoint. Defaults to `True`
- `MINIO_MANAGER_MINIO_CONTROLLER_USER` The entry of the MinIO controller user in the secret backend that contains its access and secret keys
- `MINIO_MANAGER_CONFIG_FILE` The configuration YAML with MinIO cluster information
- `MINIO_MANAGER_SECRET_BACKEND_TYPE` What secret backend to use. Currently only keepass is supported
- `MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET` The name of the bucket where the secret backend is kept. Defaults to `minio-manager-secrets`
- `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY` The access key to the S3 bucket where the secret database is stored
- `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY` The secret key to the S3 bucket where the secret database is stored
- `MINIO_MANAGER_KEEPASS_PASSWORD` Keepass database password
- `MINIO_MANAGER_KEEPASS_FILE` The name of the database file in the S3 bucket. Defaults to `secrets.kdbx`

---

Repository initiated with [fpgmaas/cookiecutter-pdm](https://github.com/fpgmaas/cookiecutter-pdm).
