/*
  Final lawyer notes when a contract is marked terminated (Terminado).
*/

USE LegalRentAI;
GO

IF COL_LENGTH('app.contracts', 'closure_notes') IS NULL
BEGIN
    ALTER TABLE app.contracts ADD closure_notes NVARCHAR(MAX) NULL;
    PRINT 'Added app.contracts.closure_notes';
END
GO
