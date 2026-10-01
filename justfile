# List available recipes.
default:
    @just --list

# Install the project and its dev dependency group into .venv.
install-dev:
    uv sync

# Lint and check formatting.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Run the test suite. Extra arguments are passed through to pytest.
test *args:
    uv run pytest {{args}}

# Lint plus the full suite: the gate to run before pushing.
ci: lint test

# Run the CLI from the checkout, e.g. `just cli build examples/report --format html`.
cli +args:
    uv run ginja {{args}}

# Build the one-file letter example (HTML and PDF).
example-letter:
    uv run ginja build examples/letter/letter.md

# Build the multi-file report example (HTML and PDF).
example-report:
    uv run ginja build examples/report

# Build one CV variant, e.g. `just example-cv ai-consulting de`.
example-cv profile="data-science" locale="en":
    uv run ginja build examples/curriculum-vitae --profile {{profile}} --locale {{locale}}

# Build every CV variant: 3 profiles x 2 locales, as repeated engine invocations.
example-cv-all:
    #!/usr/bin/env bash
    set -euo pipefail
    for profile in ai-consulting data-science data-analytics; do
        for locale in en de; do
            uv run ginja build examples/curriculum-vitae --profile "$profile" --locale "$locale"
        done
    done

# Delete the examples' generated files.
clean:
    rm -rf examples/*/build
