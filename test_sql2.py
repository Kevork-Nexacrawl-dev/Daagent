from tools.native.execute_sql import execute_sql

# Test SQLite - create table
result1 = execute_sql('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);', 'sqlite', database='test.db')
print("Create table:", result1)

# Insert data
result2 = execute_sql('INSERT INTO users (name) VALUES ("Alice");', 'sqlite', database='test.db')
print("Insert Alice:", result2)

# Query data
result3 = execute_sql('SELECT * FROM users;', 'sqlite', database='test.db')
print("Select users:", result3)