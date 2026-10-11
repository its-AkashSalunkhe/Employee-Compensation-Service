INSERT INTO Department (DepartmentID, DepartmentName, Location) VALUES
(1, 'Engineering', 'Navi Mumbai'),
(2, 'Human Resources', 'Mumbai'),
(3, 'Finance', 'Mumbai'),
(4, 'Sales', 'Pune'),
(5, 'Marketing', NULL),
(6, 'Support', 'Navi Mumbai');

INSERT INTO Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate) VALUES
('Rohan', 'Patil', 1, 1200000.00, 120000.00, '2019-06-03'),
('Sneha', 'Kulkarni', 1, 950000.00, 80000.00, '2020-02-17'),
('Aditya', 'Joshi', 1, 780000.00, NULL, '2022-08-01'),
('Pooja', 'Nair', 1, 1500000.00, NULL, '2018-01-15'),
('Karan', 'Shah', 1, 650000.00, 50000.00, '2023-07-10'),
('Neha', 'Iyer', 2, 700000.00, NULL, '2021-04-12'),
('Amit', 'Gaikwad', 2, 560000.00, 28000.00, '2022-11-21'),
('Priya', 'Menon', 2, 620000.00, NULL, '2024-01-08'),
('Sanjay', 'More', 3, 1100000.00, 90000.00, '2019-09-30'),
('Divya', 'Rao', 3, 880000.00, NULL, '2021-12-06'),
('Mahesh', 'Pawar', 3, 720000.00, 36000.00, '2023-03-27'),
('Vikram', 'Deshmukh', 4, 1400000.00, 450000.00, '2018-10-22'),
('Anita', 'Sawant', 4, 850000.00, 300000.00, '2020-05-18'),
('Rahul', 'Chavan', 4, 640000.00, 200000.00, '2022-02-14'),
('Kavita', 'Bhosale', 4, 600000.00, NULL, '2024-06-03'),
('Ishita', 'Thakur', 5, 590000.00, NULL, '2023-09-11'),
('Nikhil', 'Jadhav', 5, 520000.00, 26000.00, '2024-02-19'),
('Shweta', 'Kamble', 5, 480000.00, NULL, '2025-01-13');
