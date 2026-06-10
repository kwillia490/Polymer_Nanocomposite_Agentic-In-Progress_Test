#!/bin/bash

# Legacy compatibility wrapper.
# Prefer calling workflow.py directly for new runs:
#   python3 workflow.py build
#   python3 workflow.py build --submit

set -euo pipefail

python3 workflow.py build "$@"
