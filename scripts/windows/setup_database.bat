@echo off
setlocal

echo ============================================
echo  Legal Rent AI - Database Setup
echo ============================================
echo.

set "ROOT=%~dp0..\.."
set "DB_DIR=%ROOT%\docs\database"
set "SERVER=localhost"

echo Server: %SERVER%
echo.

echo [1/5] Creating database LegalRentAI...
sqlcmd -S %SERVER% -E -b -i "%DB_DIR%\00-create-database.sql"
if errorlevel 1 goto :error

echo.
echo [2/5] Creating schema and tables...
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "%DB_DIR%\ddl.sql"
if errorlevel 1 goto :error

echo.
echo [3/5] Seeding demo users...
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "%DB_DIR%\seed.sql"
if errorlevel 1 goto :error

echo.
echo [4/5] Applying incremental migrations...
pushd "%DB_DIR%\migrations"
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "run-all-incremental.sql"
if errorlevel 1 goto :error
popd

echo.
echo [5/5] Legacy role catalog fix (no-op on fresh ddl.sql)...
sqlcmd -S %SERVER% -E -b -d LegalRentAI -i "%DB_DIR%\migrations\12-migrate-remove-administrator.sql"
if errorlevel 1 goto :error

echo.
echo ============================================
echo  Setup complete!
echo  Database: LegalRentAI
echo  Schema:   app (22 tables)
echo  Open SSMS and refresh Object Explorer.
echo ============================================
goto :end

:error
echo.
echo ERROR: Database setup failed.
exit /b 1

:end
endlocal
