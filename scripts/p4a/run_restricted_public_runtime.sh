#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# P4A Restricted Public Runtime Wrapper
# ---------------------------------------------------------------------------
# This wrapper is the default-off activation gate for the restricted public
# First Launch runtime.  It enforces all activation and configuration
# preconditions before exec'ing the Python entrypoint.
#
# Without the activation permit, correct enable value, exact mode, and all
# required configuration paths, this script exits nonzero before Python
# execution.  It never creates the activation permit, never creates real
# configuration, and never accesses AWS.
# ---------------------------------------------------------------------------

# --- Paths ---------------------------------------------------------------
ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"
PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"

# --- Required exact values -----------------------------------------------
REQUIRED_ENABLE_VALUE="1"
REQUIRED_MODE="RESTRICTED_PUBLIC_LIVE_SHADOW"

# --- Approved directories ------------------------------------------------
APPROVED_STATE_DIR="/var/lib/trader-assist-v0"
APPROVED_CONFIG_DIR="/etc/trader-assist-v0"

# ===========================================================================
# 1. Activation permit
# ===========================================================================
if [[ ! -f "${ACTIVATION_PERMIT}" ]]; then
    echo "ERROR: activation permit not found at ${ACTIVATION_PERMIT}" >&2
    exit 1
fi

# ===========================================================================
# 2. Enable value
# ===========================================================================
if [[ "${TRADER_ASSIST_V0_ENABLE:-}" != "${REQUIRED_ENABLE_VALUE}" ]]; then
    echo "ERROR: TRADER_ASSIST_V0_ENABLE must be exactly '${REQUIRED_ENABLE_VALUE}'" >&2
    exit 1
fi

# ===========================================================================
# 3. Mode
# ===========================================================================
if [[ "${TRADER_ASSIST_V0_MODE:-}" != "${REQUIRED_MODE}" ]]; then
    echo "ERROR: TRADER_ASSIST_V0_MODE must be exactly '${REQUIRED_MODE}'" >&2
    exit 1
fi

# ===========================================================================
# 4. Required configuration paths
# ===========================================================================
if [[ -z "${TRADER_ASSIST_V0_DATABASE_PATH:-}" ]]; then
    echo "ERROR: TRADER_ASSIST_V0_DATABASE_PATH is required" >&2
    exit 1
fi

if [[ -z "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH:-}" ]]; then
    echo "ERROR: TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH is required" >&2
    exit 1
fi

if [[ -z "${TRADER_ASSIST_V0_WEBHOOK_URL:-}" ]]; then
    echo "ERROR: TRADER_ASSIST_V0_WEBHOOK_URL is required" >&2
    exit 1
fi

# ===========================================================================
# 5. Path containment: database must be under approved state directory
# ===========================================================================
DB_REALPATH="$(realpath "${TRADER_ASSIST_V0_DATABASE_PATH}" 2>/dev/null || true)"
if [[ -z "${DB_REALPATH}" ]]; then
    echo "ERROR: cannot resolve database path" >&2
    exit 1
fi
APPROVED_STATE_REAL="$(realpath "${APPROVED_STATE_DIR}" 2>/dev/null || true)"
if [[ "${DB_REALPATH}" != "${APPROVED_STATE_REAL}"/* ]]; then
    echo "ERROR: database path must be under ${APPROVED_STATE_DIR}" >&2
    exit 1
fi

# ===========================================================================
# 6. Path containment: risk config must be under approved config directory
# ===========================================================================
RISK_REALPATH="$(realpath "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}" 2>/dev/null || true)"
if [[ -z "${RISK_REALPATH}" ]]; then
    echo "ERROR: cannot resolve risk configuration path" >&2
    exit 1
fi
APPROVED_CONFIG_REAL="$(realpath "${APPROVED_CONFIG_DIR}" 2>/dev/null || true)"
if [[ "${RISK_REALPATH}" != "${APPROVED_CONFIG_REAL}"/* ]]; then
    echo "ERROR: risk configuration path must be under ${APPROVED_CONFIG_DIR}" >&2
    exit 1
fi

# ===========================================================================
# 7. Authorization header: must be an exact pair
# ===========================================================================
AUTH_NAME="${TRADER_ASSIST_V0_AUTHORIZATION_HEADER_NAME:-}"
AUTH_VALUE="${TRADER_ASSIST_V0_AUTHORIZATION_HEADER_VALUE:-}"

if [[ -n "${AUTH_NAME}" && -z "${AUTH_VALUE}" ]]; then
    echo "ERROR: authorization header name set but value is empty" >&2
    exit 1
fi
if [[ -z "${AUTH_NAME}" && -n "${AUTH_VALUE}" ]]; then
    echo "ERROR: authorization header value set but name is empty" >&2
    exit 1
fi

# ===========================================================================
# 8. Construct Python argv as a bash array and exec
# ===========================================================================

PYTHON_ARGS=(
    "${PYTHON_EXECUTABLE}"
    "${PYTHON_ENTRYPOINT}"
    "--enable-restricted-public-runtime"
    "--mode" "${REQUIRED_MODE}"
    "--database-path" "${TRADER_ASSIST_V0_DATABASE_PATH}"
    "--risk-configuration-path" "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}"
    "--webhook-url" "${TRADER_ASSIST_V0_WEBHOOK_URL}"
    "--webhook-timeout-seconds" "${TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS:-10}"
    "--acknowledgement-timeout-seconds" "${TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS:-30}"
    "--session-timeout-seconds" "${TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS:-21600}"
)

if [[ -n "${AUTH_NAME}" ]]; then
    PYTHON_ARGS+=(
        "--authorization-header-name" "${AUTH_NAME}"
        "--authorization-header-value" "${AUTH_VALUE}"
    )
fi

exec "${PYTHON_ARGS[@]}"