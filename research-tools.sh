#!/usr/bin/env bash
set -euo pipefail

VERSION="palimpsest-research-tools v0.1.0"
SCRIPT_NAME="$(basename "$0")"

# ── Helpers ──────────────────────────────────────────────────────────────────

usage() {
    cat <<EOF
${SCRIPT_NAME} — palimpsest research tools

Usage:
  ${SCRIPT_NAME} <subcommand> [options]

Subcommands:
  wayback          Fetch historical URL snapshots from the Wayback Machine
  companies-house  Look up UK company information
  whois            WHOIS lookup for a domain
  rdap             RDAP lookup for a domain

Options:
  --version   Print version and exit
  --help      Show this help message

Run '${SCRIPT_NAME} <subcommand> --help' for subcommand-specific help.
EOF
}

die() {
    echo "Error: $*" >&2
    exit 1
}

http_get() {
    local url="$1" code tmp
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    code="$(curl -sS --max-time 30 -o "$tmp" -w "%{http_code}" "$url")" || die "HTTP request failed for: $url"
    echo "$code"
}

http_get_auth() {
    local url="$1" auth="$2" code tmp
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    code="$(curl -sS --max-time 30 -u "$auth" -o "$tmp" -w "%{http_code}" "$url")" || die "HTTP request failed for: $url"
    echo "$code"
}

TEMP_FILES=()

cleanup() {
    rm -f "${TEMP_FILES[@]}"
}

# ── wayback ───────────────────────────────────────────────────────────────────

wayback_help() {
    cat <<EOF
Usage: ${SCRIPT_NAME} wayback <url> [--from YYYY] [--to YYYY] [--limit N] [--json]

Fetches historical URL snapshots from the Wayback Machine CDX API.

Arguments:
  <url>        The URL to look up (required)
  --from YYYY  Start year (e.g. 2005)
  --to YYYY    End year (e.g. 2020)
  --limit N    Maximum results (default: 100)
  --json       Output raw JSON instead of a markdown table
EOF
}

cmd_wayback() {
    local url="" from="" to="" limit="100" json_output=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h) wayback_help; exit 0 ;;
            --from) shift; from="$1"; shift ;;
            --to) shift; to="$1"; shift ;;
            --limit) shift; limit="$1"; shift ;;
            --json) json_output=true; shift ;;
            --*) die "Unknown flag: $1" ;;
            *)  if [[ -z "$url" ]]; then url="$1"; shift; else die "Unexpected argument: $1"; fi ;;
        esac
    done

    [[ -z "$url" ]] && die "wayback: <url> is required. Use --help for usage."

    local api_url="https://web.archive.org/cdx/search/cdx?url=${url}&output=json&fl=timestamp,original,statuscode,digest,mimetype"
    [[ -n "$from" ]]  && api_url+="&from=${from}"
    [[ -n "$to" ]]    && api_url+="&to=${to}"
    api_url+="&limit=${limit}"

    local http_code body tmp
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    http_code=$(curl -sS --max-time 30 -w "%{http_code}" -o "$tmp" "$api_url") || die "HTTP request failed for Wayback CDX API"
    body="$(cat "$tmp")"

    if [[ "$http_code" != "200" ]]; then
        die "Wayback API returned HTTP ${http_code}: ${body}"
    fi

    if [[ "$json_output" == "true" ]]; then
        echo "$body"
        return 0
    fi

    # Parse JSON array-of-arrays; first row is headers
    local headers
    headers="$(echo "$body" | jq -r '.[0] | join(" | ")')"
    local rows
    rows="$(echo "$body" | jq -r '.[1:][] | [.[0], .[1], .[2], .[3][:10], .[4]] | join(" | ")')"

    if [[ -z "$rows" ]]; then
        echo "No snapshots found for: ${url}"
        return 0
    fi

    echo "### Wayback Machine snapshots for \`${url}\`"
    echo ""
    echo "| ${headers} |"
    # Build separator line with same column count
    local col_count
    col_count="$(echo "$body" | jq -r '.[0] | length')"
    local sep=""
    for ((i=0; i<col_count; i++)); do sep+="| --- "; done
    sep+="|"
    echo "${sep}"
    while IFS= read -r row; do
        echo "| ${row} |"
    done <<< "$rows"
    echo ""
    echo "Source: ${api_url}"
}

# ── companies-house ───────────────────────────────────────────────────────────

companies_house_help() {
    cat <<EOF
Usage: ${SCRIPT_NAME} companies-house <company-number> [--json]

Looks up UK company information from the Companies House API.

Requires the COMPANIES_HOUSE_API_KEY environment variable.

Options:
  --json  Output raw JSON instead of a markdown table
EOF
}

cmd_companies_house() {
    # Check for help before consuming the positional arg
    for arg in "$@"; do
        if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
            companies_house_help
            exit 0
        fi
    done

    [[ $# -lt 1 ]] && die "companies-house: <company-number> is required. Use --help for usage."

    local company_number="$1"
    local json_output=false
    shift

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json) json_output=true; shift ;;
            *) die "Unknown flag: $1" ;;
        esac
    done

    local api_key="${COMPANIES_HOUSE_API_KEY:-}"
    [[ -z "$api_key" ]] && die "COMPANIES_HOUSE_API_KEY environment variable is required."

    local profile_url="https://api.company-information.service.gov.uk/company/${company_number}"
    local officers_url="https://api.company-information.service.gov.uk/company/${company_number}/officers"

    # Fetch company profile
    local profile_body officers_body
    local profile_code officers_code
    local tmp

    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    profile_code=$(curl -sS --max-time 30 -u "${api_key}:" -w "%{http_code}" -o "$tmp" "$profile_url") || die "HTTP request failed for Companies House API"
    profile_body="$(cat "$tmp")"

    if [[ "$profile_code" != "200" ]]; then
        die "Companies House API returned HTTP ${profile_code}: ${profile_body}"
    fi

    # Fetch officers
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    officers_code=$(curl -sS --max-time 30 -u "${api_key}:" -w "%{http_code}" -o "$tmp" "$officers_url") || die "HTTP request failed for Companies House officers API"
    officers_body="$(cat "$tmp")"

    local officers_ok=false
    if [[ "$officers_code" == "200" ]]; then
        officers_ok=true
    fi

    # Parse profile
    local company_name company_status incorporation_date
    local address_line locality postal_code sic_codes

    company_name="$(echo "$profile_body" | jq -r '.company_name // "N/A"')"
    company_status="$(echo "$profile_body" | jq -r '.company_status // "N/A"')"
    incorporation_date="$(echo "$profile_body" | jq -r '.date_of_creation // "N/A"')"

    address_line="$(echo "$profile_body" | jq -r '.registered_office_address.address_line_1 // ""')"
    locality="$(echo "$profile_body" | jq -r '.registered_office_address.locality // ""')"
    postal_code="$(echo "$profile_body" | jq -r '.registered_office_address.postal_code // ""')"
    local address="${address_line}${address_line:+, }${locality}${locality:+, }${postal_code}"
    address="$(echo "$address" | sed 's/^[, ]*//; s/[, ]*$//')"
    [[ -z "$address" ]] && address="N/A"

    sic_codes="$(echo "$profile_body" | jq -r '.sic_codes // [] | join(", ")')"
    [[ -z "$sic_codes" ]] && sic_codes="N/A"

    # --json output
    if [[ "$json_output" == "true" ]]; then
        local officers_json="[]"
        if [[ "$officers_ok" == "true" ]]; then
            officers_json="$officers_body"
        fi
        echo "$profile_body" | jq \
            --argjson officers "$officers_json" \
            '{company: ., officers: $officers}'
        return 0
    fi

    # Output markdown
    echo "### Company Profile: ${company_name}"
    echo ""
    echo "| Field | Value |"
    echo "| --- | --- |"
    echo "| Company Number | ${company_number} |"
    echo "| Status | ${company_status} |"
    echo "| Incorporation Date | ${incorporation_date} |"
    echo "| Address | ${address} |"
    echo "| SIC Codes | ${sic_codes} |"
    echo ""

    if [[ "$officers_ok" == "true" ]]; then
        local officer_count
        officer_count="$(echo "$officers_body" | jq -r '.items | length')"
        if [[ "$officer_count" -gt 0 ]]; then
            echo "#### Officers (current)"
            echo ""
            echo "| Name | Role |"
            echo "| --- | --- |"
            local items
            items="$(echo "$officers_body" | jq -r '.items[] | [.name, .officer_role] | join(" | ")')"
            while IFS= read -r item; do
                echo "| ${item} |"
            done <<< "$items"
            echo ""
        else
            echo "*No officers listed.*"
            echo ""
        fi
    else
        echo "*Could not fetch officers list.*"
        echo ""
    fi

    echo "Source: ${profile_url}"
}

# ── whois ─────────────────────────────────────────────────────────────────────

whois_help() {
    cat <<EOF
Usage: ${SCRIPT_NAME} whois <domain> [--json]

Performs a WHOIS lookup for a domain.
Falls back to RDAP if the system whois command is unavailable.

Options:
  --json  Output JSON with registrar, creation_date, expiry_date, nameservers, and raw fields
EOF
}

cmd_whois() {
    # Check for help before consuming the positional arg
    for arg in "$@"; do
        if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
            whois_help
            exit 0
        fi
    done

    [[ $# -lt 1 ]] && die "whois: <domain> is required. Use --help for usage."

    local domain="$1"
    local json_output=false
    shift

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json) json_output=true; shift ;;
            *) die "Unknown flag: $1" ;;
        esac
    done

    if command -v whois &>/dev/null; then
        local raw
        raw="$(whois "$domain" 2>/dev/null)" || true

        if [[ -z "$raw" ]]; then
            # whois returned nothing; fall back to RDAP
            cmd_rdap_fallback "$domain" "$json_output"
            return 0
        fi

        # Extract fields (case-insensitive search)
        local registrar="N/A"
        local creation_date="N/A"
        local expiry_date="N/A"
        local name_servers="N/A"

        registrar="$(echo "$raw" | grep -i -m1 'Registrar:' | head -1 | sed 's/.*Registrar:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$registrar" ]] && registrar="N/A"

        creation_date="$(echo "$raw" | grep -i -m1 'Creation Date:' | head -1 | sed 's/.*Creation Date:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$creation_date" ]] && creation_date="$(echo "$raw" | grep -i -m1 'created:' | head -1 | sed 's/.*created:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$creation_date" ]] && creation_date="N/A"

        expiry_date="$(echo "$raw" | grep -i -m1 'Registry Expiry Date:' | head -1 | sed 's/.*Registry Expiry Date:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$expiry_date" ]] && expiry_date="$(echo "$raw" | grep -i -m1 'Expiry Date:' | head -1 | sed 's/.*Expiry Date:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$expiry_date" ]] && expiry_date="$(echo "$raw" | grep -i -m1 'expires:' | head -1 | sed 's/.*expires:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [[ -z "$expiry_date" ]] && expiry_date="N/A"

        name_servers="$(echo "$raw" | grep -i 'Name Server:' | sed 's/.*Name Server:\s*//I' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr '\n' ', ' | sed 's/, $//')"
        [[ -z "$name_servers" ]] && name_servers="N/A"

        if [[ "$json_output" == "true" ]]; then
            echo "$(jq -n \
                --arg registrar "$registrar" \
                --arg creation_date "$creation_date" \
                --arg expiry_date "$expiry_date" \
                --arg nameservers "$name_servers" \
                --arg raw "$raw" \
                '{registrar: $registrar, creation_date: $creation_date, expiry_date: $expiry_date, nameservers: $nameservers, raw: $raw}')"
            return 0
        fi

        echo "### WHOIS: ${domain}"
        echo ""
        echo "| Field | Value |"
        echo "| --- | --- |"
        echo "| Registrar | ${registrar} |"
        echo "| Creation Date | ${creation_date} |"
        echo "| Expiry Date | ${expiry_date} |"
        echo "| Name Servers | ${name_servers} |"
        echo ""
        echo "Source: whois ${domain}"
    else
        cmd_rdap_fallback "$domain" "$json_output"
    fi
}

# Fallback from whois subcommand to RDAP
cmd_rdap_fallback() {
    local domain="$1"
    local json_output="${2:-false}"

    local rdap_url="https://rdap.org/domain/${domain}"
    local http_code body tmp
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    http_code=$(curl -sS --max-time 30 -w "%{http_code}" -o "$tmp" "$rdap_url") || die "RDAP request failed for: ${domain}"
    body="$(cat "$tmp")"

    if [[ "$http_code" != "200" ]]; then
        die "RDAP returned HTTP ${http_code}: ${body}"
    fi

    local ldh_name
    ldh_name="$(echo "$body" | jq -r '.ldhName // "N/A"')"

    # Extract events
    local registration_date="N/A"
    local expiration_date="N/A"
    local events
    events="$(echo "$body" | jq -r '.events[]? | [.eventAction, .eventDate] | @tsv' 2>/dev/null)" || true
    while IFS=$'\t' read -r action date_str; do
        case "$action" in
            registration) registration_date="$date_str" ;;
            expiration)   expiration_date="$date_str" ;;
        esac
    done <<< "$events"

    # Nameservers
    local nameservers
    nameservers="$(echo "$body" | jq -r '.nameservers[]?.ldhName // empty' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')"
    [[ -z "$nameservers" ]] && nameservers="N/A"

    # Status
    local status
    status="$(echo "$body" | jq -r '.status[]? // empty' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')"
    [[ -z "$status" ]] && status="N/A"

    if [[ "$json_output" == "true" ]]; then
        echo "$(jq -n \
            --arg registrar "N/A" \
            --arg creation_date "$registration_date" \
            --arg expiry_date "$expiration_date" \
            --arg nameservers "$nameservers" \
            --arg raw "$body" \
            '{registrar: $registrar, creation_date: $creation_date, expiry_date: $expiry_date, nameservers: $nameservers, raw: $raw}')"
        return 0
    fi

    echo "*whois command not available; falling back to RDAP lookup.*"
    echo ""
    echo "### RDAP: ${domain}"
    echo ""
    echo "| Field | Value |"
    echo "| --- | --- |"
    echo "| Domain Name | ${ldh_name} |"
    echo "| Registration Date | ${registration_date} |"
    echo "| Expiration Date | ${expiration_date} |"
    echo "| Name Servers | ${nameservers} |"
    echo "| Status | ${status} |"
    echo ""
    echo "Source: ${rdap_url}"
}

# ── rdap ──────────────────────────────────────────────────────────────────────

rdap_help() {
    cat <<EOF
Usage: ${SCRIPT_NAME} rdap <domain> [--json]

Perform a direct RDAP lookup for a domain (skips system whois).

Options:
  --json  Output raw JSON as-is
EOF
}

cmd_rdap() {
    # Check for help before consuming the positional arg
    for arg in "$@"; do
        if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
            rdap_help
            exit 0
        fi
    done

    [[ $# -lt 1 ]] && die "rdap: <domain> is required. Use --help for usage."

    local domain="$1"
    local json_output=false
    shift

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json) json_output=true; shift ;;
            *) die "Unknown flag: $1" ;;
        esac
    done

    local rdap_url="https://rdap.org/domain/${domain}"
    local http_code body tmp
    tmp="$(mktemp)"
    TEMP_FILES+=("$tmp")
    http_code=$(curl -sS --max-time 30 -w "%{http_code}" -o "$tmp" "$rdap_url") || die "RDAP request failed for: ${domain}"
    body="$(cat "$tmp")"

    if [[ "$http_code" != "200" ]]; then
        die "RDAP returned HTTP ${http_code}: ${body}"
    fi

    if [[ "$json_output" == "true" ]]; then
        echo "$body"
        return 0
    fi

    local ldh_name
    ldh_name="$(echo "$body" | jq -r '.ldhName // "N/A"')"

    # Events
    local registration_date="N/A"
    local expiration_date="N/A"
    local events
    events="$(echo "$body" | jq -r '.events[]? | [.eventAction, .eventDate] | @tsv' 2>/dev/null)" || true
    while IFS=$'\t' read -r action date_str; do
        case "$action" in
            registration) registration_date="$date_str" ;;
            expiration)   expiration_date="$date_str" ;;
        esac
    done <<< "$events"

    # Nameservers
    local nameservers
    nameservers="$(echo "$body" | jq -r '.nameservers[]?.ldhName // empty' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')"
    [[ -z "$nameservers" ]] && nameservers="N/A"

    # Status
    local status
    status="$(echo "$body" | jq -r '.status[]? // empty' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')"
    [[ -z "$status" ]] && status="N/A"

    echo "### RDAP: ${domain}"
    echo ""
    echo "| Field | Value |"
    echo "| --- | --- |"
    echo "| Domain Name | ${ldh_name} |"
    echo "| Registration Date | ${registration_date} |"
    echo "| Expiration Date | ${expiration_date} |"
    echo "| Name Servers | ${nameservers} |"
    echo "| Status | ${status} |"
    echo ""
    echo "Source: ${rdap_url}"
}

# ── Main dispatch ─────────────────────────────────────────────────────────────

main() {
    trap cleanup EXIT
    [[ $# -eq 0 ]] && { usage >&2; exit 1; }

    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --version)
            echo "${VERSION}"
            exit 0
            ;;
        wayback)
            shift
            cmd_wayback "$@"
            ;;
        companies-house)
            shift
            cmd_companies_house "$@"
            ;;
        whois)
            shift
            cmd_whois "$@"
            ;;
        rdap)
            shift
            cmd_rdap "$@"
            ;;
        *)
            echo "Error: Unknown subcommand '$1'" >&2
            echo "" >&2
            usage >&2
            exit 1
            ;;
    esac
}

# Only run main when executed directly, not when sourced
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
