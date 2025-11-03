#!/usr/bin/env bash
set -euo pipefail

# Determine repo root (directory containing this script is scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_PATH="${REPO_DIR}/bin/hiper"

if [[ ! -f "${BIN_PATH}" ]]; then
  echo "Error: ${BIN_PATH} not found." >&2
  exit 1
fi

# Ensure executable
chmod +x "${BIN_PATH}"
echo "Made executable: ${BIN_PATH}"

# Compute PATH entry, prefer $HOME form if applicable
HOME_PREFIX="${HOME}"
EXPORT_PATH="${REPO_DIR}/bin"
if [[ "${EXPORT_PATH}" == ${HOME_PREFIX}/* ]]; then
  EXPORT_PATH="${EXPORT_PATH/${HOME}/$HOME}"
fi

BASHRC_FILE="${HOME}/.bashrc"
LINE="export PATH=\"${EXPORT_PATH}:\$PATH\""

# Append to ~/.bashrc if not already present
if [[ -f "${BASHRC_FILE}" ]] && grep -Fq "${EXPORT_PATH}" "${BASHRC_FILE}"; then
  echo "PATH already contains ${EXPORT_PATH} in ${BASHRC_FILE}"
else
  echo "${LINE}" >> "${BASHRC_FILE}"
  echo "Appended PATH update to ${BASHRC_FILE}:"
  echo "  ${LINE}"
fi

cat <<EOF

Installation complete.

To use immediately in this shell, run:
  source "${BASHRC_FILE}"

Then verify:
  hiper --help
EOF


