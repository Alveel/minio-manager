# minio-manager

[![Release](https://img.shields.io/github/v/release/alveel/minio-manager)](https://img.shields.io/github/v/release/alveel/minio-manager)
[![Build status](https://img.shields.io/github/actions/workflow/status/alveel/minio-manager/main.yml?branch=main)](https://github.com/alveel/minio-manager/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/alveel/minio-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/alveel/minio-manager)
[![Commit activity](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)
[![License](https://img.shields.io/github/license/alveel/minio-manager)](https://img.shields.io/github/license/alveel/minio-manager)

Declare what MinIO buckets, IAM policies, ILM policies you want, and let MinIO Manager do the work.

- **Github repository**: <https://github.com/alveel/minio-manager/>
- **Documentation** <https://alveel.github.io/minio-manager/>

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

### Keepass

The Keepass database's root group must be named "Passwords".

You must have a group called "s3" and subgroups with the name of each MinIO cluster.

Usernames and entry names must be identical.

Entry names must be unique.

### Environment variables

- `KEEPASS_PASSWORD`



---

Repository initiated with [fpgmaas/cookiecutter-pdm](https://github.com/fpgmaas/cookiecutter-pdm).
