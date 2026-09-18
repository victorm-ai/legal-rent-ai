/*
  Migration 03 — Add processing/failed analysis statuses (RF-52)
*/

USE LegalRentAI;
GO

IF EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = N'CK_analyses_status'
)
BEGIN
    ALTER TABLE app.analyses DROP CONSTRAINT CK_analyses_status;
END
GO

ALTER TABLE app.analyses
    ADD CONSTRAINT CK_analyses_status CHECK (status IN (
        N'processing', N'ai_generated', N'pending_review', N'reviewed', N'approved', N'failed'
    ));
GO

PRINT 'Migration 03 completed.';
GO
