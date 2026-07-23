#!/usr/bin/env bash
# Read-only verifier for the one approved First Launch systemd unit.
set -euo pipefail

SERVICE="trader-assist-v0-public.service"
SOURCE_UNIT="/opt/trader-assist-v0/deploy/p4a/systemd/trader-assist-v0-public.service"
INSTALLED_UNIT="/etc/systemd/system/trader-assist-v0-public.service"
PUBLIC_ENV="/etc/trader-assist-v0/public.env"
APPROVED_USER="traderassist"
APPROVED_GROUP="traderassist"
APPROVED_PYTHON="/opt/trader-assist-v0/venv/bin/python"
APPROVED_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
CGROUP_ROOT="/sys/fs/cgroup"
PROC_ROOT="/proc"
WAIT_SECONDS=30

die() { printf 'SAFE_STOP: %s\n' "$1" >&2; exit 1; }
value() { systemctl show "$SERVICE" --property="$1" --value; }

require_exact() {
    local actual="$1" expected="$2" label="$3"
    [[ "$actual" == "$expected" ]] || die "$label"
}

read_public_env() {
    local line key raw value
    DATABASE_PATH=""; RISK_PATH=""; WEBHOOK_TIMEOUT=""; ACK_TIMEOUT=""; SESSION_TIMEOUT=""
    local database_count=0 risk_count=0 webhook_count=0 ack_count=0 session_count=0
    [[ -f "$PUBLIC_ENV" && ! -L "$PUBLIC_ENV" ]] || die "public environment unavailable"
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" == \#* ]] && continue
        key="${line%%=*}"
        raw="${line#*=}"
        case "$key" in
            TRADER_ASSIST_V0_DATABASE_PATH)
                ((database_count += 1)); DATABASE_PATH="$raw" ;;
            TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH)
                ((risk_count += 1)); RISK_PATH="$raw" ;;
            TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS)
                ((webhook_count += 1)); WEBHOOK_TIMEOUT="$raw" ;;
            TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS)
                ((ack_count += 1)); ACK_TIMEOUT="$raw" ;;
            TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS)
                ((session_count += 1)); SESSION_TIMEOUT="$raw" ;;
            *)
                case "$line" in
                    TRADER_ASSIST_V0_DATABASE_PATH*|TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH*|TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS*|TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS*|TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS*)
                        die "malformed required public environment assignment" ;;
                esac ;;
        esac
    done < "$PUBLIC_ENV"
    [[ $database_count -eq 1 && $risk_count -eq 1 && $webhook_count -eq 1 && $ack_count -eq 1 && $session_count -eq 1 ]] || die "duplicate or missing public environment assignment"
    [[ "$DATABASE_PATH" == /var/lib/trader-assist-v0/* && "$RISK_PATH" == /etc/trader-assist-v0/* ]] || die "runtime path outside approved roots"
    for value in "$WEBHOOK_TIMEOUT" "$ACK_TIMEOUT" "$SESSION_TIMEOUT"; do
        [[ "$value" =~ ^[1-9][0-9]*$ ]] || die "invalid runtime timeout"
    done
}

control_group() {
    local group
    group="$(value ControlGroup)" || die "cannot inspect authorized unit cgroup"
    [[ "$group" == /* && "$group" != "/" ]] || die "ambiguous authorized cgroup"
    printf '%s\n' "$CGROUP_ROOT$group"
}

cgroup_is_empty() {
    local path="$1" pid
    [[ ! -e "$path" ]] && return 0
    [[ -f "$path/cgroup.procs" ]] || die "ambiguous authorized cgroup"
    while IFS= read -r pid || [[ -n "$pid" ]]; do
        [[ -z "$pid" ]] || return 1
    done < "$path/cgroup.procs"
    return 0
}

process_matches() {
    local needle="$1" pid user args
    while read -r pid user args; do
        if [[ "$args" == *"$needle"* ]]; then
            printf '%s %s\n' "$pid" "$user"
        fi
    done < <(ps -eo pid=,user=,args=)
}

assert_no_runtime_processes() {
    local users wrappers entries
    users="$(ps -u "$APPROVED_USER" -o pid=)" || die "cannot inspect dedicated user processes"
    [[ -z "${users//[[:space:]]/}" ]] || die "unexpected dedicated user process"
    wrappers="$(process_matches "/scripts/p4a/run_restricted_public_runtime.sh")"
    entries="$(process_matches "$APPROVED_ENTRYPOINT")"
    [[ -z "$wrappers" && -z "$entries" ]] || die "unexpected approved runtime process"
}

assert_installed() {
    local source_hash installed_hash metadata fragment dropins
    [[ -f "$SOURCE_UNIT" && ! -L "$SOURCE_UNIT" ]] || die "reviewed source unit unavailable"
    [[ -f "$INSTALLED_UNIT" && ! -L "$INSTALLED_UNIT" ]] || die "installed unit unavailable"
    source_hash="$(sha256sum "$SOURCE_UNIT" | awk '{print $1}')" || die "cannot hash reviewed source unit"
    installed_hash="$(sha256sum "$INSTALLED_UNIT" | awk '{print $1}')" || die "cannot hash installed unit"
    require_exact "$installed_hash" "$source_hash" "installed unit hash mismatch"
    metadata="$(stat -c '%U:%G:%a' "$INSTALLED_UNIT")" || die "cannot inspect installed unit metadata"
    require_exact "$metadata" "root:root:644" "installed unit owner or mode mismatch"
    systemd-analyze verify "$INSTALLED_UNIT" >/dev/null || die "systemd unit verification failed"
    fragment="$(value FragmentPath)" || die "cannot inspect authorized fragment path"
    require_exact "$fragment" "$INSTALLED_UNIT" "authorized fragment path mismatch"
    dropins="$(value DropInPaths)" || die "cannot inspect authorized drop-ins"
    [[ -z "$dropins" ]] || die "authorized unit has drop-ins"
    require_exact "$(value User)" "$APPROVED_USER" "authorized unit user mismatch"
    require_exact "$(value Group)" "$APPROVED_GROUP" "authorized unit group mismatch"
    require_exact "$(value Id)" "$SERVICE" "manager cannot inspect authorized unit"
}

assert_no_lifecycle_job() {
    local jobs
    jobs="$(systemctl list-jobs --no-legend --no-pager)" || die "cannot inspect authorized unit jobs"
    [[ "$jobs" != *"$SERVICE"* ]] || die "authorized unit has lifecycle job"
}

assert_pre_start() {
    local group
    assert_installed
    require_exact "$(value ActiveState)" "inactive" "authorized unit is not inactive"
    require_exact "$(value MainPID)" "0" "authorized unit main PID is not zero"
    assert_no_lifecycle_job
    assert_no_runtime_processes
    group="$(control_group)"
    cgroup_is_empty "$group" || die "authorized cgroup is not empty"
}

read_argv() {
    local pid="$1" arg
    ACTUAL_ARGV=()
    while IFS= read -r -d '' arg; do
        ACTUAL_ARGV+=("$arg")
    done < "$PROC_ROOT/$pid/cmdline" || die "cannot inspect authorized process argv"
    [[ ${#ACTUAL_ARGV[@]} -eq 17 ]] || die "authorized process argv length mismatch"
    [[ "${ACTUAL_ARGV[0]}" == "$APPROVED_PYTHON" && "${ACTUAL_ARGV[1]}" == "$APPROVED_ENTRYPOINT" ]] || die "authorized process executable contract mismatch"
    [[ "${ACTUAL_ARGV[2]}" == "--enable-restricted-public-runtime" && "${ACTUAL_ARGV[3]}" == "--mode" && "${ACTUAL_ARGV[4]}" == "RESTRICTED_PUBLIC_LIVE_SHADOW" ]] || die "authorized process mode contract mismatch"
    [[ "${ACTUAL_ARGV[5]}" == "--database-path" && "${ACTUAL_ARGV[6]}" == "$DATABASE_PATH" && "${ACTUAL_ARGV[7]}" == "--risk-configuration-path" && "${ACTUAL_ARGV[8]}" == "$RISK_PATH" ]] || die "authorized process path contract mismatch"
    [[ "${ACTUAL_ARGV[9]}" == "--notification-credential-file" && "${ACTUAL_ARGV[10]}" == /run/credentials/*/notification.json ]] || die "authorized process credential path contract mismatch"
    [[ "${ACTUAL_ARGV[11]}" == "--webhook-timeout-seconds" && "${ACTUAL_ARGV[12]}" == "$WEBHOOK_TIMEOUT" && "${ACTUAL_ARGV[13]}" == "--acknowledgement-timeout-seconds" && "${ACTUAL_ARGV[14]}" == "$ACK_TIMEOUT" && "${ACTUAL_ARGV[15]}" == "--session-timeout-seconds" && "${ACTUAL_ARGV[16]}" == "$SESSION_TIMEOUT" ]] || die "authorized process timeout contract mismatch"
}

assert_post_start() {
    local deadline pid executable group users wrappers entries cgroup_pid cgroup_pids=()
    read_public_env
    deadline=$((SECONDS + WAIT_SECONDS))
    while [[ "$(value ActiveState)" != "active" || "$(value MainPID)" == "0" ]]; do
        (( SECONDS < deadline )) || die "authorized unit start timeout"
        sleep 1
    done
    require_exact "$(value SubState)" "running" "authorized unit is not running"
    pid="$(value MainPID)" || die "cannot inspect authorized main PID"
    [[ "$pid" =~ ^[1-9][0-9]*$ && -d "$PROC_ROOT/$pid" ]] || die "invalid authorized main PID"
    executable="$(readlink -f "$PROC_ROOT/$pid/exe")" || die "cannot inspect authorized process executable"
    require_exact "$executable" "$APPROVED_PYTHON" "authorized process executable mismatch"
    read_argv "$pid"
    users="$(ps -u "$APPROVED_USER" -o pid=)" || die "cannot inspect dedicated user processes"
    [[ "${users//[[:space:]]/}" == "$pid" ]] || die "dedicated user does not own exactly main PID"
    wrappers="$(process_matches "/scripts/p4a/run_restricted_public_runtime.sh")"
    [[ -z "$wrappers" ]] || die "approved wrapper remains"
    entries="$(process_matches "$APPROVED_ENTRYPOINT")"
    [[ "${entries%% *}" == "$pid" && "$(printf '%s\n' "$entries" | sed '/^$/d' | wc -l | tr -d ' ')" == "1" ]] || die "approved entrypoint is not exactly main PID"
    group="$(control_group)"
    [[ -f "$group/cgroup.procs" ]] || die "authorized cgroup unavailable"
    while IFS= read -r cgroup_pid || [[ -n "$cgroup_pid" ]]; do
        [[ -z "$cgroup_pid" ]] || cgroup_pids+=("$cgroup_pid")
    done < "$group/cgroup.procs"
    [[ ${#cgroup_pids[@]} -eq 1 && "${cgroup_pids[0]}" == "$pid" ]] || die "authorized cgroup does not contain exactly main PID"
}

assert_final_state() {
    local group
    assert_installed
    require_exact "$(value ActiveState)" "inactive" "authorized unit is not inactive"
    require_exact "$(value UnitFileState)" "disabled" "authorized unit is not disabled"
    require_exact "$(value MainPID)" "0" "authorized unit main PID is not zero"
    assert_no_lifecycle_job
    assert_no_runtime_processes
    group="$(control_group)"
    cgroup_is_empty "$group" || die "authorized cgroup is not empty"
}

case "${1:-}" in
    installed) assert_installed ;;
    pre-start) assert_pre_start ;;
    post-start) assert_post_start ;;
    final-state) assert_final_state ;;
    *) printf 'usage: %s {installed|pre-start|post-start|final-state}\n' "$0" >&2; exit 2 ;;
esac
printf 'PASS: %s\n' "$1"
