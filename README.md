# minio-manager

[![Release](https://img.shields.io/github/v/release/alveel/minio-manager)](https://img.shields.io/github/v/release/alveel/minio-manager)
[![Build status](https://img.shields.io/github/actions/workflow/status/alveel/minio-manager/main.yml?branch=main)](https://github.com/alveel/minio-manager/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)
[![License](https://img.shields.io/github/license/alveel/minio-manager)](https://img.shields.io/github/license/alveel/minio-manager)

Declare what MinIO buckets, IAM policies, ILM policies you want, and let MinIO Manager do the work.

- **GitHub repository**: <https://github.com/alveel/minio-manager/>
- **Documentation** <https://alveel.github.io/minio-manager/>

## Description

The concept for management is to have so-called "bucket groups".

Each bucket group is managed by an account that only has access to buckets in that group.

It should be noted that this is explicitly intended for the _creation and updating of resources in MinIO_. It does _not_
delete any resources anywhere.

## Requirements

- [Python](https://www.python.org/) (3.9 or newer)
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

## Set up

An admin user should be used for these steps.

1. Create the bucket for the secret backend `minio-manager-secrets`

    `mc mb $ALIAS/minio-manager-secrets`
1. Create a user (either in MinIO or your identity provider)

    You can use `mc admin user add $ALIAS minio-manager` for a MinIO user
1. Create a policy that gives read/write access to the bucket for the secret backend

    You can use the example provided in the `examples` directory:

    `mc admin policy create $ALIAS minio-manager examples/minio-manager-secrets-policy.json`
1. Attach the policy to the user:

   - For MinIO: `mc admin policy attach $ALIAS minio-manager --user=minio-manager`
   - For LDAP: `mc idp ldap policy attach $ALIAS minio-manager --user='uid=minio-manager,cn=users,dc=your,dc=domain'`
1. Upload your secret backend (e.g. `secrets.kdbx`) to the bucket root
1. Create a MinIO service account/access key with either option:

   - `mc admin user svcacct add $ALIAS minio-manager` and note down the access and secret keys
1. Copy `.env.example` to `.env` and set the following variables to the obtained keys

   - `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY`
   - `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY`
1. Configure the other variables in the `.env` file. Descriptions of each variable can be found in the
   [Environment variables](#environment-variables) section
1. Each "bucket group" manager user must get its own policy.
   1. You can find an example in `examples/bucket-group-user-policy.json`
   1. `mc admin policy create $ALIAS infra-test-manager examples/bucket-group-user-policy.json`
   1. `mc idp ldap policy attach $ALIAS infra-test-manager --user='uid=infra-test-manager,cn=users,dc=your,dc=domain'`
1. You can then log in to the web console with this user to create an access key exactly like how we did it previously

### MinIO

At least two users are required in MinIO. One with access to a single bucket containing the secret backend, all other
users are to be used as "bucket group" managers. For each bucket created under this manager user a service account
(or access key in S3/MinIO terms) will be created.

#### Secret backend

### Keepass

The Keepass database's root group must be named "Passwords".

You must have a group called "s3" and subgroups with the name of each MinIO cluster.

Entry names must be unique.

Entries are found by way of the title of the entry, the username is not considered when searching.

## Environment variables

### Required

- `MINIO_MANAGER_CLUSTER_NAME` The name of the cluster, used for example in the secret backend
- `MINIO_MANAGER_MINIO_ENDPOINT` What host:port to use as MinIO/S3 endpoint
- `MINIO_MANAGER_MINIO_CONTROLLER_USER` The entry of the MinIO controller user in the secret backend that contains its access and secret keys
- `MINIO_MANAGER_CLUSTER_RESOURCES_FILE` The YAML file with the MinIO resource configuration (buckets, policies, etc.)
- `MINIO_MANAGER_SECRET_BACKEND_TYPE` What secret backend to use. Currently only keepass is supported
- `MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY` The access key to the S3 bucket where the secret database is stored
- `MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY` The secret key to the S3 bucket where the secret database is stored
- `MINIO_MANAGER_KEEPASS_PASSWORD` Keepass database password

### Optional

- `MINIO_MANAGER_MINIO_ENDPOINT_SECURE` Whether to use HTTPS for the endpoint. Defaults to `True`
- `MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET` The name of the bucket where the secret backend is kept. Defaults to `minio-manager-secrets`
- `MINIO_MANAGER_KEEPASS_FILE` The name of the database file in the S3 bucket. Defaults to `secrets.kdbx`
- `MINIO_MANAGER_KEEPASS_GENERATE_MISSING` Whether to automatically create missing entries in Keepass. Defaults to False
- `MINIO_MANAGER_LOG_LEVEL` The log level of the application. Defaults to `INFO`, may also use `DEBUG`

## To do features

- Disable bucket versioning if explicitly disabled. Currently, you can only enable it.
- Check if policies are already attached to a user before running the "attach" command.
- Automatically configure a service account with each bucket instead of separately specifying the bucket and service account.
- Automatically generate keepass database when it is configured as the secret backend while not present in the bucket.
- Also sort policy Principals to prevent unnecessary policy updates.
- Re-use ServiceAccount object instead of MinioCredentials object which is effectively the same.
- Allow cleaning up of removed resources, e.g. service account that doesn't have a related bucket.
- Improve logging not to show stack trace when log level is not DEBUG.
- Create container image of project
- Add colours to different log levels.

---

Repository initiated with [fpgmaas/cookiecutter-pdm](https://github.com/fpgmaas/cookiecutter-pdm).
