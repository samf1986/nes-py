PYTHON ?= $(shell which python3)
SCONS ?= $(shell which scons)

# build everything
all: test deployment

# build the LaiNES CPP code
lib_emu:
	$(SCONS) -C nes_py/nes -j $(shell nproc)
	mv nes_py/nes/lib_emu*.so nes_py

install: lib_emu
	$(PYTHON) -m pip install .

# run the Python test suite
test: install
	$(PYTHON) -m unittest discover .

# clean the build directory
clean:
	rm -rf build/ .eggs/ *.egg-info/ || true
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".sconsign.dblite" -delete
	find . -name "build" | rm -rf
	find . -name "lib_emu.so" -delete

# build the deployment package
deployment: clean 
	$(PYTHON) setup.py sdist bdist_wheel

# ship the deployment package to PyPi
ship: test deployment
	twine upload dist/*

# Show configuration
show-config:
	@echo "Python path: $(PYTHON)"
	@echo "SCons command: $(SCONS)"