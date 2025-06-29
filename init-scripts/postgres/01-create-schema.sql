-- Create test schema and sample data for PostgreSQL
CREATE SCHEMA IF NOT EXISTS testschema;

CREATE TABLE testschema.employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    salary DECIMAL(10,2),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE testschema.departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    budget DECIMAL(12,2),
    location VARCHAR(100)
);

-- Insert sample data
INSERT INTO testschema.employees (id, name, department, salary, hire_date, is_active) VALUES 
(1, 'John Doe', 'Engineering', 75000.00, '2020-01-15', TRUE),
(2, 'Jane Smith', 'Marketing', 65000.00, '2020-03-20', TRUE),
(3, 'Bob Johnson', 'Engineering', 80000.00, '2019-08-10', TRUE),
(4, 'Alice Brown', 'HR', 55000.00, '2021-05-12', FALSE),
(5, 'Charlie Wilson', 'Finance', 70000.00, '2020-11-08', TRUE);

INSERT INTO testschema.departments (id, name, budget, location) VALUES 
(1, 'Engineering', 500000.00, 'San Francisco'),
(2, 'Marketing', 200000.00, 'New York'),
(3, 'HR', 150000.00, 'Chicago'),
(4, 'Finance', 300000.00, 'Boston');

-- Reset sequences to ensure consistent IDs
SELECT setval('testschema.employees_id_seq', 5, true);
SELECT setval('testschema.departments_id_seq', 4, true);