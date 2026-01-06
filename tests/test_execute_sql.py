"""
Tests for SQL execution tool.
"""

import json
import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from pathlib import Path

from tools.native.execute_sql import execute_sql


class TestExecuteSQL:
    """Test SQL execution tool"""

    def test_sqlite_select_query(self):
        """Test basic SQLite SELECT query"""
        query = "SELECT 1 as test_value, 'hello' as test_string"
        result = execute_sql(query)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["rows"]) == 1
        assert data["rows"][0]["test_value"] == 1
        assert data["rows"][0]["test_string"] == "hello"
        assert data["row_count"] == 1
        assert data["affected_rows"] == 0
        assert "execution_time_ms" in data

    def test_sqlite_create_and_insert(self):
        """Test SQLite CREATE TABLE and INSERT"""
        import uuid
        db_name = f"test_{uuid.uuid4().hex}.db"
        
        # Create table
        create_query = """
        CREATE TABLE test_users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER
        )
        """
        result = execute_sql(create_query, database=db_name)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["affected_rows"] == 0  # DDL doesn't return affected rows

        # Insert data
        insert_query = "INSERT INTO test_users (name, age) VALUES ('Alice', 30)"
        result = execute_sql(insert_query, database=db_name)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["affected_rows"] == 1

        # Select data
        select_query = "SELECT * FROM test_users"
        result = execute_sql(select_query, database=db_name)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["rows"]) == 1
        assert data["rows"][0]["name"] == "Alice"
        assert data["rows"][0]["age"] == 30

    def test_sqlite_workspace_creation(self):
        """Test that SQLite databases are created in workspace"""
        import uuid
        db_name = f"workspace_test_{uuid.uuid4().hex}.db"
        
        query = "SELECT 1"
        result = execute_sql(query, database=db_name)
        data = json.loads(result)
        assert data["status"] == "success"

        # Check database file exists in workspace
        db_path = Path("./workspace/sql/" + db_name)
        assert db_path.exists()
        assert db_path.is_file()

    def test_sql_invalid_query(self):
        """Test error handling for invalid SQL"""
        query = "INVALID SQL QUERY SYNTAX"
        result = execute_sql(query)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "message" in data

    def test_sql_unsupported_database(self):
        """Test unsupported database type"""
        query = "SELECT 1"
        result = execute_sql(query, db_type="unsupported")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Unsupported database type" in data["message"]

    @patch('tools.native.execute_sql.HAS_POSTGRESQL', False)
    def test_postgresql_not_available(self):
        """Test PostgreSQL when driver not available"""
        query = "SELECT 1"
        result = execute_sql(query, db_type="postgresql")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not available" in data["message"]

    @patch('tools.native.execute_sql.HAS_MYSQL', False)
    def test_mysql_not_available(self):
        """Test MySQL when driver not available"""
        query = "SELECT 1"
        result = execute_sql(query, db_type="mysql")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not available" in data["message"]

    def test_sql_connection_error_simulation(self):
        """Test connection error handling"""
        # Try to connect to non-existent PostgreSQL server
        query = "SELECT 1"
        result = execute_sql(query, db_type="postgresql", host="nonexistent.host")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "connection failed" in data["message"].lower()

    def test_sql_multiple_rows(self):
        """Test query returning multiple rows"""
        import uuid
        db_name = f"multi_{uuid.uuid4().hex}.db"
        
        # Create test data
        setup_queries = [
            "CREATE TABLE multi_test (id INTEGER, value TEXT)",
            "INSERT INTO multi_test VALUES (1, 'first')",
            "INSERT INTO multi_test VALUES (2, 'second')",
            "INSERT INTO multi_test VALUES (3, 'third')"
        ]

        for q in setup_queries:
            execute_sql(q, database=db_name)

        # Test multi-row select
        result = execute_sql("SELECT * FROM multi_test ORDER BY id", database=db_name)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["row_count"] == 3
        assert len(data["rows"]) == 3
        assert data["rows"][0]["value"] == "first"
        assert data["rows"][2]["value"] == "third"