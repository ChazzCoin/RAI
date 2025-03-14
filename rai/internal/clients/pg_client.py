import psycopg2
from F.LOG import Log

from rai.internal.authority import AUTHORITY

Log = Log("Postgres Database Client")

post_name = AUTHORITY.get_env("POSTGRES_DB_NAME", "rai")
post_user = AUTHORITY.get_env("POSTGRES_DB_USER", "rai")
post_pass = AUTHORITY.get_env("POSTGRES_DB_PASSWORD", "rai2024")
post_host = AUTHORITY.get_env("POSTGRES_DB_HOST", "192.168.1.6")
post_port = AUTHORITY.get_env("POSTGRES_DB_PORT", 5431)

class cPostgres:

    connection: psycopg2
    cursor = None

    def __init__(self):
        self.connect()

    def connect(self):
        # Initialize connection to PostgreSQL database using psycopg3
        try:
            self.connection = psycopg2.connect(
                dbname=post_name,
                user=post_user,
                password=post_pass,
                host=post_host,
                port=post_port
            )
            self.cursor = self.connection.cursor()
            print(self.connection.info.status)
            Log.s("Successfully Connected to Remote Postgres Client.")
        except psycopg2.Error as e:
            Log.e(f"Error Connecting to Postgres Client: {e}")
            raise

    def fetch_schema(self):
        try:
            # Open a cursor to perform database operations
            with self.connection.cursor() as cursor:
                # SQL query to retrieve schema information (tables and columns)
                schema_query = """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                    """
                cursor.execute(schema_query)
                schema_data = cursor.fetchall()

                # Format schema into AI-friendly output
                return self.format_schema_for_prompt(schema_data)
        except psycopg2.Error as e:
            print(f"Error fetching schema: {e}")
            return None

    def format_schema_for_prompt(self, schema_data):
        schema_dict = {}
        for table, column in schema_data:
            if table not in schema_dict:
                schema_dict[table] = []
            schema_dict[table].append(column)
        # Format the schema into a human-readable string for an AI prompt
        formatted_schema = "Database Schema:\n"
        for table, columns in schema_dict.items():
            formatted_schema += f"\nTable: {table}\nColumns: {', '.join(columns)}\n"
        return formatted_schema

    def close(self):
        """Close the connection to the database."""
        if self.connection:
            self.cursor.close()
            self.connection.close()
            print("Connection to PostgreSQL database closed.")