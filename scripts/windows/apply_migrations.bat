@echo off
setlocal

echo ============================================
echo  Legal Rent AI - Apply DB Migrations
echo ============================================
echo.

set "ROOT=%~dp0..\.."
set "MIG_DIR=%ROOT%\docs\database\migrations"
set "SERVER=localhost"

if not "%~1"=="" set "SERVER=%~1"

echo Server: %SERVER%
echo Database: LegalRentAI
echo.

pushd "%MIG_DIR%"

echo Applying incremental migrations (idempotent)...
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "run-all-incremental.sql"
if errorlevel 1 goto :error

echo.
echo Applying role catalog fix (only if legacy administrator role exists)...
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "12-migrate-remove-administrator.sql"
if errorlevel 1 goto :error

popd

echo.
echo ============================================
echo  Migrations complete.
echo ============================================
goto :end

:error
popd 2>nul
echo.
echo ERROR: Migration failed.
exit /b 1

:end
endlocal
