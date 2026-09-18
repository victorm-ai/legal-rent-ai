/*
  Legal Rent AI - Database DDL
  Target: Microsoft SQL Server 2019+ / Azure SQL Database
  Run in order. Creates schema [app] and all MVP tables.
*/

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'app')
    EXEC('CREATE SCHEMA [app]');
GO

/* ============================================================
   Catalog tables
   ============================================================ */

IF OBJECT_ID(N'app.roles', N'U') IS NULL
BEGIN
    CREATE TABLE app.roles (
        id          TINYINT         NOT NULL,
        code        NVARCHAR(32)    NOT NULL,
        name        NVARCHAR(100)   NOT NULL,
        CONSTRAINT PK_roles PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_roles_code UNIQUE (code)
    );

    INSERT INTO app.roles (id, code, name) VALUES
        (1, N'lawyer', N'Lawyer'),
        (2, N'client', N'Client');
END
GO

/* ============================================================
   Users
   ============================================================ */

IF OBJECT_ID(N'app.users', N'U') IS NULL
BEGIN
    CREATE TABLE app.users (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_users_id DEFAULT NEWSEQUENTIALID(),
        email           NVARCHAR(320)    NOT NULL,
        name            NVARCHAR(200)    NOT NULL,
        role_id         TINYINT          NOT NULL,
        password_hash   NVARCHAR(128)    NOT NULL,
        password_salt   NVARCHAR(64)     NOT NULL,
        is_active       BIT              NOT NULL CONSTRAINT DF_users_is_active DEFAULT (1),
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_users_created_at DEFAULT (SYSUTCDATETIME()),
        updated_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_users_updated_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_users PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_users_email UNIQUE (email),
        CONSTRAINT FK_users_role_id FOREIGN KEY (role_id) REFERENCES app.roles (id)
    );

    CREATE NONCLUSTERED INDEX IX_users_role_id ON app.users (role_id);
END
GO

/* ============================================================
   Contracts
   ============================================================ */

IF OBJECT_ID(N'app.contracts', N'U') IS NULL
BEGIN
    CREATE TABLE app.contracts (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_contracts_id DEFAULT NEWSEQUENTIALID(),
        user_id         UNIQUEIDENTIFIER NOT NULL,
        perspective     NVARCHAR(32)     NOT NULL,
        jurisdiction    NVARCHAR(100)    NULL,
        status          NVARCHAR(32)     NOT NULL,
        title           NVARCHAR(300)    NULL,
        closure_notes   NVARCHAR(MAX)    NULL,
        is_deleted      BIT              NOT NULL CONSTRAINT DF_contracts_is_deleted DEFAULT (0),
        deleted_at      DATETIME2(3)     NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_contracts_created_at DEFAULT (SYSUTCDATETIME()),
        updated_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_contracts_updated_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_contracts PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_contracts_user_id FOREIGN KEY (user_id) REFERENCES app.users (id),
        CONSTRAINT CK_contracts_perspective CHECK (perspective IN (N'landlord', N'tenant', N'neutral')),
        CONSTRAINT CK_contracts_status CHECK (status IN (
            N'draft', N'in_review', N'approved', N'in_signing', N'signed', N'expired', N'terminated'
        ))
    );

    CREATE NONCLUSTERED INDEX IX_contracts_user_id ON app.contracts (user_id);
    CREATE NONCLUSTERED INDEX IX_contracts_status ON app.contracts (status) WHERE is_deleted = 0;
    CREATE NONCLUSTERED INDEX IX_contracts_created_at ON app.contracts (created_at DESC);
END
GO

IF OBJECT_ID(N'app.contract_documents', N'U') IS NULL
BEGIN
    CREATE TABLE app.contract_documents (
        id                  UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_contract_documents_id DEFAULT NEWSEQUENTIALID(),
        contract_id         UNIQUEIDENTIFIER NOT NULL,
        file_name           NVARCHAR(255)    NOT NULL,
        file_content        VARBINARY(MAX)   NOT NULL,
        file_size_bytes     BIGINT           NOT NULL,
        page_count          INT              NULL,
        document_type       NVARCHAR(50)     NOT NULL,
        mime_type           NVARCHAR(100)    NULL,
        is_signed_version   BIT              NOT NULL CONSTRAINT DF_contract_documents_is_signed DEFAULT (0),
        is_deleted          BIT              NOT NULL CONSTRAINT DF_contract_documents_is_deleted DEFAULT (0),
        extracted_text      NVARCHAR(MAX)    NULL,
        extraction_method   NVARCHAR(32)     NULL,
        uploaded_at         DATETIME2(3)     NOT NULL CONSTRAINT DF_contract_documents_uploaded_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_contract_documents PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_contract_documents_contract_id FOREIGN KEY (contract_id) REFERENCES app.contracts (id),
        CONSTRAINT CK_contract_documents_type CHECK (
            document_type IN (N'main_contract', N'annex', N'other', N'lawyer_revision')
        ),
        CONSTRAINT CK_contract_documents_extraction_method CHECK (
            extraction_method IS NULL OR extraction_method IN (N'native', N'ocr', N'none', N'edited')
        )
    );

    CREATE NONCLUSTERED INDEX IX_contract_documents_contract_id ON app.contract_documents (contract_id);
END
GO

IF OBJECT_ID(N'app.contract_parties', N'U') IS NULL
BEGIN
    CREATE TABLE app.contract_parties (
        id                      UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_contract_parties_id DEFAULT NEWSEQUENTIALID(),
        contract_id             UNIQUEIDENTIFIER NOT NULL,
        party_type              NVARCHAR(50)     NOT NULL,
        name                    NVARCHAR(300)    NULL,
        legal_representative    NVARCHAR(300)    NULL,
        address                 NVARCHAR(500)    NULL,
        confidence              DECIMAL(5,4)     NULL,
        source_page             INT              NULL,
        CONSTRAINT PK_contract_parties PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_contract_parties_contract_id FOREIGN KEY (contract_id) REFERENCES app.contracts (id)
    );

    CREATE NONCLUSTERED INDEX IX_contract_parties_contract_id ON app.contract_parties (contract_id);
END
GO

/* ============================================================
   Analysis
   ============================================================ */

IF OBJECT_ID(N'app.analyses', N'U') IS NULL
BEGIN
    CREATE TABLE app.analyses (
        id                  UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_analyses_id DEFAULT NEWSEQUENTIALID(),
        contract_id         UNIQUEIDENTIFIER NOT NULL,
        perspective         NVARCHAR(32)     NOT NULL,
        document_scope      NVARCHAR(32)     NOT NULL CONSTRAINT DF_analyses_document_scope DEFAULT (N'original'),
        status              NVARCHAR(32)     NOT NULL,
        summary_executive   NVARCHAR(MAX)    NULL,
        general_risk        NVARCHAR(16)     NULL,
        started_at          DATETIME2(3)     NULL,
        completed_at        DATETIME2(3)     NULL,
        created_at          DATETIME2(3)     NOT NULL CONSTRAINT DF_analyses_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_analyses PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_analyses_contract_id FOREIGN KEY (contract_id) REFERENCES app.contracts (id),
        CONSTRAINT CK_analyses_perspective CHECK (perspective IN (N'landlord', N'tenant', N'neutral')),
        CONSTRAINT CK_analyses_document_scope CHECK (document_scope IN (N'original', N'lawyer_revision')),
        CONSTRAINT CK_analyses_status CHECK (status IN (
            N'processing', N'ai_generated', N'pending_review', N'reviewed', N'approved', N'failed'
        )),
        CONSTRAINT CK_analyses_general_risk CHECK (
            general_risk IS NULL OR general_risk IN (N'low', N'medium', N'high')
        )
    );

    CREATE NONCLUSTERED INDEX IX_analyses_contract_id ON app.analyses (contract_id);
    CREATE NONCLUSTERED INDEX IX_analyses_status ON app.analyses (status);
    CREATE NONCLUSTERED INDEX IX_analyses_created_at ON app.analyses (created_at DESC);
    CREATE UNIQUE NONCLUSTERED INDEX UX_analyses_contract_perspective_scope
        ON app.analyses (contract_id, perspective, document_scope)
        WHERE status <> N'failed';
END
GO

IF OBJECT_ID(N'app.analysis_llm_runs', N'U') IS NULL
BEGIN
    CREATE TABLE app.analysis_llm_runs (
        id                      UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_analysis_llm_runs_id DEFAULT NEWSEQUENTIALID(),
        analysis_id             UNIQUEIDENTIFIER NOT NULL,
        provider                NVARCHAR(100)    NOT NULL,
        model                   NVARCHAR(100)    NOT NULL,
        model_version           NVARCHAR(50)     NULL,
        prompt_id               NVARCHAR(100)    NULL,
        response_storage_path   NVARCHAR(500)    NULL,
        tokens_input            INT              NULL,
        tokens_output           INT              NULL,
        duration_ms             INT              NULL,
        created_at              DATETIME2(3)     NOT NULL CONSTRAINT DF_analysis_llm_runs_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_analysis_llm_runs PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_analysis_llm_runs_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id)
    );

    CREATE NONCLUSTERED INDEX IX_analysis_llm_runs_analysis_id ON app.analysis_llm_runs (analysis_id);
END
GO

IF OBJECT_ID(N'app.extracted_fields', N'U') IS NULL
BEGIN
    CREATE TABLE app.extracted_fields (
        id                  UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_extracted_fields_id DEFAULT NEWSEQUENTIALID(),
        analysis_id         UNIQUEIDENTIFIER NOT NULL,
        field_name          NVARCHAR(100)    NOT NULL,
        field_value         NVARCHAR(MAX)    NULL,
        confidence          DECIMAL(5,4)     NOT NULL,
        source_page         INT              NULL,
        source_clause       NVARCHAR(200)    NULL,
        source_section      NVARCHAR(200)    NULL,
        source_text_snippet NVARCHAR(MAX)    NULL,
        CONSTRAINT PK_extracted_fields PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_extracted_fields_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT CK_extracted_fields_confidence CHECK (confidence >= 0 AND confidence <= 1)
    );

    CREATE NONCLUSTERED INDEX IX_extracted_fields_analysis_id ON app.extracted_fields (analysis_id);
    CREATE NONCLUSTERED INDEX IX_extracted_fields_field_name ON app.extracted_fields (field_name);
END
GO

IF OBJECT_ID(N'app.clauses', N'U') IS NULL
BEGIN
    CREATE TABLE app.clauses (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_clauses_id DEFAULT NEWSEQUENTIALID(),
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        category        NVARCHAR(100)    NOT NULL,
        text            NVARCHAR(MAX)    NOT NULL,
        section         NVARCHAR(200)    NULL,
        page            INT              NULL,
        confidence      DECIMAL(5,4)     NOT NULL,
        CONSTRAINT PK_clauses PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_clauses_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT CK_clauses_confidence CHECK (confidence >= 0 AND confidence <= 1)
    );

    CREATE NONCLUSTERED INDEX IX_clauses_analysis_id ON app.clauses (analysis_id);
END
GO

IF OBJECT_ID(N'app.findings', N'U') IS NULL
BEGIN
    CREATE TABLE app.findings (
        id                  UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_findings_id DEFAULT NEWSEQUENTIALID(),
        analysis_id         UNIQUEIDENTIFIER NOT NULL,
        clause_id           UNIQUEIDENTIFIER NULL,
        finding_type        NVARCHAR(50)     NOT NULL,
        severity            NVARCHAR(16)     NOT NULL,
        title               NVARCHAR(300)    NOT NULL,
        description         NVARCHAR(MAX)    NOT NULL,
        legal_basis         NVARCHAR(MAX)    NULL,
        source_law          NVARCHAR(500)    NULL,
        evidence_text       NVARCHAR(MAX)    NULL,
        evidence_page       INT              NULL,
        recommendation      NVARCHAR(MAX)    NULL,
        suggested_rewording NVARCHAR(MAX)    NULL,
        sort_order          INT              NOT NULL CONSTRAINT DF_findings_sort_order DEFAULT (0),
        confidence          DECIMAL(5,4)     NULL,
        CONSTRAINT PK_findings PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_findings_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT FK_findings_clause_id FOREIGN KEY (clause_id) REFERENCES app.clauses (id),
        CONSTRAINT CK_findings_severity CHECK (severity IN (N'low', N'medium', N'high'))
    );

    CREATE NONCLUSTERED INDEX IX_findings_analysis_id ON app.findings (analysis_id);
    CREATE NONCLUSTERED INDEX IX_findings_severity ON app.findings (severity);
END
GO

IF OBJECT_ID(N'app.legal_citations', N'U') IS NULL
BEGIN
    CREATE TABLE app.legal_citations (
        id          UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_legal_citations_id DEFAULT NEWSEQUENTIALID(),
        finding_id  UNIQUEIDENTIFIER NOT NULL,
        law_code    NVARCHAR(100)    NOT NULL,
        article     NVARCHAR(100)    NULL,
        excerpt     NVARCHAR(MAX)    NULL,
        source_uri  NVARCHAR(500)    NULL,
        CONSTRAINT PK_legal_citations PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_legal_citations_finding_id FOREIGN KEY (finding_id) REFERENCES app.findings (id)
    );

    CREATE NONCLUSTERED INDEX IX_legal_citations_finding_id ON app.legal_citations (finding_id);
END
GO

/* ============================================================
   Chat
   ============================================================ */

IF OBJECT_ID(N'app.chat_sessions', N'U') IS NULL
BEGIN
    CREATE TABLE app.chat_sessions (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_chat_sessions_id DEFAULT NEWSEQUENTIALID(),
        contract_id     UNIQUEIDENTIFIER NOT NULL,
        user_id         UNIQUEIDENTIFIER NOT NULL,
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_chat_sessions_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_chat_sessions PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_chat_sessions_contract_id FOREIGN KEY (contract_id) REFERENCES app.contracts (id),
        CONSTRAINT FK_chat_sessions_user_id FOREIGN KEY (user_id) REFERENCES app.users (id),
        CONSTRAINT FK_chat_sessions_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id)
    );

    CREATE NONCLUSTERED INDEX IX_chat_sessions_contract_id ON app.chat_sessions (contract_id);
END
GO

IF OBJECT_ID(N'app.chat_messages', N'U') IS NULL
BEGIN
    CREATE TABLE app.chat_messages (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_chat_messages_id DEFAULT NEWSEQUENTIALID(),
        session_id      UNIQUEIDENTIFIER NOT NULL,
        role            NVARCHAR(20)     NOT NULL,
        content         NVARCHAR(MAX)    NOT NULL,
        references_json NVARCHAR(MAX)    NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_chat_messages_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_chat_messages PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_chat_messages_session_id FOREIGN KEY (session_id) REFERENCES app.chat_sessions (id),
        CONSTRAINT CK_chat_messages_role CHECK (role IN (N'user', N'assistant', N'system'))
    );

    CREATE NONCLUSTERED INDEX IX_chat_messages_session_id ON app.chat_messages (session_id);
END
GO

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

/* ============================================================
   Reports and downloads
   ============================================================ */

IF OBJECT_ID(N'app.reports', N'U') IS NULL
BEGIN
    CREATE TABLE app.reports (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_reports_id DEFAULT NEWSEQUENTIALID(),
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        format          NVARCHAR(20)     NOT NULL,
        storage_path    NVARCHAR(500)    NOT NULL,
        generated_by    UNIQUEIDENTIFIER NOT NULL,
        generated_at    DATETIME2(3)     NOT NULL CONSTRAINT DF_reports_generated_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_reports PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_reports_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT FK_reports_generated_by FOREIGN KEY (generated_by) REFERENCES app.users (id),
        CONSTRAINT CK_reports_format CHECK (format IN (N'pdf', N'json'))
    );

    CREATE NONCLUSTERED INDEX IX_reports_analysis_id ON app.reports (analysis_id);
END
GO

IF OBJECT_ID(N'app.download_logs', N'U') IS NULL
BEGIN
    CREATE TABLE app.download_logs (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_download_logs_id DEFAULT NEWSEQUENTIALID(),
        user_id         UNIQUEIDENTIFIER NOT NULL,
        resource_type   NVARCHAR(50)     NOT NULL,
        resource_id     UNIQUEIDENTIFIER NOT NULL,
        downloaded_at   DATETIME2(3)     NOT NULL CONSTRAINT DF_download_logs_downloaded_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_download_logs PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_download_logs_user_id FOREIGN KEY (user_id) REFERENCES app.users (id),
        CONSTRAINT CK_download_logs_resource_type CHECK (resource_type IN (N'contract', N'report', N'document'))
    );

    CREATE NONCLUSTERED INDEX IX_download_logs_user_id ON app.download_logs (user_id);
    CREATE NONCLUSTERED INDEX IX_download_logs_downloaded_at ON app.download_logs (downloaded_at DESC);
END
GO

/* ============================================================
   Notifications
   ============================================================ */

IF OBJECT_ID(N'app.notifications', N'U') IS NULL
BEGIN
    CREATE TABLE app.notifications (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_notifications_id DEFAULT NEWSEQUENTIALID(),
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        user_id         UNIQUEIDENTIFIER NOT NULL,
        lawyer_email    NVARCHAR(320)    NOT NULL,
        decision        NVARCHAR(MAX)    NOT NULL,
        status          NVARCHAR(32)     NOT NULL,
        sent_at         DATETIME2(3)     NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_notifications_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_notifications PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_notifications_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT FK_notifications_user_id FOREIGN KEY (user_id) REFERENCES app.users (id),
        CONSTRAINT CK_notifications_status CHECK (status IN (N'pending', N'sent', N'failed'))
    );

    CREATE NONCLUSTERED INDEX IX_notifications_analysis_id ON app.notifications (analysis_id);
END
GO

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
END
GO

/* ============================================================
   Contract comparison (P1)
   ============================================================ */

IF OBJECT_ID(N'app.contract_comparisons', N'U') IS NULL
BEGIN
    CREATE TABLE app.contract_comparisons (
        id                      UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_contract_comparisons_id DEFAULT NEWSEQUENTIALID(),
        base_contract_id        UNIQUEIDENTIFIER NOT NULL,
        compare_contract_id     UNIQUEIDENTIFIER NOT NULL,
        created_by              UNIQUEIDENTIFIER NOT NULL,
        summary                 NVARCHAR(MAX)    NULL,
        risk_delta              NVARCHAR(16)     NULL,
        created_at              DATETIME2(3)     NOT NULL CONSTRAINT DF_contract_comparisons_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_contract_comparisons PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_contract_comparisons_base FOREIGN KEY (base_contract_id) REFERENCES app.contracts (id),
        CONSTRAINT FK_contract_comparisons_compare FOREIGN KEY (compare_contract_id) REFERENCES app.contracts (id),
        CONSTRAINT FK_contract_comparisons_created_by FOREIGN KEY (created_by) REFERENCES app.users (id),
        CONSTRAINT CK_contract_comparisons_risk_delta CHECK (
            risk_delta IS NULL OR risk_delta IN (N'low', N'medium', N'high')
        )
    );
END
GO

IF OBJECT_ID(N'app.comparison_changes', N'U') IS NULL
BEGIN
    CREATE TABLE app.comparison_changes (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_comparison_changes_id DEFAULT NEWSEQUENTIALID(),
        comparison_id   UNIQUEIDENTIFIER NOT NULL,
        change_type     NVARCHAR(50)     NOT NULL,
        category        NVARCHAR(100)    NULL,
        description     NVARCHAR(MAX)    NULL,
        old_value       NVARCHAR(MAX)    NULL,
        new_value       NVARCHAR(MAX)    NULL,
        CONSTRAINT PK_comparison_changes PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_comparison_changes_comparison_id FOREIGN KEY (comparison_id) REFERENCES app.contract_comparisons (id),
        CONSTRAINT CK_comparison_changes_type CHECK (change_type IN (N'added', N'removed', N'modified'))
    );

    CREATE NONCLUSTERED INDEX IX_comparison_changes_comparison_id ON app.comparison_changes (comparison_id);
END
GO

/* ============================================================
   Human-in-the-loop (P2)
   ============================================================ */

IF OBJECT_ID(N'app.finding_reviews', N'U') IS NULL
BEGIN
    CREATE TABLE app.finding_reviews (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_finding_reviews_id DEFAULT NEWSEQUENTIALID(),
        finding_id      UNIQUEIDENTIFIER NOT NULL,
        lawyer_id       UNIQUEIDENTIFIER NOT NULL,
        verdict         NVARCHAR(32)     NOT NULL,
        notes           NVARCHAR(MAX)    NULL,
        created_at      DATETIME2(3)     NOT NULL CONSTRAINT DF_finding_reviews_created_at DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_finding_reviews PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_finding_reviews_finding_id FOREIGN KEY (finding_id) REFERENCES app.findings (id),
        CONSTRAINT FK_finding_reviews_lawyer_id FOREIGN KEY (lawyer_id) REFERENCES app.users (id),
        CONSTRAINT CK_finding_reviews_verdict CHECK (verdict IN (N'correct', N'incorrect', N'not_relevant'))
    );

    CREATE NONCLUSTERED INDEX IX_finding_reviews_finding_id ON app.finding_reviews (finding_id);
END
GO

IF OBJECT_ID(N'app.analysis_approvals', N'U') IS NULL
BEGIN
    CREATE TABLE app.analysis_approvals (
        id              UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_analysis_approvals_id DEFAULT NEWSEQUENTIALID(),
        analysis_id     UNIQUEIDENTIFIER NOT NULL,
        lawyer_id       UNIQUEIDENTIFIER NOT NULL,
        approved_at     DATETIME2(3)     NOT NULL CONSTRAINT DF_analysis_approvals_approved_at DEFAULT (SYSUTCDATETIME()),
        notes           NVARCHAR(MAX)    NULL,
        CONSTRAINT PK_analysis_approvals PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_analysis_approvals_analysis_id UNIQUE (analysis_id),
        CONSTRAINT FK_analysis_approvals_analysis_id FOREIGN KEY (analysis_id) REFERENCES app.analyses (id),
        CONSTRAINT FK_analysis_approvals_lawyer_id FOREIGN KEY (lawyer_id) REFERENCES app.users (id)
    );
END
GO

PRINT 'Legal Rent AI schema created successfully in [app].';
GO
