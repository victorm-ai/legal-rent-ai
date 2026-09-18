/*
  Legal Rent AI — Seed data (development)
  Run after ddl.sql against database LegalRentAI.
  Demo users match auth/service.py (PBKDF2-HMAC-SHA256, 100k iterations).
*/

USE LegalRentAI;
GO

SET NOCOUNT ON;
GO

/* Fixed GUIDs for demo users (development only) */
DECLARE @lawyer_id UNIQUEIDENTIFIER = '11111111-1111-1111-1111-111111111102';
DECLARE @client_id UNIQUEIDENTIFIER = '11111111-1111-1111-1111-111111111103';

IF NOT EXISTS (SELECT 1 FROM app.users WHERE email = N'abogado@contractes.com')
BEGIN
    INSERT INTO app.users (id, email, name, role_id, password_hash, password_salt)
    VALUES (
        @lawyer_id,
        N'abogado@contractes.com',
        N'Sample Lawyer',
        1,
        N'90012ae3e6fa429f2ffedc5889aedd9850dce78d6999bdd9cf5dce862f57f029',
        N'9299b84380f1afaa0ea19356a2616eca'
    );
    PRINT 'Seeded user: abogado@contractes.com (password: abogado123)';
END

IF NOT EXISTS (SELECT 1 FROM app.users WHERE email = N'code.zemoreno@gmail.com')
BEGIN
    INSERT INTO app.users (id, email, name, role_id, password_hash, password_salt)
    VALUES (
        @client_id,
        N'code.zemoreno@gmail.com',
        N'Sample Client',
        2,
        N'b1fe3fc3927d290d50f006f512ffb979a026d52b0faa03b168dfdeb5b1fab8b1',
        N'bce50ae60aa194a161e1041ff763a8ad'
    );
    PRINT 'Seeded user: code.zemoreno@gmail.com (password: cliente123)';
END
GO

PRINT 'Seed data applied.';
GO
