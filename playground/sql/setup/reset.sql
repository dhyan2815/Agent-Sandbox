/*
===========================================
Reset Database
===========================================
*/

TRUNCATE TABLE employees
RESTART IDENTITY;

INSERT INTO employees
(first_name,last_name,department,salary,hire_date)

VALUES

('Alice','Johnson','Engineering',85000,'2022-03-15'),

('Bob','Smith','Marketing',60000,'2021-07-10'),

('Charlie','Brown','Engineering',90000,'2020-09-25'),

('David','Wilson','Sales',55000,'2023-01-12'),

('Emma','Taylor','HR',65000,'2022-11-08'),

('Frank','Anderson','Sales',72000,'2021-05-30'),

('Grace','Thomas','Marketing',68000,'2020-12-01'),

('Helen','Martin','Engineering',97000,'2019-04-18');