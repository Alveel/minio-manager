# minio-manager

[![Release](https://img.shields.io/github/v/release/Alveel/minio-manager?include_prereleases)](https://img.shields.io/github/v/release/Alveel/minio-manager?include_prereleases)
[![Build status](https://img.shields.io/github/actions/workflow/status/Alveel/minio-manager/main.yaml)](https://github.com/alveel/minio-manager/actions/workflows/main.yml?query=branch%3Amain)
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

To quickly configure a local development MinIO, you can run

```shell
make run-test-environment
```
**Note**: requires [Podman](https://podman.io/)!

Copy `.env.example` to `.env` and optionally modify to your liking.

Now you can use debug tools in your IDE to run the Python code.
Configure your debugger to run the Python module `minio_manager` with the environment variables from `.env`.
A sample debugger configuration for Visual Studio Code is configured in `.vscode/launch.json` and should be directly available from "Run and Debug".

Find local MinIO installation on http://localhost:9000.

When you are finished, run

```shell
make stop-test-environment
```

**Note** that the created `secrets-insecure.yaml` will not be removed automatically and will get overwritten by the setup command.

To finalize the set-up for publishing to PyPi or Artifactory, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-pdm/features/codecov/).

## To do features

Check the open [enhancement](https://github.com/Alveel/minio-manager/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) issues.

---

Repository initiated with [fpgmaas/cookiecutter-pdm](https://github.com/fpgmaas/cookiecutter-pdm).
