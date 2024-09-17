import psycopg
from config import env

class PostgresClient:
    connection: psycopg.connection

    def __init__(self):
        # Initialize connection to PostgreSQL database using psycopg3
        try:
            self.connection = psycopg.connect(
                dbname=env("POSTGRES_DB_NAME"),
                user=env("POSTGRES_DB_USER"),
                password=env("POSTGRES_DB_PASSWORD"),
                host=env("POSTGRES_DB_HOST"),
                port=env("POSTGRES_DB_PORT")
            )
        except psycopg.Error as e:
            print(f"Error connecting to the database: {e}")
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
        except psycopg.Error as e:
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

    def add_record(self, table_name, record):
        """Insert a record into a table."""
        columns = ', '.join(record.keys())
        values = ', '.join([f'%({key})s' for key in record.keys()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
        try:
            self.cursor.execute(query, record)
            print("Record added successfully.")
        except Exception as e:
            print(f"Error inserting record: {e}")
            self.connection.rollback()

    def query_table(self, table_name, columns='*', conditions=None):
        """Query records from a table."""
        try:
            if conditions:
                query = f"SELECT {columns} FROM {table_name} WHERE {conditions}"
            else:
                query = f"SELECT {columns} FROM {table_name}"
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records
        except Exception as e:
            print(f"Error querying table: {e}")
            return None

    def delete_record(self, table_name, conditions):
        """Delete a record from a table based on conditions."""
        query = f"DELETE FROM {table_name} WHERE {conditions}"
        try:
            self.cursor.execute(query)
            print("Record deleted successfully.")
        except Exception as e:
            print(f"Error deleting record: {e}")
            self.connection.rollback()

    def delete_table(self, table_name):
        """Delete an entire table."""
        query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
        try:
            self.cursor.execute(query)
            print(f"Table {table_name} deleted successfully.")
        except Exception as e:
            print(f"Error deleting table: {e}")
            self.connection.rollback()

    def get_tables(self):
        """Retrieve a list of all tables in the current database."""
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        try:
            self.cursor.execute(query)
            tables = self.cursor.fetchall()
            return [table[0] for table in tables]
        except Exception as e:
            print(f"Error retrieving tables: {e}")
            return None

    def get_columns(self, table_name):
        """Retrieve a list of columns in a specific table."""
        query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
        try:
            self.cursor.execute(query)
            columns = self.cursor.fetchall()
            return [col[0] for col in columns]
        except Exception as e:
            print(f"Error retrieving columns: {e}")
            return None

# Usage example
if __name__ == "__main__":
    client = PostgresClient(dbname="mydb", user="myuser", password="mypassword", host="myremotehost")
    client.connect()

    # Add a record
    record = {"name": "John Doe", "age": 30, "city": "New York"}
    client.add_record("users", record)

    # Query table
    users = client.query_table("users")
    print(users)

    # Get all tables
    tables = client.get_tables()
    print(tables)

    # Get columns from table
    columns = client.get_columns("users")
    print(columns)

    # Delete a record
    client.delete_record("users", "name = 'John Doe'")

    # Delete a table
    client.delete_table("old_table")

    client.close()



