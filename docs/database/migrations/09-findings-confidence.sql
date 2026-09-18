/*
  Migration 09 — confidence on findings (RNF-13). Idempotent.
*/

USE LegalRentAI;
GO

IF COL_LENGTH('app.findings', 'confidence') IS NULL
BEGIN
    ALTER TABLE app.findings ADD confidence DECIMAL(5,4) NULL;
    PRINT 'Added column app.findings.confidence';
END
GO

PRINT 'Migration 09 completed.';
GO
