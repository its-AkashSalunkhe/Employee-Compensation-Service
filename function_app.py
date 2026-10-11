import json
import logging
import os
from datetime import date
from decimal import Decimal

import azure.functions as func
import pyodbc

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

MAX_AMOUNT = 9999999999.99

EMPLOYEE_SELECT = (
    "SELECT e.EmployeeID, e.FirstName, e.LastName, e.DepartmentID, d.DepartmentName, "
    "e.Salary, e.Bonus, e.HireDate "
    "FROM Employee e LEFT JOIN Department d ON d.DepartmentID = e.DepartmentID "
)


def get_conn():
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("SQL_CONNECTION_STRING is not set")
    return pyodbc.connect(conn_str)


def fetch_all(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def reply(status, body):
    return func.HttpResponse(
        json.dumps(body, default=json_default),
        status_code=status,
        mimetype="application/json",
    )


def server_error(e):
    logging.exception("Request failed")
    if isinstance(e, (pyodbc.OperationalError, pyodbc.InterfaceError)):
        return reply(503, {"error": "Database is not reachable right now, try again later"})
    return reply(500, {"error": "Something went wrong on the server"})


def to_int(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def department_exists(dept_id):
    rows = fetch_all("SELECT DepartmentID FROM Department WHERE DepartmentID = ?", (dept_id,))
    return len(rows) > 0


def check_employee(body, is_new):
    if not isinstance(body, dict):
        return ["Body must be a JSON object"]

    errors = []

    for field in ["FirstName", "LastName", "DepartmentID", "Salary"]:
        if (is_new or field in body) and body.get(field) is None:
            errors.append(field + " is required")

    for field in ["FirstName", "LastName"]:
        value = body.get(field)
        if value is not None and (not isinstance(value, str) or value.strip() == "" or len(value) > 50):
            errors.append(field + " must be text of 1 to 50 characters")

    dept = body.get("DepartmentID")
    if dept is not None and (not isinstance(dept, int) or isinstance(dept, bool)):
        errors.append("DepartmentID must be a whole number")

    salary = body.get("Salary")
    if salary is not None and (not is_number(salary) or salary <= 0 or salary > MAX_AMOUNT):
        errors.append("Salary must be a number greater than 0")

    bonus = body.get("Bonus")
    if bonus is not None and (not is_number(bonus) or bonus < 0 or bonus > MAX_AMOUNT):
        errors.append("Bonus must be a number of 0 or more, or null for no bonus")

    hire_date = body.get("HireDate")
    if hire_date is not None:
        try:
            date.fromisoformat(hire_date)
        except (TypeError, ValueError):
            errors.append("HireDate must be in YYYY-MM-DD format")

    return errors


def report(sql, params=()):
    try:
        return reply(200, fetch_all(sql, params))
    except Exception as e:
        return server_error(e)


# Part A - employee CRUD

@app.route(route="departments", methods=["GET"])
def list_departments(req: func.HttpRequest) -> func.HttpResponse:
    return report("SELECT DepartmentID, DepartmentName, Location FROM Department ORDER BY DepartmentID")


@app.route(route="employees", methods=["POST"])
def create_employee(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return reply(400, {"error": "Request body must be valid JSON"})

    errors = check_employee(body, True)
    if errors:
        return reply(400, {"errors": errors})

    try:
        if not department_exists(body["DepartmentID"]):
            return reply(400, {"error": "DepartmentID " + str(body["DepartmentID"]) + " does not exist"})

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate) "
                "OUTPUT INSERTED.EmployeeID VALUES (?, ?, ?, ?, ?, ?)",
                (
                    body["FirstName"].strip(),
                    body["LastName"].strip(),
                    body["DepartmentID"],
                    body["Salary"],
                    body.get("Bonus"),
                    body.get("HireDate"),
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        rows = fetch_all(EMPLOYEE_SELECT + "WHERE e.EmployeeID = ?", (new_id,))
        return reply(201, rows[0])
    except Exception as e:
        return server_error(e)


@app.route(route="employees/{id}", methods=["GET"])
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = to_int(req.route_params.get("id"))
    if emp_id is None:
        return reply(400, {"error": "Employee id must be a number"})

    try:
        rows = fetch_all(EMPLOYEE_SELECT + "WHERE e.EmployeeID = ?", (emp_id,))
        if not rows:
            return reply(404, {"error": "Employee not found"})
        return reply(200, rows[0])
    except Exception as e:
        return server_error(e)


@app.route(route="employees", methods=["GET"])
def list_employees(req: func.HttpRequest) -> func.HttpResponse:
    sql = EMPLOYEE_SELECT
    params = ()

    dept_text = req.params.get("departmentId")
    if dept_text is not None:
        dept_id = to_int(dept_text)
        if dept_id is None:
            return reply(400, {"error": "departmentId must be a number"})
        sql += "WHERE e.DepartmentID = ? "
        params = (dept_id,)
    sql += "ORDER BY e.EmployeeID"

    try:
        if params and not department_exists(params[0]):
            return reply(404, {"error": "Department not found"})
        return reply(200, fetch_all(sql, params))
    except Exception as e:
        return server_error(e)


@app.route(route="employees/{id}", methods=["PUT", "PATCH"])
def update_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = to_int(req.route_params.get("id"))
    if emp_id is None:
        return reply(400, {"error": "Employee id must be a number"})

    try:
        body = req.get_json()
    except ValueError:
        return reply(400, {"error": "Request body must be valid JSON"})

    errors = check_employee(body, False)
    if errors:
        return reply(400, {"errors": errors})

    sets = []
    values = []
    for field in ["FirstName", "LastName", "DepartmentID", "Salary", "Bonus", "HireDate"]:
        if field in body:
            value = body[field]
            if field in ("FirstName", "LastName"):
                value = value.strip()
            sets.append(field + " = ?")
            values.append(value)

    if not sets:
        return reply(400, {"error": "No fields to update"})
    values.append(emp_id)

    try:
        if not fetch_all("SELECT EmployeeID FROM Employee WHERE EmployeeID = ?", (emp_id,)):
            return reply(404, {"error": "Employee not found"})
        if "DepartmentID" in body and not department_exists(body["DepartmentID"]):
            return reply(400, {"error": "DepartmentID " + str(body["DepartmentID"]) + " does not exist"})

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE Employee SET " + ", ".join(sets) + " WHERE EmployeeID = ?", tuple(values))
            conn.commit()
        finally:
            conn.close()

        rows = fetch_all(EMPLOYEE_SELECT + "WHERE e.EmployeeID = ?", (emp_id,))
        return reply(200, rows[0])
    except Exception as e:
        return server_error(e)


@app.route(route="employees/{id}", methods=["DELETE"])
def delete_employee(req: func.HttpRequest) -> func.HttpResponse:
    emp_id = to_int(req.route_params.get("id"))
    if emp_id is None:
        return reply(400, {"error": "Employee id must be a number"})

    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM Employee WHERE EmployeeID = ?", (emp_id,))
            deleted = cur.rowcount
            conn.commit()
        finally:
            conn.close()

        if deleted == 0:
            return reply(404, {"error": "Employee not found"})
        return reply(200, {"message": "Employee " + str(emp_id) + " deleted"})
    except Exception as e:
        return server_error(e)


# Part B - compensation reports

@app.route(route="reports/total-bonus", methods=["GET"])
def total_bonus(req: func.HttpRequest) -> func.HttpResponse:
    try:
        rows = fetch_all("SELECT COALESCE(SUM(Bonus), 0) AS TotalBonus FROM Employee")
        return reply(200, rows[0])
    except Exception as e:
        return server_error(e)


@app.route(route="reports/no-bonus", methods=["GET"])
def no_bonus_employees(req: func.HttpRequest) -> func.HttpResponse:
    return report(EMPLOYEE_SELECT + "WHERE e.Bonus IS NULL ORDER BY e.EmployeeID")


@app.route(route="reports/bonus-percentage", methods=["GET"])
def bonus_percentage(req: func.HttpRequest) -> func.HttpResponse:
    return report(
        "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
        "ROUND(Bonus * 100.0 / Salary, 2) AS BonusPercentage "
        "FROM Employee WHERE Bonus IS NOT NULL "
        "ORDER BY BonusPercentage DESC, EmployeeID"
    )


@app.route(route="reports/department-bonus-above-avg-salary", methods=["GET"])
def departments_bonus_above_avg(req: func.HttpRequest) -> func.HttpResponse:
    return report(
        "SELECT d.DepartmentID, d.DepartmentName, "
        "SUM(COALESCE(e.Bonus, 0)) AS TotalBonus, ROUND(AVG(e.Salary), 2) AS AverageSalary "
        "FROM Department d JOIN Employee e ON e.DepartmentID = d.DepartmentID "
        "GROUP BY d.DepartmentID, d.DepartmentName "
        "HAVING SUM(COALESCE(e.Bonus, 0)) > AVG(e.Salary) "
        "ORDER BY d.DepartmentID"
    )


@app.route(route="reports/bonus-ranking", methods=["GET"])
def bonus_ranking(req: func.HttpRequest) -> func.HttpResponse:
    return report(
        "SELECT RANK() OVER (ORDER BY CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END, Bonus DESC) AS BonusRank, "
        "EmployeeID, FirstName, LastName, Bonus "
        "FROM Employee ORDER BY BonusRank, EmployeeID"
    )


@app.route(route="reports/top-earner", methods=["GET"])
def top_earner(req: func.HttpRequest) -> func.HttpResponse:
    try:
        by_salary = fetch_all(
            "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
            "Salary + COALESCE(Bonus, 0) AS TotalCompensation "
            "FROM Employee WHERE Salary = (SELECT MAX(Salary) FROM Employee) "
            "ORDER BY EmployeeID"
        )
        by_total = fetch_all(
            "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
            "Salary + COALESCE(Bonus, 0) AS TotalCompensation "
            "FROM Employee WHERE Salary + COALESCE(Bonus, 0) = "
            "(SELECT MAX(Salary + COALESCE(Bonus, 0)) FROM Employee) "
            "ORDER BY EmployeeID"
        )
        if not by_salary:
            return reply(404, {"error": "No employees found"})

        top = by_salary[0]
        same = top["TotalCompensation"] == by_total[0]["TotalCompensation"]
        return reply(200, {
            "HighestSalaryEmployee": top,
            "AlsoHighestTotalCompensation": same,
            "HighestTotalCompensationEmployee": by_total[0],
        })
    except Exception as e:
        return server_error(e)


# Part C (optional) - default bonus, worked out when reading, not stored

@app.route(route="reports/bonus-with-default", methods=["GET"])
def bonus_with_default(req: func.HttpRequest) -> func.HttpResponse:
    percent = float(os.environ.get("DEFAULT_BONUS_PERCENT", "5"))
    return report(
        "SELECT EmployeeID, FirstName, LastName, Salary, Bonus, "
        "CAST(COALESCE(Bonus, ROUND(Salary * ? / 100.0, 2)) AS DECIMAL(12,2)) AS EffectiveBonus, "
        "CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END AS IsDefaultBonus "
        "FROM Employee ORDER BY EmployeeID",
        (percent,),
    )
