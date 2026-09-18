/*
  Apply all incremental migrations to an existing LegalRentAI database.
  Safe to re-run (idempotent). Fresh installs: run ddl.sql first, then this script.

  From repo root:
    sqlcmd -S localhost -E -d LegalRentAI -b -i "docs\database\migrations\run-all-incremental.sql"

  Or use: apply_migrations.bat
*/

USE LegalRentAI;
GO

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT '=== Legal Rent AI — incremental migrations ===';
GO

:r 01-add-file-content.sql
:r 02-add-text-extraction.sql
:r 03-add-analysis-statuses.sql
:r 04-add-analysis-perspective.sql
:r 05-review-messages.sql
:r 06-review-message-read-cursors.sql
:r 06-document-text-edits.sql
:r 07-contract-closure-notes.sql
:r 07-lawyer-revision-document.sql
:r 08-add-analysis-document-scope.sql
:r 09-findings-confidence.sql
:r 10-chat-llm-observability.sql

PRINT '=== Incremental migrations finished ===';
GO
