#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
tar --exclude='__pycache__' --exclude='*.pyc' -czf dist/sysadmin-gym-v5-0-1.tar.gz gym.sh gym-config.json linux_gym modules fixtures tests README.md README-INSTALL.md RHCSA-COVERAGE.md
printf '%s\n' dist/sysadmin-gym-v5-0-1.tar.gz
