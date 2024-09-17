import psycopg
from config import env
from datetime import datetime
from config.postgres import PostgresClient

class PromptModel(PostgresClient):

    def __init__(self):
        # Initialize the base PostgresClient and ensure table exists for prompts
        super().__init__()
        self.ensure_table_exists()

    def ensure_table_exists(self):
        """Ensure the chat_prompts table exists in the database."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS chat_prompts (
            id SERIAL PRIMARY KEY,
            prompt TEXT NOT NULL,
            type VARCHAR(50) NOT NULL,
            category VARCHAR(50) NOT NULL,
            subCategory VARCHAR(50),
            dateCreated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dateUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_query)
                self.connection.commit()
                print("chat_prompts table is ready.")
        except Exception as e:
            print(f"Error creating table: {e}")
            self.connection.rollback()

    def save_prompt(self, prompt, prompt_type, category, sub_category=None):
        """Save a new chat prompt."""
        insert_query = """
        INSERT INTO chat_prompts (prompt, type, category, subCategory) 
        VALUES (%(prompt)s, %(type)s, %(category)s, %(subCategory)s) RETURNING id;
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_query, {
                    'prompt': prompt,
                    'type': prompt_type,
                    'category': category,
                    'subCategory': sub_category
                })
                prompt_id = cursor.fetchone()[0]
                self.connection.commit()
                print(f"Prompt saved with ID: {prompt_id}")
                return prompt_id
        except Exception as e:
            print(f"Error saving prompt: {e}")
            self.connection.rollback()
            return None

    def get_prompt_by_id(self, prompt_id):
        """Retrieve a chat prompt by its ID."""
        query = "SELECT * FROM chat_prompts WHERE id = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (prompt_id,))
                prompt_record = cursor.fetchone()
                if prompt_record:
                    return self.format_prompt_record(prompt_record)
                else:
                    print(f"No prompt found with ID: {prompt_id}")
                    return None
        except Exception as e:
            print(f"Error retrieving prompt: {e}")
            return None

    def update_prompt(self, prompt_id, prompt=None, prompt_type=None, category=None, sub_category=None):
        """Update an existing chat prompt or its metadata."""
        update_query = """
        UPDATE chat_prompts SET
        prompt = COALESCE(%(prompt)s, prompt),
        type = COALESCE(%(type)s, type),
        category = COALESCE(%(category)s, category),
        subCategory = COALESCE(%(subCategory)s, subCategory),
        dateUpdated = %(dateUpdated)s
        WHERE id = %(id)s;
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(update_query, {
                    'prompt': prompt,
                    'type': prompt_type,
                    'category': category,
                    'subCategory': sub_category,
                    'dateUpdated': datetime.now(),
                    'id': prompt_id
                })
                self.connection.commit()
                print(f"Prompt with ID {prompt_id} updated successfully.")
        except Exception as e:
            print(f"Error updating prompt: {e}")
            self.connection.rollback()

    def delete_prompt(self, prompt_id):
        """Delete a prompt by its ID."""
        delete_query = "DELETE FROM chat_prompts WHERE id = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(delete_query, (prompt_id,))
                self.connection.commit()
                print(f"Prompt with ID {prompt_id} deleted successfully.")
        except Exception as e:
            print(f"Error deleting prompt: {e}")
            self.connection.rollback()

    def get_all_prompts(self, limit=10):
        """Retrieve all chat prompts with a limit."""
        query = f"SELECT * FROM chat_prompts ORDER BY dateCreated DESC LIMIT {limit}"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                records = cursor.fetchall()
                return [self.format_prompt_record(record) for record in records]
        except Exception as e:
            print(f"Error retrieving prompts: {e}")
            return []

    def format_prompt_record(self, record):
        """Format a prompt record into a dictionary."""
        return {
            'id': record[0],
            'prompt': record[1],
            'type': record[2],
            'category': record[3],
            'subCategory': record[4],
            'dateCreated': record[5],
            'dateUpdated': record[6]
        }

    def close(self):
        """Close the connection and commit changes before exiting."""
        if self.connection:
            self.connection.commit()
            self.connection.close()
            print("Connection to PostgreSQL database closed.")


# Example usage
if __name__ == "__main__":
    chat_model = PromptModel()
    # Save a new prompt
    prompt_id = chat_model.save_prompt(
        "What is the capital of France?",
        prompt_type="user",
        category="Geography",
        sub_category="Countries"
    )
    # Retrieve a prompt by ID
    prompt = chat_model.get_prompt_by_id(prompt_id)
    print(prompt)

    # Update the response for a prompt
    chat_model.update_prompt(prompt_id, prompt="What is the largest country in Europe?")

    # Retrieve all prompts (limit to 5)
    all_prompts = chat_model.get_all_prompts(limit=5)
    print(all_prompts)

    # Delete a prompt by ID
    chat_model.delete_prompt(prompt_id)

    chat_model.close()
