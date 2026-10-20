#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

readonly TARGETS=(./notebooks ./scripts ./src ./tests ./dags)  

log() {
    local result="$1"
    shift
    printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "${result}" "$*"
}

usage() {
    cat <<'USAGE'
Usage: scripts/code_quality.sh <mode>

Modes:
  lint    Run Ruff checks and format Python files with Black.
  flake8  Run Flake8 style checks.
  bandit  Run Bandit security scan.
  all     Run all checks sequentially and fail if any check fails.
USAGE
}

run_step() {
    local name="$1"
    local status
    shift

    log START "${name}"
    if "$@"; then
        log PASS "${name}"
    else
        status=$?
        log FAIL "${name} (exit ${status})" >&2
        return "${status}"
    fi
}

run_lint() {
    local failed=0
    run_step 'Ruff lint' ruff check "${TARGETS[@]}" || failed=1
    run_step 'Black formatting' black "${TARGETS[@]}" || failed=1
    return "${failed}"
}

run_flake8() {
    run_step 'Flake8 style check' flake8 "${TARGETS[@]}"
}

run_bandit() {
    run_step 'Bandit security scan' bandit -c pyproject.toml -r "${TARGETS[@]}"
}

run_all() {
    local failed=0
    run_lint || failed=1
    run_flake8 || failed=1
    run_bandit || failed=1
    return "${failed}"
}

run_mode() {
    local mode_name="$1"
    local status
    shift

    log START "Mode ${mode_name}"
    if "$@"; then
        log PASS "Mode ${mode_name}"
    else
        status=$?
        log FAIL "Mode ${mode_name} (exit ${status})" >&2
        return "${status}"
    fi
}

mode="${1:-}"
if [[ "$#" -gt 1 ]]; then
    usage >&2
    exit 2
fi

case "${mode}" in
    lint) run_mode lint run_lint ;;
    flake8) run_mode flake8 run_flake8 ;;
    bandit) run_mode bandit run_bandit ;;
    all) run_mode all run_all ;;
    -h|--help) usage ;;
    *) usage >&2; exit 2 ;;
esac
