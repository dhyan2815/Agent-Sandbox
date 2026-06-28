/*
===========================================
SQL Learning Database
Author: Dhyan Patel
===========================================

Run this file only once.
*/

DROP TABLE IF EXISTS employees;

CREATE TABLE employees (

    employee_id SERIAL PRIMARY KEY,

    first_name VARCHAR(50),

    last_name VARCHAR(50),

    department VARCHAR(50),

    salary NUMERIC(10,2),

    hire_date DATE
);