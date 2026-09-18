/* Separate analyses for original contract vs lawyer-edited revision */

IF COL_LENGTH('app.analyses', 'document_scope') IS NULL
BEGIN
    ALTER TABLE app.analyses
        ADD document_scope NVARCHAR(32) NOT NULL
            CONSTRAINT DF_analyses_document_scope DEFAULT (N'original');
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = N'CK_analyses_document_scope'
)
BEGIN
    ALTER TABLE app.analyses
        ADD CONSTRAINT CK_analyses_document_scope CHECK (
            document_scope IN (N'original', N'lawyer_revision')
        );
END
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'UX_analyses_contract_perspective'
      AND object_id = OBJECT_ID(N'app.analyses')
)
BEGIN
    DROP INDEX UX_analyses_contract_perspective ON app.analyses;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'UX_analyses_contract_perspective_scope'
      AND object_id = OBJECT_ID(N'app.analyses')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_analyses_contract_perspective_scope
        ON app.analyses (contract_id, perspective, document_scope)
        WHERE status <> N'failed';
END
GO
