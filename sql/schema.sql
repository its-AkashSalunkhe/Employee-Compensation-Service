IF OBJECT_ID('dbo.Employee', 'U') IS NOT NULL DROP TABLE dbo.Employee;
IF OBJECT_ID('dbo.Department', 'U') IS NOT NULL DROP TABLE dbo.Department;

CREATE TABLE Department (
    DepartmentID    INT           NOT NULL PRIMARY KEY,
    DepartmentName  VARCHAR(100)  NOT NULL,
    Location        VARCHAR(100)  NULL
);

CREATE TABLE Employee (
    EmployeeID      INT IDENTITY(1,1) PRIMARY KEY,
    FirstName       VARCHAR(50)    NOT NULL,
    LastName        VARCHAR(50)    NOT NULL,
    DepartmentID    INT            NULL,
    Salary          DECIMAL(12,2)  NOT NULL,
    Bonus           DECIMAL(12,2)  NULL,
    HireDate        DATE           NULL,
    CONSTRAINT FK_Employee_Department FOREIGN KEY (DepartmentID) REFERENCES Department(DepartmentID),
    CONSTRAINT CK_Employee_Salary CHECK (Salary > 0),
    CONSTRAINT CK_Employee_Bonus CHECK (Bonus IS NULL OR Bonus >= 0)
);

CREATE INDEX IX_Employee_DepartmentID ON Employee(DepartmentID);
