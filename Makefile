.PHONY: install live-install verify data lab test solutions ollama-pull clean chat eval data-check
VENV ?= .venv
PY ?= $(shell if [ -x "$(VENV)/bin/python" ]; then echo "$(VENV)/bin/python"; else command -v python 2>/dev/null || command -v python3; fi)
JUPYTER ?= $(shell if [ -x "$(VENV)/bin/jupyter" ]; then echo "$(VENV)/bin/jupyter"; else command -v jupyter; fi)

install:        ## one-command install (uv-first, Python 3.11; scripted floor works for everyone)
	bash install.sh

live-install:   ## add the live LLM SDKs (opt-in; needed for a key/Ollama-backed agent)
	@if command -v uv >/dev/null 2>&1; then \
		uv sync --locked --extra notebooks --extra dev --extra openai --extra gemini --extra ollama; \
	else \
		echo "uv not found; installing live SDKs with pip"; \
		$(PY) -m pip install -r requirements-live.txt; \
		$(PY) -m pip install -e . --no-deps; \
	fi

verify:         ## run the preflight check
	$(PY) -m healthagent.verify

chat:           ## chat with the agent over the dataset (ha-chat); use Q="..." for one-shot
	$(PY) -m healthagent.cli.chat $(if $(Q),--question "$(Q)",)

eval:           ## red-team probe scorecard across backends (PROVIDERS=scripted,openai,...)
	$(PY) -m healthagent.cli.eval $(if $(PROVIDERS),--providers $(PROVIDERS),)

data-check:     ## validate a dataset against the codebook (BYOD; honors HA_DATA_DIR)
	$(PY) -m healthagent.cli.datacheck $(if $(TABLES),--tables $(TABLES),)

data:           ## (re)generate the committed synthetic dataset
	$(PY) data/generate_dataset.py

lab:            ## launch JupyterLab on the notebooks
	$(JUPYTER) lab notebooks/

test:           ## run the offline-core test suite (provider-contract tests need the live extras)
	$(PY) -m pytest -q -p no:warnings -m "not provider_contract"

solutions:      ## copy reference solutions over the workshop stubs (instructor rescue)
	cp ha_workshop/solutions/student_tools.py ha_workshop/student_tools.py
	cp ha_workshop/solutions/agent_config.py ha_workshop/agent_config.py
	@echo "Solutions copied into ha_workshop/. Revert with: git checkout ha_workshop/"

ollama-pull:    ## pull the recommended local model (do this on home wifi)
	ollama pull llama3.1:8b

clean:
	rm -rf cache .pytest_cache **/__pycache__
