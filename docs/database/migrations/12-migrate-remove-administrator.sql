/*

  Normalize role catalog to lawyer=1, client=2 (no administrator).

  Idempotent. Uses NOCHECK on FK_users_role_id during ID renumbering.

*/



USE LegalRentAI;

GO



SET NOCOUNT ON;

GO



IF EXISTS (SELECT 1 FROM app.roles WHERE code = N'lawyer' AND id = 1)

   AND EXISTS (SELECT 1 FROM app.roles WHERE code = N'client' AND id = 2)

   AND NOT EXISTS (SELECT 1 FROM app.roles WHERE code = N'administrator')

BEGIN

    PRINT 'Role catalog already normalized (lawyer=1, client=2).';

END

ELSE

BEGIN

    DELETE FROM app.users WHERE email IN (N'admin@contractes.com', N'administrador@contractes.com');



    DECLARE @admin_id TINYINT = (SELECT id FROM app.roles WHERE code = N'administrator');

    DECLARE @lawyer_id TINYINT = (SELECT id FROM app.roles WHERE code = N'lawyer');

    DECLARE @client_id TINYINT = (SELECT id FROM app.roles WHERE code = N'client');



    IF @admin_id IS NOT NULL AND @lawyer_id IS NOT NULL AND @admin_id <> @lawyer_id

    BEGIN

        UPDATE app.users SET role_id = @lawyer_id WHERE role_id = @admin_id;

    END



    DELETE FROM app.roles WHERE code = N'administrator';



    ALTER TABLE app.users NOCHECK CONSTRAINT FK_users_role_id;



    IF @lawyer_id IS NOT NULL AND @lawyer_id <> 101

    BEGIN

        UPDATE app.roles SET id = 101 WHERE code = N'lawyer';

        UPDATE app.users SET role_id = 101 WHERE role_id = @lawyer_id;

        SET @lawyer_id = 101;

    END



    IF @client_id IS NOT NULL AND @client_id <> 102

    BEGIN

        UPDATE app.roles SET id = 102 WHERE code = N'client';

        UPDATE app.users SET role_id = 102 WHERE role_id = @client_id;

        SET @client_id = 102;

    END



    UPDATE app.roles SET id = 1 WHERE code = N'lawyer';

    UPDATE app.roles SET id = 2 WHERE code = N'client';

    UPDATE app.users SET role_id = 1 WHERE role_id = 101;

    UPDATE app.users SET role_id = 2 WHERE role_id = 102;



    ALTER TABLE app.users WITH CHECK CHECK CONSTRAINT FK_users_role_id;



    PRINT 'Role catalog normalized: lawyer=1, client=2.';

END

GO


