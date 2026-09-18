/* Add perspective to analyses — one analysis per tenant/landlord/neutral per contract */

IF COL_LENGTH('app.analyses', 'perspective') IS NULL
BEGIN
    ALTER TABLE app.analyses ADD perspective NVARCHAR(32) NULL;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = N'CK_analyses_perspective'
)
BEGIN
    ALTER TABLE app.analyses
        ADD CONSTRAINT CK_analyses_perspective CHECK (
            perspective IS NULL OR perspective IN (N'landlord', N'tenant', N'neutral')
        );
END
GO

;WITH ranked AS (
    SELECT
        a.id,
        a.contract_id,
        ROW_NUMBER() OVER (PARTITION BY a.contract_id ORDER BY a.created_at) AS rn
    FROM app.analyses a
    WHERE a.perspective IS NULL
)
UPDATE a
SET a.perspective = CASE r.rn
    WHEN 1 THEN COALESCE(c.perspective, N'tenant')
    WHEN 2 THEN CASE COALESCE(c.perspective, N'tenant')
        WHEN N'tenant' THEN N'landlord'
        WHEN N'landlord' THEN N'tenant'
        ELSE N'tenant'
    END
    ELSE N'neutral'
END
FROM app.analyses a
INNER JOIN ranked r ON r.id = a.id
INNER JOIN app.contracts c ON c.id = a.contract_id;
GO

;WITH duplicates AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY contract_id, perspective
            ORDER BY created_at DESC
        ) AS rn
    FROM app.analyses
    WHERE perspective IS NOT NULL AND status <> N'failed'
)
UPDATE a
SET a.status = N'failed'
FROM app.analyses a
INNER JOIN duplicates d ON d.id = a.id
WHERE d.rn > 1;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = N'UX_analyses_contract_perspective' AND object_id = OBJECT_ID(N'app.analyses')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_analyses_contract_perspective
        ON app.analyses (contract_id, perspective)
        WHERE perspective IS NOT NULL AND status <> N'failed';
END
GO
