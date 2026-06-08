.PHONY: install verify data lab test solutions ollama-pull clean
VENV ?= .venv
PY = $(VENV)/bin/python

install:        ## one-command install (uv-first, Python 3.11)
	bash install.sh

verify:         ## run the preflight check
	$(PY) -m healthagent.verify

data:           ## (re)generate the committed synthetic dataset
	$(PY) data/generate_dataset.py

lab:            ## launch JupyterLab on the notebooks
	$(VENV)/bin/jupyter lab notebooks/

test:           ## run the test suite
	$(PY) -m pytest -q -p no:warnings

solutions:      ## copy reference solutions over the workshop stubs (instructor rescue)
	cp ha_workshop/solutions/student_tools.py ha_workshop/student_tools.py
	cp ha_workshop/solutions/agent_config.py ha_workshop/agent_config.py
	@echo "Solutions copied into ha_workshop/. Revert with: git checkout ha_workshop/"

ollama-pull:    ## pull the recommended local model (do this on home wifi)
	ollama pull llama3.1:8b

clean:
	rm -rf cache .pytest_cache **/__pycache__
