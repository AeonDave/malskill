#!/usr/bin/env bash
# Install Agent Skills from this repository as folders or .skill archives.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT=""
DESTINATION=""
FORMAT=""
ALL=false
SKILL_REFS_RAW=""

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
    cat <<EOF
Usage: ./install.sh [options]

Options:
  -s, --source <dir>        Root to scan for SKILL.md folders (default: repo root)
  -d, --destination <dir>   Destination root for installed folders or .skill files
  -f, --format <folder|skill>
                            folder = copy skill directories
                            skill  = create .skill zip archives
  -k, --skills <refs>       Comma-separated skill refs (relative paths or unique names)
  -a, --all                 Select all discovered skills
  -h, --help                Show this help

Examples:
  ./install.sh
  ./install.sh --all --format folder --destination ~/.agents/skills
  ./install.sh --skills offensive-tools/windows/mimikatz,programming/python-patterns --format skill --destination ./dist/skills
EOF
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
        -k|--skills)
            SKILL_REFS_RAW="$2"
            shift 2
            ;;
        -a|--all)
            ALL=true
            shift
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

discover_skills

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

select_skills

if [[ ${#SELECTED_FULLS[@]} -eq 0 ]]; then
    printf '[ERROR] No skills selected.\n' >&2
    exit 1
fi

assert_unique_artifact_names() {
    local i j
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

assert_unique_artifact_names

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

choose_destination

choose_format() {
    local choice
    if [[ -n "$FORMAT" ]]; then
        case "$FORMAT" in
            folder|skill) return ;;
            *)
                printf '[ERROR] Unsupported format: %s\n' "$FORMAT" >&2
                exit 1
                ;;
        esac
    fi

    step 'Choose output format'
    printf '[1] folder  - copy each skill directory into the destination root\n'
    printf '[2] .skill  - create a standard zip-based .skill archive per selected skill\n'
    read -r -p 'Select format: ' choice
    case "${choice// /}" in
        1) FORMAT='folder' ;;
        2) FORMAT='skill' ;;
        *)
            printf '[ERROR] Invalid format selection: %s\n' "$choice" >&2
            exit 1
            ;;
    esac
}

choose_format

printf '\n'
info "Selected ${#SELECTED_FULLS[@]} skill(s)"
info "Destination root: $DESTINATION"
info "Format: $FORMAT"
printf '\n'

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
    if [[ -f "$target/SKILL.md" || -f "$target/skill.md" ]]; then
        rm -rf "$target"
        return
    fi
    printf '[ERROR] Refusing to remove existing directory not recognized as a skill folder: %s\n' "$target" >&2
    exit 1
}

install_as_folders() {
    local i target
    mkdir -p "$DESTINATION"
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        target="$DESTINATION/${SELECTED_NAMES[$i]}"
        if [[ -e "$target" ]]; then
            warn "Removing existing installed skill directory: $target"
            remove_existing_skill_directory "$target"
        fi
        step "Installing folder ${SELECTED_RELS[$i]} -> $target"
        cp -R "${SELECTED_FULLS[$i]}" "$DESTINATION/"
    done
}

install_as_packages() {
    local i target
    mkdir -p "$DESTINATION"
    for ((i = 0; i < ${#SELECTED_FULLS[@]}; i++)); do
        target="$DESTINATION/${SELECTED_NAMES[$i]}.skill"
        if [[ -e "$target" ]]; then
            if [[ -d "$target" ]]; then
                printf '[ERROR] Refusing to overwrite directory with .skill archive: %s\n' "$target" >&2
                exit 1
            fi
            warn "Removing existing archive: $target"
            rm -f "$target"
        fi
        step "Packaging ${SELECTED_RELS[$i]} -> $target"
        run_python "$PACKAGER_SCRIPT" "${SELECTED_FULLS[$i]}" "$DESTINATION"
    done
}

validate_selected_skills

case "$FORMAT" in
    folder)
        install_as_folders
        ;;
    skill)
        install_as_packages
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
        printf '    %s\n' "$DESTINATION/${SELECTED_NAMES[$i]}"
    else
        printf '    %s\n' "$DESTINATION/${SELECTED_NAMES[$i]}.skill"
    fi
done
