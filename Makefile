THIS_FILE := $(lastword $(MAKEFILE_LIST))

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
	# @echo "🚀 Checking for obsolete dependencies: Running deptry"
	# @pdm run deptry .

.PHONY: run-test-environment
run-test-environment:
	@echo "🚀 Running local test environment"
	@podman run --detach --name minio-local-test --rm -p 9000:9000 -p 9001:9001 \
		quay.io/minio/minio server /data --console-address ":9001"

.PHONY: stop-test-environment
stop-test-environment:
	@podman stop --ignore minio-local-test

.PHONY: test
test: ## Test the code with pytest
	@$(MAKE) -f $(THIS_FILE) stop-test-environment
	@$(MAKE) -f $(THIS_FILE) run-test-environment
	@echo "🚀 Testing code: Running pytest"
	@pdm run pytest --cov --cov-config=pyproject.toml --cov-report=xml --import-mode=importlib
	@$(MAKE) -f $(THIS_FILE) stop-test-environment

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@pdm build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@rm -rf dist

.PHONY: publish
publish: ## publish a release to pypi.
	@echo "🚀 Publishing."
	@pdm publish --username __token__ --password $PYPI_TOKEN


.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@pdm run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@pdm run mkdocs serve

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
