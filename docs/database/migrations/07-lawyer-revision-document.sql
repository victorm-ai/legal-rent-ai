/* Lawyer-edited contract revision (single replaceable document per contract) */

IF OBJECT_ID(N'app.contract_documents', N'U') IS NOT NULL
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE name = N'CK_contract_documents_type'
          AND parent_object_id = OBJECT_ID(N'app.contract_documents')
    )
    BEGIN
        ALTER TABLE app.contract_documents
            DROP CONSTRAINT CK_contract_documents_type;
    END

    ALTER TABLE app.contract_documents
        ADD CONSTRAINT CK_contract_documents_type CHECK (
            document_type IN (N'main_contract', N'annex', N'other', N'lawyer_revision')
        );
END
GO
