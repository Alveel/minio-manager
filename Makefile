THIS_FILE := $(lastword $(MAKEFILE_LIST))
GIT_TAG := $(shell git for-each-ref --sort=creatordate --format '%(refname)' refs/tags | tail -n 1 | cut -d '/' -f 3)

.PHONY: install
install: ## Install the environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using PDM"
	@pdm install
	@pdm run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking pdm lock file consistency with 'pyproject.toml': Running pdm lock --check"
	@pdm lock --check
	@echo "🚀 Linting code: Running pre-commit"
	@pdm run pre-commit run -a
	# @echo "🚀 Static type checking: Running mypy"
	# @pdm run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@pdm run deptry .

start-local-test:
	@echo "🚀 Running local test environment"
	@podman run --detach --name minio-local-test --rm -p 9000:9000 -p 9001:9001 \
		quay.io/minio/minio server /data --console-address ":9001"
	@echo "😴 Waiting for MinIO to start..."
	@sleep 4
	@echo "🪛 Configuring 'mc' alias 'local-test-admin'"
	@mc alias set local-test-admin http://localhost:9000 minioadmin minioadmin

configure-admin:
	@echo "🪛 Configuring 'mc' alias 'minio-admin'"
	@mc alias set minio-admin http://localhost:9000 minioadmin minioadmin

configure-controller:
	@echo "👷 Creating user 'local-test-controller'"
	@mc admin user add local-test-admin local-test-controller insecure-password-for-testing

	@echo "🚧 Creating user policy for controller user and assigning to user 'local-test-controller'"
	@mc admin policy create local-test-admin local-test-controller-policy examples/bucket-group-user-policy.json
	@mc admin policy attach local-test-admin local-test-controller-policy --user=local-test-controller

	@echo "🪛 Configuring 'mc' alias 'local-test-controller'"
	@mc alias set local-test-controller http://localhost:9000 local-test-controller insecure-password-for-testing

	@echo "🤖 Creating service account for 'local-test-controller' user"
	@mc admin user svcacct add local-test-controller local-test-controller \
		--name "Local Test" \
		--access-key static-for-testing \
		--secret-key static-secret-key-for-testing

setup-test-environment: start-local-test configure-admin configure-controller ## Run the test environment
	cp --update=none examples/my_group/secrets-insecure.yaml . # copy but don't overwrite

stop-test-environment:
	@podman stop minio-local-test

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@pdm build

clean-build: ## clean build artifacts
	@rm -rf dist

.PHONY: publish
publish: ## publish a release to pypi.
	@echo "🚀 Publishing."
	@pdm publish --username __token__ --password $PYPI_TOKEN

build-and-publish: build publish ## Build and publish.

docs-test: ## Test if documentation can be built without warnings or errors
	@pdm run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@pdm run mkdocs serve

build-image:
	@podman build -t minio-manager:$(GIT_TAG) --build-arg GIT_TAG=$(GIT_TAG) .

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
