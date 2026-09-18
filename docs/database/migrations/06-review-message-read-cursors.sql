/*
  Per-user read cursors for client–lawyer review chat notifications.
  Run once against LegalRentAI if the table is missing.
*/

USE LegalRentAI;
GO

IF OBJECT_ID(N'app.review_message_read_cursors', N'U') IS NULL
BEGIN
    CREATE TABLE app.review_message_read_cursors (
        user_id         UNIQUEIDENTIFIER NOT NULL,
        contract_id     UNIQUEIDENTIFIER NOT NULL,
        last_read_at    DATETIME2(3)     NOT NULL CONSTRAINT DF_review_message_read_cursors_last_read_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_review_message_read_cursors PRIMARY KEY CLUSTERED (user_id, contract_id),
        CONSTRAINT FK_review_message_read_cursors_user_id FOREIGN KEY (user_id) REFERENCES app.users (id),
        CONSTRAINT FK_review_message_read_cursors_contract_id FOREIGN KEY (contract_id) REFERENCES app.contracts (id)
    );
    PRINT 'Created app.review_message_read_cursors';
END
GO
