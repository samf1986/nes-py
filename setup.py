"""The setup script for installing and distributing the nes-py package."""
import os
from glob import glob
from typing import List

import pybind11
from setuptools import setup
from setuptools import find_packages
from pybind11.setup_helpers import Pybind11Extension


def read_readme() -> str:
    """Read the README.md file and return its content."""
    with open('README.md') as f:
        return f.read()


def get_source_files() -> List[str]:
    """Get all C++ source files needed for compilation."""
    return (
        glob('nes_py/nes/src/*.cpp') + 
        glob('nes_py/nes/src/mappers/*.cpp')
    )


def configure_compiler() -> None:
    """Configure the C++ compiler settings."""
    os.environ['CC'] = 'g++'
    os.environ['CCX'] = 'g++'


def get_extension_modules() -> List[Pybind11Extension]:
    """Create and return the extension modules configuration."""
    # Get all source files
    sources = get_source_files()  # This already includes all .cpp files
    
    return [
        Pybind11Extension(
            'nes_py.lib_emu',
            sources,  # Include all source files
            include_dirs=[
                'nes_py/nes/include',
                'nes_py/nes/src',
                pybind11.get_include(),
                pybind11.get_include(user=True)
            ],
            cxx_std=11,
        ),
    ]

def get_requirements() -> List[str]:
    """Get the requirements for the package."""
    with open('requirements.txt') as f:
        return list(map(str.strip, f.read().splitlines()))


def main() -> None:
    """Main setup configuration."""
    configure_compiler()
    
    setup(
        name='nes_py',
        version='9.0.0',
        description='An NES Emulator and OpenAI Gym interface',
        long_description=read_readme(),
        long_description_content_type='text/markdown',
        keywords='NES Emulator OpenAI-Gym',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: POSIX :: Linux',
            'Operating System :: Microsoft :: Windows',
            'Programming Language :: C++',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Topic :: Games/Entertainment',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Emulators',
        ],
        url='https://github.com/Kautenja/nes-py',
        author='Christian Kauten',
        author_email='kautencreations@gmail.com',
        license='MIT',
        packages=find_packages(exclude=['tests', '*.tests', '*.tests.*']),
        ext_modules=get_extension_modules(),
        zip_safe=False,
        install_requires=get_requirements(),
        extras_require={
            'dev': [
                'pytest>=7.0.0',
                'pytest-cov>=4.0.0',
                'black>=23.0.0',
                'mypy>=1.0.0',
            ],
        },
        entry_points={
            'console_scripts': [
                'nes_py=nes_py.app.cli:main',
            ],
        },
        python_requires='>=3.8',
    )


if __name__ == '__main__':
    main()
