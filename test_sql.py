from tools.native.execute_sql import execute_sql

# Test SQLite database creation and query
result = execute_sql('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO users (name) VALUES ("Alice"), ("Bob"), ("Charlie");', 'sqlite', database='test.db')
print("Create/Insert result:", result)

result2 = execute_sql('SELECT * FROM users;', 'sqlite', database='test.db')
print("Select result:", result2)