"""
SQL execution tool for Daagent.
Executes SQL queries against SQLite, PostgreSQL, and MySQL databases.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False

try:
    import pymysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class QueryExecutionError(Exception):
    """Raised when query execution fails."""
    pass


@contextmanager
def _get_connection(db_type: str, **kwargs):
    """
    Context manager for database connections.

    Args:
        db_type: Type of database ('sqlite', 'postgresql', 'mysql')
        **kwargs: Connection parameters

    Yields:
        Database connection object
    """
    conn = None
    try:
        if db_type == 'sqlite':
            db_path = kwargs.get('database', 'default.db')
            workspace_dir = Path("./workspace/sql")
            workspace_dir.mkdir(parents=True, exist_ok=True)
            full_path = workspace_dir / db_path
            conn = sqlite3.connect(str(full_path))

        elif db_type == 'postgresql':
            if not HAS_POSTGRESQL:
                raise DatabaseConnectionError("PostgreSQL support not available. Install psycopg2-binary.")
            conn = psycopg2.connect(
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 5432),
                database=kwargs.get('database', ''),
                user=kwargs.get('username', ''),
                password=kwargs.get('password', '')
            )

        elif db_type == 'mysql':
            if not HAS_MYSQL:
                raise DatabaseConnectionError("MySQL support not available. Install pymysql.")
            conn = pymysql.connect(
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 3306),
                database=kwargs.get('database', ''),
                user=kwargs.get('username', ''),
                password=kwargs.get('password', '')
            )

        else:
            raise DatabaseConnectionError(f"Unsupported database type: {db_type}")

        yield conn

    finally:
        if conn:
            conn.close()


def _execute_query(conn, query: str, db_type: str) -> Dict[str, Any]:
    """
    Execute a SQL query and return results.

    Args:
        conn: Database connection
        query: SQL query to execute
        db_type: Database type

    Returns:
        Dictionary with query results
    """
    start_time = time.time()
    cursor = None

    try:
        if db_type == 'sqlite':
            cursor = conn.cursor()
            cursor.execute(query)

            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                result_rows = [dict(zip(columns, row)) for row in rows]
                row_count = len(result_rows)
                affected_rows = 0
            else:
                # Check if it's a DDL statement (CREATE, ALTER, DROP, etc.)
                upper_query = query.strip().upper()
                if upper_query.startswith(('CREATE', 'ALTER', 'DROP', 'TRUNCATE')):
                    # DDL statements don't affect rows
                    affected_rows = 0
                else:
                    # DML operations (INSERT, UPDATE, DELETE)
                    affected_rows = cursor.rowcount
                row_count = 0
                result_rows = []

            conn.commit()

        elif db_type in ['postgresql', 'mysql']:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor if db_type == 'postgresql' else None)

            if db_type == 'postgresql':
                cursor.execute(query)
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    result_rows = [dict(row) for row in rows]
                    row_count = len(result_rows)
                    affected_rows = 0
                else:
                    affected_rows = cursor.rowcount
                    row_count = 0
                    result_rows = []
            else:  # mysql
                cursor.execute(query)
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    result_rows = [dict(zip(columns, row)) for row in rows]
                    row_count = len(result_rows)
                    affected_rows = 0
                else:
                    affected_rows = cursor.rowcount
                    row_count = 0
                    result_rows = []

            conn.commit()

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "rows": result_rows,
            "row_count": row_count,
            "affected_rows": affected_rows,
            "execution_time_ms": execution_time_ms
        }

    finally:
        if cursor:
            cursor.close()


def execute_sql(query: str, db_type: str = "sqlite", database: Optional[str] = None,
                host: Optional[str] = None, port: Optional[int] = None,
                username: Optional[str] = None, password: Optional[str] = None,
                timeout: int = 30) -> str:
    """
    Execute SQL query against specified database.

    Args:
        query: SQL query to execute
        db_type: Database type ('sqlite', 'postgresql', 'mysql') - default: sqlite
        database: Database name (for SQLite: filename, for others: database name)
        host: Database host (ignored for SQLite)
        port: Database port (ignored for SQLite)
        username: Database username (ignored for SQLite)
        password: Database password (ignored for SQLite)
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        JSON string containing query results:
        {
            "status": "success" | "error",
            "rows": array of result rows (for SELECT),
            "row_count": number of rows returned (for SELECT),
            "affected_rows": number of rows affected (for DML),
            "execution_time_ms": query execution time,
            "message": error message if failed
        }
    """
    try:
        # Validate database type
        supported_types = ['sqlite', 'postgresql', 'mysql']
        if db_type not in supported_types:
            return json.dumps({
                "status": "error",
                "message": f"Unsupported database type: {db_type}. Supported: {', '.join(supported_types)}",
                "rows": [],
                "row_count": 0,
                "affected_rows": 0,
                "execution_time_ms": 0
            })

        # Prepare connection parameters
        conn_kwargs = {}
        if db_type == 'sqlite':
            conn_kwargs['database'] = database or 'default.db'
        else:
            conn_kwargs.update({
                'host': host or 'localhost',
                'port': port or (5432 if db_type == 'postgresql' else 3306),
                'database': database or '',
                'username': username or '',
                'password': password or ''
            })

        # Execute query with timeout
        logger.info(f"Executing {db_type} query")
        with _get_connection(db_type, **conn_kwargs) as conn:
            result = _execute_query(conn, query, db_type)

        return json.dumps({
            "status": "success",
            "rows": result["rows"],
            "row_count": result["row_count"],
            "affected_rows": result["affected_rows"],
            "execution_time_ms": result["execution_time_ms"]
        }, indent=2)

    except DatabaseConnectionError as e:
        return json.dumps({
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "rows": [],
            "row_count": 0,
            "affected_rows": 0,
            "execution_time_ms": 0
        })
    except Exception as e:
        error_msg = f"Query execution failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg,
            "rows": [],
            "row_count": 0,
            "affected_rows": 0,
            "execution_time_ms": 0
        })


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_sql",
        "description": "Execute SQL queries against databases. Supports SQLite (default), PostgreSQL, and MySQL. Use this for database operations, data analysis, or any SQL-related tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute"
                },
                "db_type": {
                    "type": "string",
                    "enum": ["sqlite", "postgresql", "mysql"],
                    "description": "Database type (default: sqlite)",
                    "default": "sqlite"
                },
                "database": {
                    "type": "string",
                    "description": "Database name. For SQLite: filename (default: default.db). For others: database name."
                },
                "host": {
                    "type": "string",
                    "description": "Database host (ignored for SQLite, default: localhost)"
                },
                "port": {
                    "type": "integer",
                    "description": "Database port (ignored for SQLite, default: 5432 for PostgreSQL, 3306 for MySQL)"
                },
                "username": {
                    "type": "string",
                    "description": "Database username (ignored for SQLite)"
                },
                "password": {
                    "type": "string",
                    "description": "Database password (ignored for SQLite)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 30)",
                    "minimum": 1,
                    "maximum": 300
                }
            },
            "required": ["query"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_sql