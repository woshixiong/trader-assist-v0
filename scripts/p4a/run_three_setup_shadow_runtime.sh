#!/usr/bin/env bash
set -euo pipefail

ACTIVATION_PERMIT="/etc/trader-assist-v0/three-setup-activation-permit"
PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_three_setup_shadow_runtime.py"
PREFLIGHT_ENTRYPOINT="/opt/trader-assist-v0/scripts/three_setup_shadow_preflight.py"
PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"
PYTHONPATH_FORCED="/opt/trader-assist-v0/src:/opt/trader-assist-v0"
RELEASE_MANIFEST="/opt/trader-assist-v0/three-setup-release-manifest.json"
CONFIG_PATH="${TRADER_ASSIST_V0_THREE_SETUP_CONFIG_PATH:-/etc/trader-assist-v0/three-setup-shadow.json}"

[[ -f "${ACTIVATION_PERMIT}" ]] || { echo "ERROR: activation permit is absent" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_ENABLE:-}" == "1" ]] || { echo "ERROR: enable must be 1" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_MODE:-}" == "THREE_SETUP_SHADOW_RELEASE" ]] || { echo "ERROR: invalid mode" >&2; exit 1; }
[[ "${CONFIG_PATH}" == /etc/trader-assist-v0/* && -f "${CONFIG_PATH}" && ! -L "${CONFIG_PATH}" ]] || { echo "ERROR: invalid config path" >&2; exit 1; }
[[ -n "${CREDENTIALS_DIRECTORY:-}" && "${CREDENTIALS_DIRECTORY}" == /* ]] || { echo "ERROR: credential directory is absent" >&2; exit 1; }
[[ -f "${CREDENTIALS_DIRECTORY}/notification.json" ]] || { echo "ERROR: notification credential is absent" >&2; exit 1; }
[[ -x "${PYTHON_EXECUTABLE}" && -f "${PYTHON_ENTRYPOINT}" ]] || { echo "ERROR: approved Python entrypoint is absent" >&2; exit 1; }
[[ -f "${PREFLIGHT_ENTRYPOINT}" && -f "${RELEASE_MANIFEST}" ]] || { echo "ERROR: candidate preflight surface is absent" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_RELEASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "ERROR: exact release SHA is absent" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_RELEASE_TREE:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "ERROR: exact release TREE is absent" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_MANIFEST_DIGEST:-}" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: manifest digest is absent" >&2; exit 1; }

export PYTHONPATH="${PYTHONPATH_FORCED}"
"${PYTHON_EXECUTABLE}" "${PREFLIGHT_ENTRYPOINT}" \
  --root /opt/trader-assist-v0 \
  --release-manifest "${RELEASE_MANIFEST}" \
  --config "${CONFIG_PATH}" \
  --expected-sha "${TRADER_ASSIST_V0_THREE_SETUP_RELEASE_SHA}" \
  --expected-tree "${TRADER_ASSIST_V0_THREE_SETUP_RELEASE_TREE}" \
  --expected-manifest-digest "${TRADER_ASSIST_V0_THREE_SETUP_MANIFEST_DIGEST}" \
  --pip-check-with python3.12
exec "${PYTHON_EXECUTABLE}" "${PYTHON_ENTRYPOINT}" \
  --enable-three-setup-shadow-runtime \
  --mode THREE_SETUP_SHADOW_RELEASE \
  --config-path "${CONFIG_PATH}" \
  --notification-credential-file "${CREDENTIALS_DIRECTORY}/notification.json"
