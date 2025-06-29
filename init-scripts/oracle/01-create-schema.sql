-- Create test schema and sample data for Oracle
CREATE TABLE testschema.employees (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    department VARCHAR2(50),
    salary NUMBER(10,2),
    hire_date DATE,
    is_active NUMBER(1) DEFAULT 1
);

CREATE TABLE testschema.departments (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(50) NOT NULL,
    budget NUMBER(12,2),
    location VARCHAR2(100)
);

-- Insert sample data
INSERT INTO testschema.employees VALUES (1, 'John Doe', 'Engineering', 75000.00, DATE '2020-01-15', 1);
INSERT INTO testschema.employees VALUES (2, 'Jane Smith', 'Marketing', 65000.00, DATE '2020-03-20', 1);
INSERT INTO testschema.employees VALUES (3, 'Bob Johnson', 'Engineering', 80000.00, DATE '2019-08-10', 1);
INSERT INTO testschema.employees VALUES (4, 'Alice Brown', 'HR', 55000.00, DATE '2021-05-12', 0);
INSERT INTO testschema.employees VALUES (5, 'Charlie Wilson', 'Finance', 70000.00, DATE '2020-11-08', 1);

INSERT INTO testschema.departments VALUES (1, 'Engineering', 500000.00, 'San Francisco');
INSERT INTO testschema.departments VALUES (2, 'Marketing', 200000.00, 'New York');
INSERT INTO testschema.departments VALUES (3, 'HR', 150000.00, 'Chicago');
INSERT INTO testschema.departments VALUES (4, 'Finance', 300000.00, 'Boston');

COMMIT;