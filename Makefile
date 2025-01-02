UV ?= $(shell which uv)
PYTHON ?= $(shell which python3)

# build everything
all: test deployment

# build the SimpleNES C++ code
lib_emu:
	$(MAKE) -C nes_py/nes $(MAKEFLAGS)
	mv nes_py/nes/libemulator.so nes_py/emulator.so

install:
	$(UV) pip install .

# run the Python test suite
test: install
	$(PYTHON) -m unittest discover .

# clean the build directory
clean:
	$(MAKE) -C nes_py/nes clean
	rm -rf build/ .eggs/ *.egg-info/ || true
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".sconsign.dblite" -delete
	find . -name "build" | rm -rf
	find . -name "emulator.so" -delete

# build the deployment package
deployment: clean 
	$(UV) build --sdist --wheel

# ship the deployment package to PyPi
ship: test deployment
	twine upload dist/*

# Show configuration
show-config:
	@echo "Python path: $(PYTHON)"
	@echo "UV command: $(UV)"
