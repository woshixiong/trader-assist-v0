#!/usr/bin/env bash
# Read-only verifier for the approved dedicated First Launch service.
set -euo pipefail

SERVICE=trader-assist-v0-public.service
SOURCE_UNIT=/opt/trader-assist-v0/deploy/p4a/systemd/trader-assist-v0-public.service
INSTALLED_UNIT=/etc/systemd/system/trader-assist-v0-public.service
PUBLIC_ENV=/etc/trader-assist-v0/public.env
PROC_ROOT=/proc
CGROUP_ROOT=/sys/fs/cgroup
APP_USER=traderassist APP_GROUP=traderassist
PYTHON=/opt/trader-assist-v0/venv/bin/python
ENTRYPOINT=/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py
STATE_ROOT=/var/lib/trader-assist-v0 CONFIG_ROOT=/etc/trader-assist-v0

die() { printf 'SAFE_STOP: %s\n' "$1" >&2; exit 1; }
show() { systemctl show "$SERVICE" --property="$1" --value; }
exact() { [[ "$1" == "$2" ]] || die "$3"; }
path_under() { [[ "$1" == "$2" || "$1" == "$2"/* ]]; }

canonical_dir() { (cd "$1" 2>/dev/null && pwd -P) || return 1; }
canonical_file() {
    local parent
    parent="$(canonical_dir "$(dirname "$1")")" || return 1
    printf '%s/%s\n' "$parent" "$(basename "$1")"
}

read_env() {
    local line key value count_db=0 count_risk=0 count_webhook=0 count_ack=0 count_session=0
    DB_PATH= RISK_PATH= WEBHOOK=10 ACK=30 SESSION=21600
    [[ -f "$PUBLIC_ENV" && ! -L "$PUBLIC_ENV" ]] || die 'public environment unavailable'
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" == \#* ]] && continue
        key="${line%%=*}"; value="${line#*=}"
        [[ "$key" != "$line" ]] || die 'malformed public environment assignment'
        case "$key" in
            TRADER_ASSIST_V0_DATABASE_PATH) ((++count_db)); DB_PATH="$value" ;;
            TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH) ((++count_risk)); RISK_PATH="$value" ;;
            TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS) ((++count_webhook)); WEBHOOK="$value" ;;
            TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS) ((++count_ack)); ACK="$value" ;;
            TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS) ((++count_session)); SESSION="$value" ;;
        esac
    done < "$PUBLIC_ENV"
    [[ $count_db -eq 1 && $count_risk -eq 1 && $count_webhook -le 1 && $count_ack -le 1 && $count_session -le 1 ]] || die 'duplicate or missing public environment assignment'
    for value in "$WEBHOOK" "$ACK" "$SESSION"; do [[ "$value" =~ ^[1-9][0-9]*$ ]] || die 'invalid runtime timeout'; done
    valid_paths
}

valid_paths() {
    local state parent config real
    [[ "$DB_PATH" == /* && "$DB_PATH" != *'/../'* && "$DB_PATH" != */.. && ! -L "$DB_PATH" ]] || die 'database path is malformed'
    [[ ! -e "$DB_PATH" || -f "$DB_PATH" ]] || die 'database target is not a regular file'
    state="$(canonical_dir "$STATE_ROOT")" || die 'state root unavailable'
    parent="$(canonical_dir "$(dirname "$DB_PATH")")" || die 'database parent unavailable'
    path_under "$parent" "$state" || die 'database path escapes state root'
    DB_PATH="$parent/$(basename "$DB_PATH")"
    [[ "$RISK_PATH" == /* && ! -L "$RISK_PATH" && -f "$RISK_PATH" ]] || die 'risk path is not a regular file'
    real="$(canonical_file "$RISK_PATH")" || die 'risk path unavailable'
    config="$(canonical_dir "$CONFIG_ROOT")" || die 'config root unavailable'
    path_under "$real" "$config" || die 'risk path escapes config root'
    RISK_PATH="$real"
}

assert_installed() {
    local metadata fragment dropins
    [[ -f "$SOURCE_UNIT" && ! -L "$SOURCE_UNIT" && -f "$INSTALLED_UNIT" && ! -L "$INSTALLED_UNIT" ]] || die 'unit file unavailable'
    cmp -s "$SOURCE_UNIT" "$INSTALLED_UNIT" || die 'installed unit differs from reviewed unit'
    metadata="$(stat -c '%U:%G:%a' "$INSTALLED_UNIT")" || die 'cannot inspect installed unit metadata'
    exact "$metadata" root:root:644 'installed unit owner or mode mismatch'
    systemd-analyze verify "$INSTALLED_UNIT" >/dev/null || die 'systemd unit verification failed'
    fragment="$(show FragmentPath)" || die 'cannot inspect unit fragment'
    dropins="$(show DropInPaths)" || die 'cannot inspect unit drop-ins'
    exact "$fragment" "$INSTALLED_UNIT" 'unit fragment drift'
    [[ -z "$dropins" ]] || die 'unexpected unit drop-in'
    exact "$(show User)" "$APP_USER" 'unit user drift'
    exact "$(show Group)" "$APP_GROUP" 'unit group drift'
    exact "$(show Id)" "$SERVICE" 'unit identity drift'
}

snapshot() {
    PROCESS_SNAPSHOT="$(ps -eo pid=,uid=,args=)" || die 'cannot inspect process snapshot'
    APP_UID="$(id -u "$APP_USER")" || die 'cannot resolve dedicated user'
}

matching_pids() {
    local needle="$1"
    awk -v needle="$needle" '$0 ~ needle {print $1}' <<<"$PROCESS_SNAPSHOT"
}

uid_pids() { awk -v uid="$APP_UID" '$2 == uid {print $1}' <<<"$PROCESS_SNAPSHOT"; }

cgroup_path() {
    local group
    group="$(show ControlGroup)" || die 'cannot inspect control group'
    [[ -z "$group" || ( "$group" == /* && "$group" != / && "$group" != *'/../'* && "$group" != */.. ) ]] || die 'malformed control group'
    [[ -z "$group" ]] && return 0
    printf '%s%s\n' "$CGROUP_ROOT" "$group"
}

empty_cgroup() {
    local group="$1" pid
    [[ -z "$group" || ! -e "$group" ]] && return 0
    [[ -f "$group/cgroup.procs" ]] || die 'unexplainable control group'
    while IFS= read -r pid || [[ -n "$pid" ]]; do [[ -z "$pid" ]] || return 1; done < "$group/cgroup.procs"
}

no_runtime() {
    local pids wrappers entries group
    snapshot
    pids="$(uid_pids)"; wrappers="$(matching_pids '/scripts/p4a/run_restricted_public_runtime.sh')"; entries="$(matching_pids "$ENTRYPOINT")"
    [[ -z "${pids//[[:space:]]/}" && -z "$wrappers" && -z "$entries" ]] || die 'unexpected runtime process'
    group="$(cgroup_path)"; empty_cgroup "$group" || die 'control group is not empty'
}

no_job() {
    local jobs
    jobs="$(systemctl list-jobs --no-legend --no-pager)" || die 'cannot inspect lifecycle jobs'
    [[ "$jobs" != *"$SERVICE"* ]] || die 'unit lifecycle job present'
}

read_argv() {
    local pid="$1" arg env entry count=0
    ARGV=(); CREDENTIAL_DIR=
    while IFS= read -r -d '' arg; do ARGV+=("$arg"); done < "$PROC_ROOT/$pid/cmdline" || die 'cannot inspect process argv'
    [[ ${#ARGV[@]} -eq 17 ]] || die 'runtime argv length mismatch'
    while IFS= read -r -d '' env; do
        if [[ "$env" == CREDENTIALS_DIRECTORY=* ]]; then ((++count)); CREDENTIAL_DIR="${env#*=}"; fi
    done < "$PROC_ROOT/$pid/environ" || die 'cannot inspect process environment'
    [[ $count -eq 1 && "$CREDENTIAL_DIR" == /* && "$CREDENTIAL_DIR" != *'/../'* && "$CREDENTIAL_DIR" != */.. ]] || die 'credential directory contract mismatch'
    entry="$CREDENTIAL_DIR/notification.json"
    [[ "${ARGV[*]}" == "${PYTHON} ${ENTRYPOINT} --enable-restricted-public-runtime --mode RESTRICTED_PUBLIC_LIVE_SHADOW --database-path ${DB_PATH} --risk-configuration-path ${RISK_PATH} --notification-credential-file ${entry} --webhook-timeout-seconds ${WEBHOOK} --acknowledgement-timeout-seconds ${ACK} --session-timeout-seconds ${SESSION}" ]] || die 'runtime argv contract mismatch'
}

post_once() {
    local pid exe pids wrappers entries group group_pids
    assert_installed
    exact "$(show ActiveState)" active 'unit is not active'
    exact "$(show SubState)" running 'unit is not running'
    pid="$(show MainPID)" || die 'cannot inspect main PID'
    [[ "$pid" =~ ^[1-9][0-9]*$ && -d "$PROC_ROOT/$pid" ]] || die 'main PID disappeared'
    exe="$(readlink -f "$PROC_ROOT/$pid/exe")" || die 'cannot inspect process executable'
    snapshot; wrappers="$(matching_pids '/scripts/p4a/run_restricted_public_runtime.sh')"
    if [[ "$exe" != "$PYTHON" && "$wrappers" == *"$pid"* ]]; then return 75; fi
    exact "$exe" "$PYTHON" 'process executable mismatch'
    read_argv "$pid"
    pids="$(uid_pids)"; exact "${pids//$'\n'/ }" "$pid" 'dedicated user does not own exactly main PID'
    [[ -z "$wrappers" ]] || die 'wrapper remains after Python transition'
    entries="$(matching_pids "$ENTRYPOINT")"; exact "$entries" "$pid" 'entrypoint is not exactly main PID'
    group="$(cgroup_path)"; [[ -n "$group" && -f "$group/cgroup.procs" ]] || die 'post-start control group unavailable'
    group_pids="$(sed '/^$/d' "$group/cgroup.procs")" || die 'cannot inspect control group'
    exact "$group_pids" "$pid" 'control group does not contain exactly main PID'
    assert_installed
    exact "$(show ActiveState)" active 'runtime identity drift'
    exact "$(show SubState)" running 'runtime identity drift'
    exact "$(show MainPID)" "$pid" 'runtime identity drift'
    exact "$(readlink -f "$PROC_ROOT/$pid/exe")" "$PYTHON" 'runtime identity drift'
    read_argv "$pid"
}

post_start() {
    local deadline=$((SECONDS + 30)) rc
    read_env
    while :; do
        if post_once; then return 0; else rc=$?; fi
        [[ $rc -eq 75 && $SECONDS -lt $deadline ]] || die 'runtime did not stabilize before deadline'
        sleep 1
    done
}

case "${1:-}" in
    installed) assert_installed ;;
    pre-start) assert_installed; exact "$(show ActiveState)" inactive 'unit is not inactive'; exact "$(show MainPID)" 0 'main PID is not zero'; no_job; no_runtime ;;
    post-start) post_start ;;
    final-state) assert_installed; exact "$(show ActiveState)" inactive 'unit is not inactive'; exact "$(show UnitFileState)" disabled 'unit is not disabled'; exact "$(show MainPID)" 0 'main PID is not zero'; no_job; no_runtime ;;
    *) printf 'usage: %s {installed|pre-start|post-start|final-state}\n' "$0" >&2; exit 2 ;;
esac
printf 'PASS: %s\n' "$1"
