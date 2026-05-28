CREATE TABLE departments (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE employees (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    salary        REAL NOT NULL
);

INSERT INTO departments VALUES (1,'Engineering'),(2,'Marketing'),(3,'HR');

INSERT INTO employees VALUES
  (1,'Alice',1,90000),(2,'Bob',1,85000),(3,'Carol',2,70000),
  (4,'Dave',2,72000),(5,'Eve',1,95000),(6,'Frank',3,60000),
  (7,'Grace',3,62000),(8,'Hank',1,88000),(9,'Ivy',2,75000),
  (10,'Jack',3,58000);
