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
#
# AUTHENTICATED_WEBHOOK_HEADER_SUPPORT:
# DEFERRED_PENDING_SEPARATELY_AUTHORIZED_SECURE_SECRET_INGRESS
# ---------------------------------------------------------------------------

# --- Paths ---------------------------------------------------------------
ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"
PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"
PYTHONPATH_FORCED="/opt/trader-assist-v0/src"

# --- Required exact values -----------------------------------------------
REQUIRED_ENABLE_VALUE="1"
REQUIRED_MODE="RESTRICTED_PUBLIC_LIVE_SHADOW"

# --- Approved directories ------------------------------------------------
APPROVED_STATE_DIR="/var/lib/trader-assist-v0"
APPROVED_CONFIG_DIR="/etc/trader-assist-v0"

# --- Portable canonicalization (no realpath dependency) ------------------
# Resolve an existing directory to its physical absolute path.  Returns
# empty string on failure.  Uses cd + pwd -P for bash 3.2 / macOS and
# Linux portability.
_resolve_dir() {
    local target="$1"
    if [[ ! -d "$target" ]]; then
        return 0
    fi
    ( cd "$target" && pwd -P ) 2>/dev/null || true
}

# Resolve an existing regular file to its physical absolute path.  Returns
# empty string on failure.
_resolve_file() {
    local target="$1"
    if [[ ! -f "$target" ]]; then
        return 0
    fi
    local dir
    dir="$( cd "$(dirname "$target")" && pwd -P )" 2>/dev/null || true
    if [[ -z "$dir" ]]; then
        return 0
    fi
    echo "${dir}/$(basename "$target")"
}

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
# 5. Approved directory canonicalization
#    The approved state and config directories must exist and canonicalize.
#    Same-UID shell TOCTOU races are reduced by ownership and service
#    isolation (root-owned config, traderassist-owned state, systemd
#    hardening) but are not mathematically eliminated.
# ===========================================================================
APPROVED_STATE_REAL="$(_resolve_dir "${APPROVED_STATE_DIR}")"
if [[ -z "${APPROVED_STATE_REAL}" ]]; then
    echo "ERROR: approved state directory cannot canonicalize: ${APPROVED_STATE_DIR}" >&2
    exit 1
fi

APPROVED_CONFIG_REAL="$(_resolve_dir "${APPROVED_CONFIG_DIR}")"
if [[ -z "${APPROVED_CONFIG_REAL}" ]]; then
    echo "ERROR: approved config directory cannot canonicalize: ${APPROVED_CONFIG_DIR}" >&2
    exit 1
fi

# ===========================================================================
# 6. Database filesystem containment
#    The database file may be absent on first start (SQLite creates it).
#    An existing database final path must not be a symlink and must be a
#    regular file.  The canonical parent must remain inside the canonical
#    approved state directory.
# ===========================================================================
if [[ "${TRADER_ASSIST_V0_DATABASE_PATH}" != /* ]]; then
    echo "ERROR: database path must be absolute" >&2
    exit 1
fi
if [[ "${TRADER_ASSIST_V0_DATABASE_PATH}" == *"/../"* || \
      "${TRADER_ASSIST_V0_DATABASE_PATH}" == *"/.." ]]; then
    echo "ERROR: database path contains traversal" >&2
    exit 1
fi

# Reject existing database symlink (covers valid and broken symlinks)
if [[ -L "${TRADER_ASSIST_V0_DATABASE_PATH}" ]]; then
    echo "ERROR: database final path must not be a symlink: ${TRADER_ASSIST_V0_DATABASE_PATH}" >&2
    exit 1
fi

# Reject existing database non-regular object; missing file is valid
if [[ -e "${TRADER_ASSIST_V0_DATABASE_PATH}" && ! -f "${TRADER_ASSIST_V0_DATABASE_PATH}" ]]; then
    echo "ERROR: database final path must be a regular file: ${TRADER_ASSIST_V0_DATABASE_PATH}" >&2
    exit 1
fi

# Database parent must exist and canonicalize inside approved state
DB_DIR="$(dirname "${TRADER_ASSIST_V0_DATABASE_PATH}")"
DB_PARENT_REAL="$(_resolve_dir "${DB_DIR}")"
if [[ -z "${DB_PARENT_REAL}" ]]; then
    echo "ERROR: database parent directory cannot canonicalize: ${DB_DIR}" >&2
    exit 1
fi
if [[ "${DB_PARENT_REAL}" != "${APPROVED_STATE_REAL}" && \
      "${DB_PARENT_REAL}" != "${APPROVED_STATE_REAL}"/* ]]; then
    echo "ERROR: database parent directory must be under ${APPROVED_STATE_DIR}" >&2
    exit 1
fi
DB_FILENAME="$(basename "${TRADER_ASSIST_V0_DATABASE_PATH}")"
if [[ "${DB_PARENT_REAL}" == "${APPROVED_STATE_REAL}" && \
      ( -z "${DB_FILENAME}" || "${DB_FILENAME}" == "." || "${DB_FILENAME}" == "/" ) ]]; then
    echo "ERROR: database path must include a filename" >&2
    exit 1
fi

# ===========================================================================
# 7. Risk configuration filesystem containment
#    The risk configuration must be an existing regular file (not a symlink)
#    inside the canonical approved config directory.
# ===========================================================================
if [[ "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}" != /* ]]; then
    echo "ERROR: risk configuration path must be absolute" >&2
    exit 1
fi
if [[ -L "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}" ]]; then
    echo "ERROR: risk configuration path must not be a symlink: ${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}" >&2
    exit 1
fi
if [[ ! -f "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}" ]]; then
    echo "ERROR: risk configuration file not found or not a regular file" >&2
    exit 1
fi
RISK_REALPATH="$(_resolve_file "${TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH}")"
if [[ -z "${RISK_REALPATH}" ]]; then
    echo "ERROR: cannot resolve risk configuration path" >&2
    exit 1
fi
if [[ "${RISK_REALPATH}" != "${APPROVED_CONFIG_REAL}" && \
      "${RISK_REALPATH}" != "${APPROVED_CONFIG_REAL}"/* ]]; then
    echo "ERROR: risk configuration path must be under ${APPROVED_CONFIG_DIR}" >&2
    exit 1
fi

# ===========================================================================
# 8. Verify Python entrypoint and executable exist
# ===========================================================================
if [[ ! -x "${PYTHON_EXECUTABLE}" ]]; then
    echo "ERROR: Python executable not found at ${PYTHON_EXECUTABLE}" >&2
    exit 1
fi
if [[ ! -f "${PYTHON_ENTRYPOINT}" ]]; then
    echo "ERROR: Python entrypoint not found at ${PYTHON_ENTRYPOINT}" >&2
    exit 1
fi

# ===========================================================================
# 9. Construct Python argv as a bash array and exec
#    PYTHONPATH is forced to the approved source tree so trader_assist_v0
#    imports exclusively from the forced source path.  public.env must
#    never define or override PYTHONPATH.
# ===========================================================================
export PYTHONPATH="${PYTHONPATH_FORCED}"

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

exec "${PYTHON_ARGS[@]}"
