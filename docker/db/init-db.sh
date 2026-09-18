#!/usr/bin/env bash
set -euo pipefail

: "${MSSQL_HOST:=sqlserver}"
: "${MSSQL_SA_PASSWORD:?MSSQL_SA_PASSWORD is required}"

SCRIPTS="/scripts"

if [[ -x /opt/mssql-tools18/bin/sqlcmd ]]; then
  SQLCMD="/opt/mssql-tools18/bin/sqlcmd"
elif [[ -x /opt/mssql-tools/bin/sqlcmd ]]; then
  SQLCMD="/opt/mssql-tools/bin/sqlcmd"
else
  echo "sqlcmd not found in SQL Server image."
  exit 1
fi

echo "Waiting for SQL Server at ${MSSQL_HOST}..."
for i in $(seq 1 60); do
  if "${SQLCMD}" -S "${MSSQL_HOST}" -U sa -P "${MSSQL_SA_PASSWORD}" -C -Q "SELECT 1" &>/dev/null; then
    echo "SQL Server is ready."
    break
  fi
  if [[ "${i}" -eq 60 ]]; then
    echo "SQL Server did not become ready in time."
    exit 1
  fi
  sleep 2
done

run_sql() {
  local db_flag=()
  local file
  if [[ $# -eq 2 ]]; then
    if [[ -n "$1" ]]; then
      db_flag=(-d "$1")
    fi
    file="$2"
  else
    file="$1"
  fi
  if [[ -z "${file}" || ! -f "${file}" ]]; then
    echo "SQL script not found: ${file}"
    exit 1
  fi
  echo "Running $(basename "${file}")..."
  "${SQLCMD}" -S "${MSSQL_HOST}" -U sa -P "${MSSQL_SA_PASSWORD}" -C "${db_flag[@]}" -b -i "${file}"
}

run_sql_cwd() {
  local db="$1"
  local dir="$2"
  local script="$3"
  local db_flag=()
  if [[ -n "${db}" ]]; then
    db_flag=(-d "${db}")
  fi
  if [[ ! -f "${dir}/${script}" ]]; then
    echo "SQL script not found: ${dir}/${script}"
    exit 1
  fi
  echo "Running ${script} (cwd ${dir})..."
  (
    cd "${dir}"
    "${SQLCMD}" -S "${MSSQL_HOST}" -U sa -P "${MSSQL_SA_PASSWORD}" -C "${db_flag[@]}" -b -i "${script}"
  )
}

run_sql "" "${SCRIPTS}/00-create-database.sql"
run_sql "LegalRentAI" "${SCRIPTS}/ddl.sql"
run_sql "LegalRentAI" "${SCRIPTS}/seed.sql"
run_sql_cwd "LegalRentAI" "${SCRIPTS}/migrations" "run-all-incremental.sql"
run_sql "LegalRentAI" "${SCRIPTS}/migrations/12-migrate-remove-administrator.sql"

echo "Database initialization complete."
