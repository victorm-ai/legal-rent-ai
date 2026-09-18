/* Allow persisted lawyer edits in extracted_text metadata */

IF OBJECT_ID(N'app.contract_documents', N'U') IS NOT NULL
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE name = N'CK_contract_documents_extraction_method'
          AND parent_object_id = OBJECT_ID(N'app.contract_documents')
    )
    BEGIN
        ALTER TABLE app.contract_documents
            DROP CONSTRAINT CK_contract_documents_extraction_method;
    END

    ALTER TABLE app.contract_documents
        ADD CONSTRAINT CK_contract_documents_extraction_method CHECK (
            extraction_method IS NULL
            OR extraction_method IN (N'native', N'ocr', N'none', N'edited')
        );
END
GO
