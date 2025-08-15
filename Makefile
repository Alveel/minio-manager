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

start-local-test: ## Start local MinIO test environment
	@echo "🚀 Running local test environment"
	@echo "🧹 Stopping any existing MinIO test container..."
	@podman stop minio-local-test 2>/dev/null || true
	@podman rm minio-local-test 2>/dev/null || true
	@podman run --detach --name minio-local-test --rm -p 9000:9000 -p 9001:9001 \
		quay.io/minio/minio server /data --console-address ":9001"
	@echo "😴 Waiting for MinIO to start..."
	@sleep 4
	@echo "🪛 Configuring 'mc' alias 'local-test-admin'"
	@mc alias set local-test-admin http://localhost:9000 minioadmin minioadmin

configure-admin: ## Configure mc alias for admin access
	@echo "🪛 Configuring 'mc' alias 'minio-admin'"
	@mc alias set minio-admin http://localhost:9000 minioadmin minioadmin

configure-controller: ## Setup the minio-manager controller user and service account
	@echo "� Creating test-controller-policy"
	@mc admin policy create local-test-admin test-controller-policy examples/controller_policies/test-controller-policy.json || echo "Policy may already exist"

	@echo "�👷 Creating user 'local-test-controller'"
	@mc admin user add local-test-admin local-test-controller insecure-password-for-testing || echo "User may already exist"

	@echo "🚧 Ensuring test-controller-policy is attached to user 'local-test-controller'"
	@mc admin policy attach local-test-admin test-controller-policy --user=local-test-controller || echo "Policy may already be attached"

	@echo "🪛 Configuring 'mc' alias 'local-test-controller'"
	@mc alias set local-test-controller http://localhost:9000 local-test-controller insecure-password-for-testing

	@echo "🤖 Creating service account for 'local-test-controller' user with static credentials"
	@mc admin user svcacct remove local-test-admin static-for-testing 2>/dev/null || echo "Service account doesn't exist yet"
	@mc admin user svcacct add local-test-admin local-test-controller \
		--name "MinIO Manager Test Controller" \
		--access-key static-for-testing \
		--secret-key static-secret-key-for-testing

	@echo "✅ Controller service account setup completed!"
	@echo "   User: local-test-controller (with test-controller-policy)"
	@echo "   Service Account Access Key: static-for-testing"
	@echo "   Service Account Secret Key: static-secret-key-for-testing"

run-test-environment: start-local-test configure-admin configure-controller ## Run the test environment
	cp examples/my_group/secrets-insecure.yaml .

stop-test-environment: ## Stop the running test environment
	@echo "🛑 Stopping MinIO test environment..."
	@podman stop minio-local-test 2>/dev/null || true
	@podman rm minio-local-test 2>/dev/null || true

.PHONY: test
test: ## Run tests without MinIO (only utility and basic tests)
	@echo "🧪 Running tests (MinIO tests will be skipped)"
	@pdm run pytest tests/ -v --tb=short

.PHONY: test-unit
test-unit: ## Run only unit tests that don't require MinIO
	@echo "🧪 Running unit tests (no MinIO required)"
	@pdm run pytest tests/test_basic.py tests/test_utilities.py -v

.PHONY: test-integration
test-integration: ## Run integration tests (requires MinIO test environment)
	@echo "🧪 Running integration tests (requires MinIO test environment)"
	@echo "💡 Make sure to run 'make run-test-environment' first"
	@pdm run pytest tests/test_bucket_creation.py tests/test_lifecycle_policies.py tests/test_bucket_policies.py tests/test_integration.py -v

.PHONY: test-all
test-all: ## Run all tests including integration tests (requires MinIO test environment)
	@echo "🧪 Running all tests (requires MinIO test environment)"
	@echo "💡 Make sure to run 'make run-test-environment' first"
	@pdm run pytest tests/ -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage"
	@pdm run pytest tests/ --cov=minio_manager --cov-report=html --cov-report=term-missing

.PHONY: test-full
test-full: run-test-environment test-all stop-test-environment ## Start test environment, run all tests, then stop environment
	@echo "✅ Full test cycle completed"

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@pdm build

clean-build: ## Clean build artifacts
	@rm -rf dist

.PHONY: publish
publish: ## Publish a release to PyPi
	@echo "🚀 Publishing."
	@pdm publish --username __token__ --password $PYPI_TOKEN

build-and-publish: build publish ## Build and publish.

docs-test: ## Test if documentation can be built without warnings or errors
	@pdm run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@pdm run mkdocs serve

build-image: ## Build the container image using the latest git tag
	@podman build -t minio-manager:$(GIT_TAG) --build-arg GIT_TAG=$(GIT_TAG) .

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
