#!/usr/bin/env bash
# .forge/run-tests.sh — wrapper around the project test suite.
#
# Called by forge-ship.sh via `.forge/project.yaml → tests.command`.
# Lives in a script to avoid YAML quoting issues in the naive
# _load_project_yaml.sh reader shipped with forge-os.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)/backend"
exec pytest tests/ -q -m 'not integration'
