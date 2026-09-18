/*
  Chat LLM observability events (structlog + SQL audit trail).
  Idempotent — safe to re-run.
*/
IF OBJECT_ID(N'app.chat_llm_call_events', N'U') IS NULL
BEGIN
    CREATE TABLE app.chat_llm_call_events (
        id                  UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_chat_llm_call_events_id DEFAULT NEWSEQUENTIALID(),
        request_id          NVARCHAR(64)     NOT NULL,
        chat_session_id     UNIQUEIDENTIFIER NOT NULL,
        event               NVARCHAR(40)     NOT NULL,
        provider            NVARCHAR(100)    NOT NULL,
        model               NVARCHAR(200)    NOT NULL,
        tokens_in           INT              NULL,
        tokens_out          INT              NULL,
        cost_usd            DECIMAL(12, 6)   NULL,
        latency_ms          INT              NULL,
        cache_hit           BIT              NOT NULL CONSTRAINT DF_chat_llm_call_events_cache_hit DEFAULT (0),
        fallback_used       BIT              NOT NULL CONSTRAINT DF_chat_llm_call_events_fallback_used DEFAULT (0),
        fallback_provider   NVARCHAR(100)    NULL,
        finish_reason       NVARCHAR(50)     NULL,
        error_type          NVARCHAR(200)    NULL,
        error_message       NVARCHAR(MAX)    NULL,
        retry_count         INT              NOT NULL CONSTRAINT DF_chat_llm_call_events_retry_count DEFAULT (0),
        stream              BIT              NOT NULL CONSTRAINT DF_chat_llm_call_events_stream DEFAULT (0),
        payload_json        NVARCHAR(MAX)    NOT NULL,
        created_at          DATETIME2(3)     NOT NULL CONSTRAINT DF_chat_llm_call_events_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_chat_llm_call_events PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_chat_llm_call_events_session_id FOREIGN KEY (chat_session_id) REFERENCES app.chat_sessions (id),
        CONSTRAINT CK_chat_llm_call_events_event CHECK (
            event IN (N'llm_call_started', N'llm_call_completed', N'llm_call_failed')
        )
    );

    CREATE NONCLUSTERED INDEX IX_chat_llm_call_events_session_id
        ON app.chat_llm_call_events (chat_session_id, created_at DESC);

    CREATE NONCLUSTERED INDEX IX_chat_llm_call_events_request_id
        ON app.chat_llm_call_events (request_id, created_at);
END
GO
