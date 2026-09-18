/*
  Legal Rent AI — Create database
  Run this script connected to the master database (default in SSMS).
  Target: SQL Server 2019+ / SQL Server Express / Developer Edition
*/

USE master;
GO

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'LegalRentAI')
BEGIN
    CREATE DATABASE LegalRentAI
    COLLATE SQL_Latin1_General_CP1_CI_AS;
    PRINT 'Database LegalRentAI created.';
END
ELSE
BEGIN
    PRINT 'Database LegalRentAI already exists.';
END
GO

USE LegalRentAI;
GO

PRINT 'Connected to LegalRentAI.';
GO
