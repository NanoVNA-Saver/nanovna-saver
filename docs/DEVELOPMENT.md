# Development Process

## Local Development Environment

Prerequerements:

1. Python > 3.10. Using [pyenv](https://github.com/pyenv/pyenv) / [pyenv-win](https://github.com/pyenv-win/pyenv-win) may be requered to test comaptibility with different python versions.
2. [Poetry v1.8.x](https://python-poetry.org/docs/1.8/#installation). May be installed via [pipx](https://pipx.pypa.io/latest/installation/).
3. Poetry plugins:
    3.1. [poetry-dynamic-versioning](https://github.com/mtkennerly/poetry-dynamic-versioning) (`poetry self add "poetry-dynamic-versioning[plugin]"`)
    3.2. [poethepoet](https://github.com/nat-n/poethepoet) (`poetry self add "poethepoet[plugin]"`)
    3.3. (optional) [poetry-plugin-up](https://github.com/MousaZeidBaker/poetry-plugin-up) (`poetry self add poetry-plugin-up`)

## Local Run and Debugging

Following commands to prepare local env and run application or run tests:

* `poetry install` - prepare virtual environment and install prod and dev dependencies
* `poetry run NanoVNASaver` - run local instance
* 🚧 TODO: testing and cleaning tasks
 
## Development Routines

A few usefull commands:

* `poetry up` - update dependencies in `pyproject.toml` respecting specified version constraints.
* `poetry up --latest` - update dependencies ignoring in `pyproject.toml` specified version constraints.
* `poetry update` - update dependency lock file respecting specified version constraints.

## Build Process

A `poetry build` may be used to prepare python packages. Version would be taken from git repository.

🚧 TODO: build platform specific artefacts: deb, native bin, flatpack packages

## Publish Process

Please configure pypi credentials, create git tag and execute `poetry publlish` command. Please refer [Poetry :: publish](https://python-poetry.org/docs/1.8/cli/#publish) for more details.

🚧 TODO: describe git tag creation and next version selection
🚧 TODO: build and publish platform specific artefacts: deb, native bin, flatpack packages