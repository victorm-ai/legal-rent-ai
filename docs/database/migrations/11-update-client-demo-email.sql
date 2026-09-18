/*
  Update demo client email for notifications and login.
  Password unchanged: cliente123
*/
USE LegalRentAI;
GO

UPDATE app.users
SET email = N'code.zemoreno@gmail.com'
WHERE email = N'cliente@contractes.com';
GO
