/* Client–lawyer review communication (RF-50, RF-51) — persisted messages, no email */

IF OBJECT_ID(N'app.review_messages', N'U') IS NULL
BEGIN
    CREATE TABLE app.review_messages (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_review_messages_id DEFAULT NEWSEQUENTIALID(),
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        user_id         UNIQUEIDENTIFIER NOT NULL,
        content         NVARCHAR(MAX)    NOT NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_review_messages_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_review_messages PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_review_messages_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT FK_review_messages_user_id FOREIGN KEY (user_id) REFERENCES app.users (id)
    );

    CREATE NONCLUSTERED INDEX IX_review_messages_analysis_id ON app.review_messages (analysis_id);
END
GO
