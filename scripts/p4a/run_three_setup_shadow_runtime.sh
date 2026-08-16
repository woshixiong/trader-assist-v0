#!/usr/bin/env bash
set -euo pipefail

ACTIVATION_PERMIT="/etc/trader-assist-v0/three-setup-activation-permit"
PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_three_setup_shadow_runtime.py"
PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"
PYTHONPATH_FORCED="/opt/trader-assist-v0/src:/opt/trader-assist-v0"
CONFIG_PATH="${TRADER_ASSIST_V0_THREE_SETUP_CONFIG_PATH:-/etc/trader-assist-v0/three-setup-shadow.json}"

[[ -f "${ACTIVATION_PERMIT}" ]] || { echo "ERROR: activation permit is absent" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_ENABLE:-}" == "1" ]] || { echo "ERROR: enable must be 1" >&2; exit 1; }
[[ "${TRADER_ASSIST_V0_THREE_SETUP_MODE:-}" == "THREE_SETUP_SHADOW_RELEASE" ]] || { echo "ERROR: invalid mode" >&2; exit 1; }
[[ "${CONFIG_PATH}" == /etc/trader-assist-v0/* && -f "${CONFIG_PATH}" && ! -L "${CONFIG_PATH}" ]] || { echo "ERROR: invalid config path" >&2; exit 1; }
[[ -n "${CREDENTIALS_DIRECTORY:-}" && "${CREDENTIALS_DIRECTORY}" == /* ]] || { echo "ERROR: credential directory is absent" >&2; exit 1; }
[[ -f "${CREDENTIALS_DIRECTORY}/notification.json" ]] || { echo "ERROR: notification credential is absent" >&2; exit 1; }
[[ -x "${PYTHON_EXECUTABLE}" && -f "${PYTHON_ENTRYPOINT}" ]] || { echo "ERROR: approved Python entrypoint is absent" >&2; exit 1; }

export PYTHONPATH="${PYTHONPATH_FORCED}"
exec "${PYTHON_EXECUTABLE}" "${PYTHON_ENTRYPOINT}" \
  --enable-three-setup-shadow-runtime \
  --mode THREE_SETUP_SHADOW_RELEASE \
  --config-path "${CONFIG_PATH}" \
  --notification-credential-file "${CREDENTIALS_DIRECTORY}/notification.json"
