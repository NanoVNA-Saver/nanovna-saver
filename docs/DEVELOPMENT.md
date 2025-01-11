# Development Process

## Local Development Environment

Prerequerements:

1. Python > 3.10. Using [pyenv](https://github.com/pyenv/pyenv) / [pyenv-win](https://github.com/pyenv-win/pyenv-win) may be requered to test comaptibility with different python versions.
2. [Astral UV v1.8.x](https://docs.astral.sh/uv/). May be installed via [pipx](https://pipx.pypa.io/latest/installation/).

## Local Run and Debugging

Following commands to prepare local env and run application or run tests:

* `uv sync` - prepare virtual environment and install prod and dev dependencies
* `uv run NanoVNASaver` - run local instance
* `uv run task test` - run unit tests in current venv
* `uv run task test-cov` - run unit tests in current venv and display test coverage report
* `uv run task test-full` - run unit tests for all avialable python versions
* `uv run task clean` - remove temporally artifacts (dist, build, *.pyc etc)
 
## Development Routines

A few usefull commands:

* 🚧 TODO: - update dependencies in `pyproject.toml` respecting specified version constraints.
* 🚧 TODO: - update dependencies ignoring in `pyproject.toml` specified version constraints.
* `uv lock` - update dependency lock file respecting specified version constraints.

## Build Process

A `uv build` may be used to prepare python packages. Version would be taken from git repository.

🚧 TODO: build platform specific artefacts: deb, native bin, flatpack packages

## Publish Process

Please configure pypi credentials, create git tag and execute `uv publish` command. Please refer [UV :: publish](https://docs.astral.sh/uv/guides/publish/) for more details.

🚧 TODO: describe git tag creation and next version selection
🚧 TODO: build and publish platform specific artefacts: deb, native bin, flatpack packages