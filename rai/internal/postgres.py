from rai.internal.clients.pg_client import cPostgres


class PostgresClient(cPostgres):

    def __init__(self):
        # Initialize connection to PostgreSQL database using psycopg3
        super().__init__()

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


POSTGRES_CLIENT = PostgresClient()

