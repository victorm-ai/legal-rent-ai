/*
  Migration 01: Store document binary content in database (RF-03/RF-05)
  Run against LegalRentAI after initial ddl.sql.
*/

USE LegalRentAI;
GO

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

IF COL_LENGTH('app.contract_documents', 'file_content') IS NULL
BEGIN
    ALTER TABLE app.contract_documents
        ADD file_content VARBINARY(MAX) NULL;
    PRINT 'Added column app.contract_documents.file_content';
END
GO

IF COL_LENGTH('app.contract_documents', 'storage_path') IS NOT NULL
BEGIN
    ALTER TABLE app.contract_documents
        DROP COLUMN storage_path;
    PRINT 'Dropped column app.contract_documents.storage_path';
END
GO

IF COL_LENGTH('app.contract_documents', 'file_content') IS NOT NULL
BEGIN
    ALTER TABLE app.contract_documents
        ALTER COLUMN file_content VARBINARY(MAX) NOT NULL;
    PRINT 'Set app.contract_documents.file_content as NOT NULL';
END
GO

PRINT 'Migration 01 completed.';
GO
