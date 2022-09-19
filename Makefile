#!make
include envfile
export $(shell sed 's/=.*//' envfile)
# Define make entry and help functionality
.DEFAULT_GOAL := help

.PHONY: help

REPO_NAME := authentic-credential-segmenter-endpoints-cdk
SHA1 := $$(git log -1 --pretty=%h)
GIT_HASH := $$(git log -1 --pretty=%h)
CURRENT_BRANCH := $$(git symbolic-ref -q --short HEAD)
LATEST_TAG := ${REPO_NAME}:latest
GIT_TAG := ${REPO_NAME}:${SHA1}
VERSION := 0.1.0
CODEBUILD_RESOLVED_SOURCE_VERSION ?= latest

lint: isort ## lint
	@poetry run black . --exclude "cdk.out|.venv|node_modules"
#	@poetry run yamllint .

isort:  ## Run isort against the project.
	@poetry run isort --profile black . --skip cdk.out --skip .venv --skip node_modules


safety: ## Run the Python Safety dependency checker. we are not yet licensed
	@echo "Running Safety check..."
	@poetry export -f requirements.txt --dev --output requirements-dev.txt && cat requirements-dev.txt | safety check
	@poetry export -f requirements.txt --output requirements.txt && cat requirements.txt | safety check
	@poetry run safety check
	@echo "Safety check completed!"
