import psycopg
from config import env

class PostgresSchemaExtractor:
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
        if self.connection:
            self.connection.close()

# Usage example:
if __name__ == "__main__":
    schema_extractor = PostgresSchemaExtractor()
    schema = schema_extractor.fetch_schema()
    if schema:
        print(schema)  # Print or send this formatted schema to the AI prompt
    schema_extractor.close()
