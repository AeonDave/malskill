#!/usr/bin/env bash
# Install Agent Skills from this repository as folders, .skill archives, or agent slash commands.

set -euo pipefail

trap 'printf "[ERROR] Unexpected failure at line %s.\n" "$LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT=""
DESTINATION=""
FORMAT=""
LAYOUT=""
ALL=false
SKILL_REFS_RAW=""
ACTION=""
AGENT=""
SCOPE=""

VALIDATOR_SCRIPT="$SCRIPT_DIR/knowledge/skill-creator/scripts/quick_validate.py"
PACKAGER_SCRIPT="$SCRIPT_DIR/knowledge/skill-creator/scripts/package_skill.py"
DISCOVERY_EXCLUSIONS=(
    "dist"
    "installed-skills"
    "node_modules"
    "__pycache__"
)

info() {
    printf '[+] %s\n' "$1"
}

step() {
    printf '[*] %s\n' "$1"
}

warn() {
    printf '[!] %s\n' "$1"
}

usage() {
    printf '%s\n' \
        'Usage: ./install.sh [options]' \
        '' \
        'Options:' \
        '  -s, --source <dir>        Root to scan for SKILL.md folders (default: repo root)' \
        '  -d, --destination <dir>   Destination root for installed folders or .skill files' \
        '  -f, --format <folder|skill|zip>' \
        '                            folder = copy skill directories' \
        '                            skill  = create .skill zip archives' \
        '                            zip    = create standard .zip archives' \
        '  -l, --layout <flat|group>' \
        '                            flat   = install every selected skill at the destination root' \
        '                            group  = preserve the source-root-relative category structure' \
        '  -k, --skills <refs>       Comma-separated skill refs (relative paths or unique names)' \
        '  -a, --all                 Select all discovered skills' \
        '  --action <skills|commands> Skip action menu' \
        '  --agent <name>            Target agent for commands (claude-code|codex|cursor|windsurf|copilot|gemini)' \
        '  --scope <global|project>  Install scope for commands' \
        '  -h, --help                Show this help' \
        '' \
        'Examples:' \
        '  ./install.sh' \
        '  ./install.sh --all --format folder --layout flat --destination ~/.agents/skills' \
        '  ./install.sh --action commands --agent claude-code --scope global' \
        '  ./install.sh --skills offensive-tools/windows/mimikatz --format zip --layout group --destination ./dist/skills'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--source)
            SOURCE_ROOT="$2"
            shift 2
            ;;
        -d|--destination)
            DESTINATION="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -l|--layout)
            LAYOUT="$2"
            shift 2
            ;;
        -k|--skills)
            SKILL_REFS_RAW="$2"
            shift 2
            ;;
        -a|--all)
            ALL=true
            shift
            ;;
        --action)
            ACTION="$2"
            shift 2
            ;;
        --agent)
            AGENT="$2"
            shift 2
            ;;
        --scope)
            SCOPE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '[ERROR] Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$SOURCE_ROOT" ]]; then
    SOURCE_ROOT="$SCRIPT_DIR"
fi
SOURCE_ROOT="$(cd "$SOURCE_ROOT" && pwd)"

if [[ ! -f "$VALIDATOR_SCRIPT" || ! -f "$PACKAGER_SCRIPT" ]]; then
    printf '[ERROR] Validator or packager script not found under %s\n' "$SCRIPT_DIR" >&2
    exit 1
fi

declare -a PYTHON_CMD=()
is_wsl() {
    grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null || grep -qi microsoft /proc/version 2>/dev/null
}

find_python() {
    if [[ -x "$SCRIPT_DIR/.venv/bin/python3" ]]; then
        PYTHON_CMD=("$SCRIPT_DIR/.venv/bin/python3")
        return
    fi
    if ! is_wsl && [[ -x "$SCRIPT_DIR/.venv/Scripts/python.exe" ]]; then
        PYTHON_CMD=("$SCRIPT_DIR/.venv/Scripts/python.exe")
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD=(python3)
        return
    fi
    if command -v python >/dev/null 2>&1; then
        PYTHON_CMD=(python)
        return
    fi
    printf '[ERROR] Python not found. Install Python or activate the repo virtual environment first.\n' >&2
    exit 1
}

run_python() {
    "${PYTHON_CMD[@]}" "$@"
}

find_python

# ─── Skill discovery ──────────────────────────────────────────────────────────

declare -a SKILL_NAMES=()
declare -a SKILL_RELS=()
declare -a SKILL_FULLS=()

should_skip_skill_dir() {
    local rel="$1"
    local segment excluded

    IFS='/' read -r -a segments <<< "$rel"
    for segment in "${segments[@]}"; do
        if [[ "$segment" == .* ]]; then
            return 0
        fi
        if [[ "$segment" == _* ]]; then
            return 0
        fi
        for excluded in "${DISCOVERY_EXCLUSIONS[@]}"; do
            if [[ "$segment" == "$excluded" ]]; then
                return 0
            fi
        done
    done

    return 1
}

discover_skills() {
    while IFS= read -r -d '' skill_file; do
        local dir rel name
        dir="$(cd "$(dirname "$skill_file")" && pwd)"
        rel="${dir#"$SOURCE_ROOT"/}"
        if [[ "$dir" == "$SOURCE_ROOT" ]]; then
            rel="."
        fi
        if should_skip_skill_dir "$rel"; then
            continue
        fi
        name="$(basename "$dir")"
        SKILL_NAMES+=("$name")
        SKILL_RELS+=("$rel")
        SKILL_FULLS+=("$dir")
    done < <(find "$SOURCE_ROOT" -type f \( -name 'SKILL.md' -o -name 'skill.md' \) -print0 | sort -z)

    if [[ ${#SKILL_FULLS[@]} -eq 0 ]]; then
        printf '[ERROR] No SKILL.md files found under %s\n' "$SOURCE_ROOT" >&2
        exit 1
    fi
}

parse_selection_indices() {
    local raw="$1"
    local max="$2"
    local token start end value
    local -a result=()

    raw="${raw// /}"
    if [[ -z "$raw" ]]; then
        printf '[ERROR] Selection cannot be empty.\n' >&2
        exit 1
    fi
    if [[ "$raw" == "all" || "$raw" == "*" ]]; then
        for ((value = 1; value <= max; value++)); do
            result+=("$value")
        done
        printf '%s\n' "${result[@]}"
        return
    fi

    IFS=',' read -r -a tokens <<< "$raw"
    for token in "${tokens[@]}"; do
        if [[ "$token" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            start="${BASH_REMATCH[1]}"
            end="${BASH_REMATCH[2]}"
            if (( start < 1 || end > max || start > end )); then
                printf '[ERROR] Invalid range: %s\n' "$token" >&2
                exit 1
            fi
            for ((value = start; value <= end; value++)); do
                result+=("$value")
            done
        elif [[ "$token" =~ ^[0-9]+$ ]]; then
            value="$token"
            if (( value < 1 || value > max )); then
                printf '[ERROR] Index out of range: %s\n' "$token" >&2
                exit 1
            fi
            result+=("$value")
        else
            printf '[ERROR] Invalid selection token: %s\n' "$token" >&2
            exit 1
        fi
    done

    printf '%s\n' "${result[@]}" | sort -n | uniq
}

declare -a SELECTED_NAMES=()
declare -a SELECTED_RELS=()
declare -a SELECTED_FULLS=()
add_selection_by_index() {
    local index="$1"
    local full="${SKILL_FULLS[$((index - 1))]}"
    local i
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        if [[ "${SELECTED_FULLS[$i]}" == "$full" ]]; then
            return
        fi
    done
    SELECTED_NAMES+=("${SKILL_NAMES[$((index - 1))]}")
    SELECTED_RELS+=("${SKILL_RELS[$((index - 1))]}")
    SELECTED_FULLS+=("$full")
}

resolve_skill_ref() {
    local ref="$1"
    local normalized="${ref//\\//}"
    local -a exact_matches=()
    local -a name_matches=()
    local i

    for ((i = 0; i < ${#SKILL_FULLS[@]}; i++)); do
        if [[ "${SKILL_RELS[$i]}" == "$normalized" || "${SKILL_FULLS[$i]}" == "$normalized" ]]; then
            exact_matches+=("$((i + 1))")
        fi
        if [[ "${SKILL_NAMES[$i]}" == "$normalized" ]]; then
            name_matches+=("$((i + 1))")
        fi
    done

    if [[ ${#exact_matches[@]} -gt 0 ]]; then
        printf '%s\n' "${exact_matches[@]}"
        return
    fi

    if [[ ${#name_matches[@]} -eq 1 ]]; then
        printf '%s\n' "${name_matches[0]}"
        return
    fi

    if [[ ${#name_matches[@]} -gt 1 ]]; then
        printf '[ERROR] Ambiguous skill reference: %s\n' "$ref" >&2
        printf '        Use one of:\n' >&2
        for i in "${name_matches[@]}"; do
            printf '        - %s\n' "${SKILL_RELS[$((i - 1))]}" >&2
        done
        exit 1
    fi

    printf '[ERROR] Skill reference not found: %s\n' "$ref" >&2
    exit 1
}

select_skills() {
    local i ref raw_selection
    if $ALL; then
        for ((i = 1; i <= ${#SKILL_FULLS[@]}; i++)); do
            add_selection_by_index "$i"
        done
        return
    fi

    if [[ -n "$SKILL_REFS_RAW" ]]; then
        IFS=',' read -r -a refs <<< "$SKILL_REFS_RAW"
        for ref in "${refs[@]}"; do
            while IFS= read -r idx; do
                [[ -n "$idx" ]] && add_selection_by_index "$idx"
            done < <(resolve_skill_ref "$ref")
        done
        return
    fi

    step "Discovered ${#SKILL_FULLS[@]} skill folders under $SOURCE_ROOT"
    for ((i = 0; i < ${#SKILL_FULLS[@]}; i++)); do
        printf '[%3d] %s\n' "$((i + 1))" "${SKILL_RELS[$i]}"
    done
    printf '\n'
    read -r -p 'Select skills by index (e.g. 1,4-7 or all): ' raw_selection
    while IFS= read -r idx; do
        [[ -n "$idx" ]] && add_selection_by_index "$idx"
    done < <(parse_selection_indices "$raw_selection" "${#SKILL_FULLS[@]}")
}

assert_unique_artifact_names() {
    local i j
    if [[ "$LAYOUT" == 'group' ]]; then
        return
    fi
    for ((i = 0; i < ${#SELECTED_NAMES[@]}; i++)); do
        for ((j = i + 1; j < ${#SELECTED_NAMES[@]}; j++)); do
            if [[ "${SELECTED_NAMES[$i]}" == "${SELECTED_NAMES[$j]}" ]]; then
                printf '[ERROR] Selected skills would collide at install time:\n' >&2
                printf '        - %s (%s)\n' "${SELECTED_NAMES[$i]}" "${SELECTED_RELS[$i]}" >&2
                printf '        - %s (%s)\n' "${SELECTED_NAMES[$j]}" "${SELECTED_RELS[$j]}" >&2
                exit 1
            fi
        done
    done
}

skill_dir_target_path() {
    local rel="$1"
    local name="$2"

    if [[ "$LAYOUT" == 'group' && "$rel" != '.' ]]; then
        printf '%s/%s\n' "$DESTINATION" "$rel"
        return
    fi

    printf '%s/%s\n' "$DESTINATION" "$name"
}

archive_target_path() {
    local rel="$1"
    local name="$2"
    local extension="$3"
    local parent_dir

    if [[ "$LAYOUT" == 'group' && "$rel" != '.' ]]; then
        parent_dir="$(dirname "$rel")"
        if [[ "$parent_dir" != '.' ]]; then
            printf '%s/%s/%s.%s\n' "$DESTINATION" "$parent_dir" "$name" "$extension"
            return
        fi
    fi

    printf '%s/%s.%s\n' "$DESTINATION" "$name" "$extension"
}

choose_destination() {
    local home_dir choice manual index custom_index option
    local -a known_options=()
    local -a ordered_options=()

    if [[ -n "$DESTINATION" ]]; then
        mkdir -p "$DESTINATION"
        DESTINATION="$(cd "$DESTINATION" && pwd)"
        return
    fi

    home_dir="${HOME:-$SCRIPT_DIR}"
    known_options=(
        "$home_dir/.agents/skills"
        "$home_dir/.claude/skills"
        "$home_dir/.copilot/skills"
        "/etc/codex/skills"
    )

    for option in "${known_options[@]}"; do
        if [[ -d "$option" && " ${ordered_options[*]} " != *" $option "* ]]; then
            ordered_options+=("$option")
        fi
    done

    step "Choose destination root"
    for ((index = 0; index < ${#ordered_options[@]}; index++)); do
        printf '[%d] %s (existing)\n' "$((index + 1))" "${ordered_options[$index]}"
    done
    custom_index=$(( ${#ordered_options[@]} + 1 ))
    printf '[%d] Enter a custom destination path\n' "$custom_index"
    read -r -p 'Select destination: ' choice

    choice="${choice// /}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#ordered_options[@]} )); then
        DESTINATION="${ordered_options[$((choice - 1))]}"
    elif [[ "$choice" =~ ^[0-9]+$ ]] && (( choice == custom_index )); then
        read -r -p 'Enter destination path: ' manual
        if [[ -z "$manual" ]]; then
            printf '[ERROR] Destination path cannot be empty.\n' >&2
            exit 1
        fi
        DESTINATION="$manual"
    else
        printf '[ERROR] Invalid destination selection: %s\n' "$choice" >&2
        exit 1
    fi

    mkdir -p "$DESTINATION"
    DESTINATION="$(cd "$DESTINATION" && pwd)"
}

choose_format() {
    local choice
    if [[ -n "$FORMAT" ]]; then
        case "$FORMAT" in
            folder|skill|zip) return ;;
            *)
                printf '[ERROR] Unsupported format: %s\n' "$FORMAT" >&2
                exit 1
                ;;
        esac
    fi

    step 'Choose output format'
    printf '[1] folder  - copy each skill directory into the destination root\n'
    printf '[2] .skill  - create a standard zip-based .skill archive per selected skill\n'
    printf '[3] .zip    - create a standard .zip archive per selected skill\n'
    read -r -p 'Select format: ' choice
    case "${choice// /}" in
        1) FORMAT='folder' ;;
        2) FORMAT='skill' ;;
        3) FORMAT='zip' ;;
        *)
            printf '[ERROR] Invalid format selection: %s\n' "$choice" >&2
            exit 1
            ;;
    esac
}

choose_layout() {
    local choice
    if [[ -n "$LAYOUT" ]]; then
        case "$LAYOUT" in
            flat|group) return ;;
            *)
                printf '[ERROR] Unsupported layout: %s\n' "$LAYOUT" >&2
                exit 1
                ;;
        esac
    fi

    step 'Choose install layout'
    printf '[1] flat   - install every selected skill at the destination root\n'
    printf '[2] group  - preserve the source-root-relative category structure\n'
    read -r -p 'Select layout: ' choice
    case "${choice// /}" in
        1) LAYOUT='flat' ;;
        2) LAYOUT='group' ;;
        *)
            printf '[ERROR] Invalid layout selection: %s\n' "$choice" >&2
            exit 1
            ;;
    esac
}

validate_selected_skills() {
    local i
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        step "Validating ${SELECTED_RELS[$i]}"
        run_python "$VALIDATOR_SCRIPT" "${SELECTED_FULLS[$i]}"
    done
}

remove_existing_skill_directory() {
    local target="$1"
    if [[ ! -e "$target" ]]; then
        return
    fi
    if [[ ! -d "$target" ]]; then
        printf '[ERROR] Target exists and is not a directory: %s\n' "$target" >&2
        exit 1
    fi
    rm -rf "$target"
}

install_as_folders() {
    local i target target_parent
    mkdir -p "$DESTINATION"
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        target="$(skill_dir_target_path "${SELECTED_RELS[$i]}" "${SELECTED_NAMES[$i]}")"
        target_parent="$(dirname "$target")"
        if [[ -e "$target" ]]; then
            warn "Removing existing installed skill directory: $target"
            remove_existing_skill_directory "$target"
        fi
        mkdir -p "$target_parent"
        step "Installing folder ${SELECTED_RELS[$i]} -> $target"
        cp -R "${SELECTED_FULLS[$i]}" "$target"
    done
}

install_as_archives() {
    local extension="$1"
    local i target target_dir temp_dir packaged
    mkdir -p "$DESTINATION"
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        target="$(archive_target_path "${SELECTED_RELS[$i]}" "${SELECTED_NAMES[$i]}" "$extension")"
        target_dir="$(dirname "$target")"
        mkdir -p "$target_dir"
        if [[ -e "$target" ]]; then
            if [[ -d "$target" ]]; then
                printf '[ERROR] Refusing to overwrite directory with .%s archive: %s\n' "$extension" "$target" >&2
                exit 1
            fi
            warn "Removing existing archive: $target"
            rm -f "$target"
        fi
        step "Packaging ${SELECTED_RELS[$i]} -> $target"
        if [[ "$extension" == 'skill' ]]; then
            run_python "$PACKAGER_SCRIPT" "${SELECTED_FULLS[$i]}" "$target_dir"
            continue
        fi

        temp_dir="$(mktemp -d)"
        if ! run_python "$PACKAGER_SCRIPT" "${SELECTED_FULLS[$i]}" "$temp_dir"; then
            rm -rf "$temp_dir"
            exit 1
        fi

        packaged="$temp_dir/${SELECTED_NAMES[$i]}.skill"
        if [[ ! -f "$packaged" ]]; then
            rm -rf "$temp_dir"
            printf '[ERROR] Packager did not create expected archive: %s\n' "$packaged" >&2
            exit 1
        fi

        mv "$packaged" "$target"
        rm -rf "$temp_dir"
    done
}

# ─── Commands flow ────────────────────────────────────────────────────────────

AGENT_SOURCE_FILES=(claude-code codex cursor windsurf copilot gemini)
AGENT_PROJECT_ONLY=(windsurf copilot)

extract_skill_description() {
    local skill_dir="$1"
    local skill_file="$skill_dir/SKILL.md"
    [[ -f "$skill_file" ]] || return 0
    awk '
        /^---$/ { if (in_fm) exit; in_fm=1; next }
        in_fm && /^description:[ \t]*\|/ { in_block=1; next }
        in_fm && in_block && /^[ \t]+/ { sub(/^[ \t]+/, ""); print; exit }
        in_fm && /^description:[ \t]+[^|]/ {
            sub(/^description:[ \t]*/, ""); print; exit
        }
    ' "$skill_file" | head -1
}

# Arrays for discovered commands
declare -a CMD_NAMES=()
declare -a CMD_RELS=()
declare -a CMD_DIRS=()
declare -a CMD_DESCS=()
declare -a CMD_AGENTS=()  # space-separated list per entry

discover_commands() {
    local cmd_dir parent_dir name rel desc agents agent_file agent_name valid_agents

    while IFS= read -r -d '' cmd_dir; do
        parent_dir="$(dirname "$cmd_dir")"
        [[ -f "$parent_dir/SKILL.md" ]] || continue

        name="$(basename "$parent_dir")"
        rel="${parent_dir#"$SOURCE_ROOT"/}"
        [[ "$parent_dir" == "$SOURCE_ROOT" ]] && rel="."

        desc="$(extract_skill_description "$parent_dir")"
        agents=""
        for agent_name in "${AGENT_SOURCE_FILES[@]}"; do
            agent_file="$cmd_dir/$agent_name.md"
            if [[ -f "$agent_file" ]]; then
                agents="$agents $agent_name"
            fi
        done
        agents="${agents# }"
        [[ -z "$agents" ]] && continue

        CMD_NAMES+=("$name")
        CMD_RELS+=("$rel")
        CMD_DIRS+=("$cmd_dir")
        CMD_DESCS+=("$desc")
        CMD_AGENTS+=("$agents")
    done < <(find "$SOURCE_ROOT" -type d -name '.commands' -print0 | sort -z)

    if [[ ${#CMD_DIRS[@]} -eq 0 ]]; then
        printf '[ERROR] No .commands/ folders found under %s\n' "$SOURCE_ROOT" >&2
        exit 1
    fi
}

declare -a SEL_CMD_NAMES=()
declare -a SEL_CMD_DIRS=()
declare -a SEL_CMD_AGENTS=()

select_commands() {
    local raw_selection i idx
    step "Found ${#CMD_DIRS[@]} command(s)"
    for ((i = 0; i < ${#CMD_DIRS[@]}; i++)); do
        local desc="${CMD_DESCS[$i]}"
        local agents="${CMD_AGENTS[$i]}"
        local label
        if [[ -n "$desc" ]]; then
            label="${CMD_NAMES[$i]} — $desc"
        else
            label="${CMD_NAMES[$i]}"
        fi
        printf '[%3d] %s  [%s]\n' "$((i + 1))" "$label" "$agents"
    done
    printf '\n'
    read -r -p 'Select commands by index (e.g. 1,3-5 or all): ' raw_selection

    while IFS= read -r idx; do
        [[ -z "$idx" ]] && continue
        local real_idx=$(( idx - 1 ))
        SEL_CMD_NAMES+=("${CMD_NAMES[$real_idx]}")
        SEL_CMD_DIRS+=("${CMD_DIRS[$real_idx]}")
        SEL_CMD_AGENTS+=("${CMD_AGENTS[$real_idx]}")
    done < <(parse_selection_indices "$raw_selection" "${#CMD_DIRS[@]}")

    if [[ ${#SEL_CMD_DIRS[@]} -eq 0 ]]; then
        printf '[ERROR] No commands selected.\n' >&2
        exit 1
    fi
}

get_agent_command_path() {
    local agent="$1"
    local name="$2"
    local scope="$3"
    local home_dir="${HOME:-$SCRIPT_DIR}"
    local cwd
    cwd="$(pwd)"

    case "$agent" in
        claude-code)
            local base; base="$([[ "$scope" == "global" ]] && echo "$home_dir" || echo "$cwd")"
            printf '%s/.claude/commands/%s.md\n' "$base" "$name"
            ;;
        codex)
            local base; base="$([[ "$scope" == "global" ]] && echo "$home_dir" || echo "$cwd")"
            printf '%s/.codex/skills/%s.md\n' "$base" "$name"
            ;;
        cursor)
            local base; base="$([[ "$scope" == "global" ]] && echo "$home_dir" || echo "$cwd")"
            printf '%s/.cursor/rules/%s.mdc\n' "$base" "$name"
            ;;
        windsurf)
            printf '%s/.windsurf/rules/%s.md\n' "$cwd" "$name"
            ;;
        copilot)
            printf '%s/.github/instructions/%s.instructions.md\n' "$cwd" "$name"
            ;;
        gemini)
            if [[ "$scope" == "global" ]]; then
                printf '%s/.gemini/skills/%s.md\n' "$home_dir" "$name"
            else
                printf '%s/.gemini/%s.md\n' "$cwd" "$name"
            fi
            ;;
        *)
            printf '[ERROR] Unknown agent: %s\n' "$agent" >&2
            exit 1
            ;;
    esac
}

is_project_only_agent() {
    local agent="$1"
    local a
    for a in "${AGENT_PROJECT_ONLY[@]}"; do
        [[ "$a" == "$agent" ]] && return 0
    done
    return 1
}

choose_agent() {
    local available_str="$1"  # space-separated
    local -a available
    read -r -a available <<< "$available_str"

    if [[ -n "$AGENT" ]]; then
        local found=false
        local a
        for a in "${available[@]}"; do
            [[ "$a" == "$AGENT" ]] && found=true && break
        done
        if ! $found; then
            printf '[ERROR] Agent "%s" has no command file in selected commands.\n' "$AGENT" >&2
            exit 1
        fi
        printf '%s\n' "$AGENT"
        return
    fi

    local ordered=()
    local ref
    for ref in "${AGENT_SOURCE_FILES[@]}"; do
        local a
        for a in "${available[@]}"; do
            [[ "$a" == "$ref" ]] && ordered+=("$ref") && break
        done
    done

    step "Select target agent"
    local i
    for ((i = 0; i < ${#ordered[@]}; i++)); do
        printf '[%d] %s\n' "$((i + 1))" "${ordered[$i]}"
    done
    local choice
    read -r -p 'Select agent: ' choice
    choice="${choice// /}"
    if [[ ! "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#ordered[@]} )); then
        printf '[ERROR] Invalid agent selection: %s\n' "$choice" >&2
        exit 1
    fi
    printf '%s\n' "${ordered[$((choice - 1))]}"
}

choose_command_scope() {
    local agent="$1"
    local name="$2"

    if [[ -n "$SCOPE" ]]; then
        printf '%s\n' "$SCOPE"
        return
    fi

    if is_project_only_agent "$agent"; then
        printf 'project\n'
        return
    fi

    local global_path project_path
    global_path="$(get_agent_command_path "$agent" "$name" "global")"
    project_path="$(get_agent_command_path "$agent" "$name" "project")"

    step "Select install scope"
    printf '[1] global  — %s\n' "$global_path"
    printf '[2] project — %s\n' "$project_path"
    local choice
    read -r -p 'Select scope: ' choice
    case "${choice// /}" in
        1) printf 'global\n' ;;
        2) printf 'project\n' ;;
        *)
            printf '[ERROR] Invalid scope selection: %s\n' "$choice" >&2
            exit 1
            ;;
    esac
}

install_command_files() {
    local agent="$1"
    local scope="$2"
    local i src dest dest_dir

    for ((i = 0; i < ${#SEL_CMD_DIRS[@]}; i++)); do
        local name="${SEL_CMD_NAMES[$i]}"
        local cmd_dir="${SEL_CMD_DIRS[$i]}"
        src="$cmd_dir/$agent.md"

        if [[ ! -f "$src" ]]; then
            warn "No $agent command file found for '$name' — skipping"
            continue
        fi

        dest="$(get_agent_command_path "$agent" "$name" "$scope")"
        dest_dir="$(dirname "$dest")"
        mkdir -p "$dest_dir"

        if [[ -e "$dest" ]]; then
            warn "Overwriting existing: $dest"
        fi

        step "Installing $name → $dest"
        cp "$src" "$dest"
        info "$name installed for $agent"
    done
}

run_commands_flow() {
    discover_commands
    select_commands

    # Collect union of available agents across selected commands
    local all_agents_str=""
    local i a
    for ((i = 0; i < ${#SEL_CMD_AGENTS[@]}; i++)); do
        for a in ${SEL_CMD_AGENTS[$i]}; do
            [[ "$all_agents_str" == *" $a "* || "$all_agents_str" == "$a "* || "$all_agents_str" == *" $a" || "$all_agents_str" == "$a" ]] || all_agents_str="$all_agents_str $a"
        done
    done
    all_agents_str="${all_agents_str# }"

    local chosen_agent chosen_scope
    chosen_agent="$(choose_agent "$all_agents_str")"
    chosen_scope="$(choose_command_scope "$chosen_agent" "${SEL_CMD_NAMES[0]}")"

    printf '\n'
    info "Selected ${#SEL_CMD_DIRS[@]} command(s)"
    info "Agent: $chosen_agent"
    info "Scope: $chosen_scope"
    printf '\n'

    install_command_files "$chosen_agent" "$chosen_scope"

    printf '\n'
    info 'Command install complete.'
}

# ─── Action selection ─────────────────────────────────────────────────────────

choose_action() {
    if [[ -n "$ACTION" ]]; then
        case "$ACTION" in
            skills|commands) return ;;
            *)
                printf '[ERROR] Invalid action: %s\n' "$ACTION" >&2
                exit 1
                ;;
        esac
    fi

    step "Select action"
    printf '[1] Install skills   — copy skill directories or packages to a destination\n'
    printf '[2] Install commands — register slash commands for AI agents (claude-code, cursor, etc.)\n'
    local choice
    read -r -p 'Select action: ' choice
    case "${choice// /}" in
        1) ACTION='skills' ;;
        2) ACTION='commands' ;;
        *)
            printf '[ERROR] Invalid action: %s\n' "$choice" >&2
            exit 1
            ;;
    esac
}

# ─── Main ─────────────────────────────────────────────────────────────────────

printf '\n'
info "Agent Skills installer"
printf '[*] Source root: %s\n' "$SOURCE_ROOT"
printf '\n'

choose_action
printf '\n'

if [[ "$ACTION" == 'commands' ]]; then
    run_commands_flow
    exit 0
fi

# ── Skills flow ──
discover_skills
select_skills

if [[ ${#SELECTED_FULLS[@]} -eq 0 ]]; then
    printf '[ERROR] No skills selected.\n' >&2
    exit 1
fi

assert_unique_artifact_names
choose_destination
choose_format
choose_layout

printf '\n'
info "Selected ${#SELECTED_FULLS[@]} skill(s)"
info "Destination root: $DESTINATION"
info "Format: $FORMAT"
info "Layout: $LAYOUT"
printf '\n'

validate_selected_skills

case "$FORMAT" in
    folder)
        install_as_folders
        ;;
    skill)
        install_as_archives 'skill'
        ;;
    zip)
        install_as_archives 'zip'
        ;;
    *)
        printf '[ERROR] Unsupported format: %s\n' "$FORMAT" >&2
        exit 1
        ;;
esac

printf '\n'
info 'Install complete.'
for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
    if [[ "$FORMAT" == 'folder' ]]; then
        printf '    %s\n' "$(skill_dir_target_path "${SELECTED_RELS[$i]}" "${SELECTED_NAMES[$i]}")"
    elif [[ "$FORMAT" == 'zip' ]]; then
        printf '    %s\n' "$(archive_target_path "${SELECTED_RELS[$i]}" "${SELECTED_NAMES[$i]}" 'zip')"
    else
        printf '    %s\n' "$(archive_target_path "${SELECTED_RELS[$i]}" "${SELECTED_NAMES[$i]}" 'skill')"
    fi
done
