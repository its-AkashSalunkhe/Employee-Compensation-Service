# Employee Compensation Service

Small backend service for an HR team to manage employee records and get bonus reports.
It is built as HTTP triggered Azure Functions (Python) on top of an Azure SQL database.
Clients only talk to the Functions, never to the database directly.

## What is used

- Python 3.11, Azure Functions (v2 programming model)
- Azure SQL Database (any SQL Server should also work)
- pyodbc with ODBC Driver 18 for SQL Server

## Files

```
function_app.py            all the functions
host.json
requirements.txt
local.settings.json.example
sql/schema.sql             creates Department and Employee tables
sql/seed.sql               sample data (6 departments, 18 employees)
```

## Setup

1. Create an Azure SQL database (the free account is enough) and add your client IP in the server firewall.
2. Run `sql/schema.sql` and then `sql/seed.sql` on the database. I used the Query editor in the Azure portal, Azure Data Studio or SSMS also works.
3. Install the tools: Python 3.11, Azure Functions Core Tools v4 and ODBC Driver 18 for SQL Server.
4. Copy `local.settings.json.example` to `local.settings.json` and put your own server, database, user and password in `SQL_CONNECTION_STRING`.
5. Install packages and start:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
func start
```

The functions will be available at `http://localhost:7071/api/...`

`local.settings.json` is in `.gitignore`, so the connection string is not committed.

## Endpoints

Employees (Part A)

| Method | Route | What it does |
| --- | --- | --- |
| POST | /api/employees | create employee (Bonus is optional) |
| GET | /api/employees/{id} | get one employee |
| GET | /api/employees?departmentId=1 | list employees, filter by department is optional |
| PUT or PATCH | /api/employees/{id} | update, only send the fields that need to change |
| DELETE | /api/employees/{id} | delete employee |
| GET | /api/departments | list departments (to look up department ids) |

Reports (Part B)

| Route | What it returns |
| --- | --- |
| /api/reports/total-bonus | total bonus of the whole company, NULL counted as 0 |
| /api/reports/no-bonus | employees whose bonus is NULL |
| /api/reports/bonus-percentage | bonus as % of salary (2 decimals) for employees with a bonus |
| /api/reports/department-bonus-above-avg-salary | departments where total bonus is more than the average salary |
| /api/reports/bonus-ranking | all employees ranked by bonus, no bonus ranked last |
| /api/reports/top-earner | highest salary employee, and whether they also have the highest salary + bonus |
| /api/reports/bonus-with-default | every employee with a 5% default bonus applied where Bonus is NULL (optional part) |

Sample calls

```
curl http://localhost:7071/api/employees?departmentId=4

curl -X POST http://localhost:7071/api/employees -H "Content-Type: application/json" \
  -d '{"FirstName":"Meera","LastName":"Kale","DepartmentID":2,"Salary":600000,"HireDate":"2026-10-01"}'

curl -X PUT http://localhost:7071/api/employees/3 -H "Content-Type: application/json" \
  -d '{"Bonus":45000}'

curl http://localhost:7071/api/reports/top-earner
```

To remove a bonus, send `{"Bonus": null}` in the update.

## Error handling

- 400 for bad input (invalid JSON, missing or wrong fields, department id that does not exist, non numeric ids)
- 404 when the employee or department is not found
- 503 when the database cannot be reached
- 500 for anything unexpected. The real error is only written to the log, the client gets a generic message.

All SQL uses parameters (`?`), no values are joined into the query text.

## Secrets

The connection string is read from the `SQL_CONNECTION_STRING` setting. Locally it is in `local.settings.json` (not committed). When deployed it goes in the Function App application settings, and it could be moved to Key Vault and referenced from there. The functions use the Function authorization level, so a function key is needed when calling the deployed app.

## Assumptions

- Only NULL counts as "no bonus". A bonus of 0 is treated as a bonus that was given with value 0.
- Amounts are in INR, the sample data uses that.
- DepartmentID and HireDate are nullable in the table as the brief did not mark them NOT NULL, but the create endpoint asks for a DepartmentID.
- I added CHECK constraints so Salary is above 0 and Bonus is not negative.
- If two employees have the same highest salary, the one with the lower EmployeeID is returned. Employees with equal bonus get the same rank (RANK is used, so the next rank is skipped).
- A department with no employees does not show in the department bonus report.
- The list endpoint has no paging since the data is small.

## Default bonus (5%)

I did not write the default bonus into the table, it is calculated while reading (`/api/reports/bonus-with-default`, the percent comes from `DEFAULT_BONUS_PERCENT`, default 5).

Reasons:

- It can be worked out from Salary, so storing it would duplicate data and go out of date when the salary changes.
- If the percentage rule changes there is only one place to change and no old rows to fix.
- Bonus NULL means no bonus was awarded. If the 5% was saved into the column, the "total bonus paid" and "never received a bonus" reports would become wrong because money that was never paid would be counted.

The downside is that every reader has to use the same calculation. If payroll needs the exact amount fixed at a point in time, then it should be saved at that time in a separate column or table, not in Bonus.

## Deploying to Azure

1. Create a Function App (Python 3.11, Linux).
2. Add `SQL_CONNECTION_STRING` in Configuration > Application settings.
3. Allow the Function App to reach the SQL server (Azure services toggle in the SQL server firewall, or the outbound IPs).
4. `func azure functionapp publish <function-app-name>`

## Things I would add with more time

- Managed identity for the database instead of a SQL password
- Paging on the employee list
- Unit tests and a CI pipeline
- Department CRUD endpoints
