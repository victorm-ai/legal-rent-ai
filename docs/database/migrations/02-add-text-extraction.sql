/*
  Migration 02 — Persist extracted document text (RF-06, RF-07)
  Run after ddl.sql on existing LegalRentAI databases.
*/

USE LegalRentAI;
GO

IF COL_LENGTH('app.contract_documents', 'extracted_text') IS NULL
BEGIN
    ALTER TABLE app.contract_documents
        ADD extracted_text NVARCHAR(MAX) NULL;
    PRINT 'Added column app.contract_documents.extracted_text';
END
GO

IF COL_LENGTH('app.contract_documents', 'extraction_method') IS NULL
BEGIN
    ALTER TABLE app.contract_documents
        ADD extraction_method NVARCHAR(32) NULL;
    PRINT 'Added column app.contract_documents.extraction_method';
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = N'CK_contract_documents_extraction_method'
)
BEGIN
    ALTER TABLE app.contract_documents
        ADD CONSTRAINT CK_contract_documents_extraction_method
            CHECK (
                extraction_method IS NULL
                OR extraction_method IN (N'native', N'ocr', N'none')
            );
    PRINT 'Added constraint CK_contract_documents_extraction_method';
END
GO

PRINT 'Migration 02 completed.';
GO
