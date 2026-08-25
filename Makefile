.PHONY: help setup verify test-boot bundles console demo test clean

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

help: ## Show this help message
	@echo "Orbital OTA Bench - Makefile Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Set up Python environment and install tools
	@echo "Setting up virtual environment and dependencies..."
	brew install cue qemu-system-arm || true
	uv venv .venv --python 3.11 --clear
	.venv/bin/pip install -r requirements.txt
	.venv/bin/playwright install chromium

verify: ## Run full test suite including QEMU and Playwright E2E
	@echo "Running verification tests..."
	$(PYTEST) -v tests/

test: ## Run offline unit tests
	$(PYTEST) -v -k "not qemu and not e2e" tests/

test-boot: ## Boot the dual-slot target in QEMU
	@echo "Booting dual-slot QEMU target..."
	$(PYTHON) -m target.boot_control --run-qemu

bundles: ## Validate and build all CUE bundles
	@echo "Validating CUE bundles..."
	cue vet bundles/schema.cue bundles/missions/*.cue

console: ## Serve the FastAPI/web UI operator console
	@echo "Launching operator console..."
	$(PYTHON) -m console.server

demo: ## Run the 3-minute scripted demo scenario
	@echo "Running demo scenario..."
	$(PYTHON) -m chaos.demo

clean: ## Clean built artifacts and virtualenv
	rm -rf .venv build/ dist/ out/
	find . -type d -name "__pycache__" -exec rm -rf {} +
