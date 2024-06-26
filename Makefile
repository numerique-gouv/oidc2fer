# /!\ /!\ /!\ /!\ /!\ /!\ /!\ DISCLAIMER /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# This Makefile is only meant to be used for DEVELOPMENT purpose as we are
# changing the user id that will run in the container.
#
# PLEASE DO NOT USE IT FOR YOUR CI/PRODUCTION/WHATEVER...
#
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# Note to developers:
#
# While editing this file, please respect the following statements:
#
# 1. Every variable should be defined in the ad hoc VARIABLES section with a
#    relevant subsection
# 2. Every new rule should be defined in the ad hoc RULES section with a
#    relevant subsection depending on the targeted service
# 3. Rules should be sorted alphabetically within their section
# 4. When a rule has multiple dependencies, you should:
#    - duplicate the rule name to add the help string (if required)
#    - write one dependency per line to increase readability and diffs
# 5. .PHONY rule statement should be written after the corresponding rule
# ==============================================================================
# VARIABLES

BOLD := \033[1m
RESET := \033[0m
GREEN := \033[1;32m


# -- Docker
# Get the current user ID to use for docker run and docker exec commands
DOCKER_UID          = $(shell id -u)
DOCKER_GID          = $(shell id -g)
DOCKER_USER         = $(DOCKER_UID):$(DOCKER_GID)
COMPOSE             = DOCKER_USER=$(DOCKER_USER) docker compose
COMPOSE_EXEC        = $(COMPOSE) exec
COMPOSE_EXEC_APP    = $(COMPOSE_EXEC) app-dev
COMPOSE_RUN         = $(COMPOSE) run --rm
COMPOSE_RUN_APP     = $(COMPOSE_RUN) app-dev

# ==============================================================================
# RULES

default: help

# -- Project

create-dev-certs: ## Create self-signed HTTPS certificates for development
create-dev-certs:
	rm -rf env.d/development/certs
	mkdir -p env.d/development/certs
	cp "$$(mkcert --CAROOT)/rootCA.pem" env.d/development/certs/mkcert-root-ca.pem
	mkcert -key-file env.d/development/certs/key.pem -cert-file env.d/development/certs/cert.pem *.traefik.me
.PHONY: create-dev-certs

create-env-files: ## Copy the dist env files to env files
create-env-files: \
	env.d/development/common \
	env.d/development/satosa
.PHONY: create-env-files

bootstrap: ## Prepare Docker images for the project
bootstrap: \
	create-dev-certs \
	create-env-files \
	build \
	run
.PHONY: bootstrap

# -- Docker/compose
build: ## build the app-dev container
	@$(COMPOSE) build app-dev
.PHONY: build

down: ## stop and remove containers, networks, images, and volumes
	@$(COMPOSE) down
.PHONY: down

logs: ## display app-dev logs (follow mode)
	@$(COMPOSE) logs -f app-dev
.PHONY: logs

run: ## start the development servers
	@$(COMPOSE) up --force-recreate --wait -d nginx app-dev oidc-test-client
.PHONY: run

status: ## an alias for "docker compose ps"
	@$(COMPOSE) ps
.PHONY: status

stop: ## stop the development server using Docker
	@$(COMPOSE) stop
.PHONY: stop

# -- Backend

# Nota bene: Black should come after isort just in case they don't agree...
lint: ## lint back-end python sources
lint: \
  lint-ruff-format \
  lint-ruff-check \
  lint-pylint
.PHONY: lint

lint-ruff-format: ## format back-end python sources with ruff
	@echo 'lint:ruff-format started…'
	@$(COMPOSE_RUN_APP) ruff format .
.PHONY: lint-ruff-format

lint-ruff-check: ## lint back-end python sources with ruff
	@echo 'lint:ruff-check started…'
	@$(COMPOSE_RUN_APP) ruff check . --fix
.PHONY: lint-ruff-check

lint-pylint: ## lint back-end python sources with pylint only on changed files from main
	@echo 'lint:pylint started…'
	bin/pylint --diff-only=origin/main
.PHONY: lint-pylint

test: run ## run project tests
	@$(MAKE) test-back
.PHONY: test

test-back: ## run back-end tests
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	bin/pytest $${args:-${1}}
.PHONY: test-back

oidc-test: ## open OIDC test client in browser
	@$(MAKE) down
	@$(MAKE) run
	python -mwebbrowser -n https://oidc-test-client.traefik.me
.phony: oidc-test

e2e-test: ## automated end-to-end test in browser
	@$(MAKE) down
	@$(MAKE) run
	TEST_E2E=1 pytest
.phony: e2e-test

env.d/development/common:
	cp -n env.d/development/common.dist env.d/development/common

env.d/development/satosa:
	openssl req -quiet -batch -x509 -nodes -days 3650 -newkey rsa:2048 \
	  -subj "/CN=satosa.traefik.me" -out - -keyout - \
	  | awk '/BEGIN PRIVATE/,/END PRIVATE/{privkey=privkey $$0 "\n"} \
	         /BEGIN CERTIFICATE/,/END CERTIFICATE/{cert=cert $$0 "\n"} \
	         END { \
	           printf "SAML2_BACKEND_KEY=\"%s\"\n", privkey; \
	           printf "SAML2_BACKEND_CERT=\"%s\"\n", cert; \
	         }' > $@
	echo "OIDC_FRONTEND_KEY=\"$$(openssl genrsa 2048)\"" >> $@
	echo "STATE_ENCRYPTION_KEY=$$(openssl rand -hex 32)" >> $@

# -- Misc
clean: ## restore repository state as it was freshly cloned
	git clean -idx
.PHONY: clean

help:
	@echo "$(BOLD)OIDC2FER Makefile"
	@echo "Please use 'make $(BOLD)target$(RESET)' where $(BOLD)target$(RESET) is one of:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(RESET) %s\n", $$1, $$2}'
.PHONY: help
