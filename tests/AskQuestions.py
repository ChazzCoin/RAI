import unittest
import logging
import time


test_cases = [
        {
            "question": "Tell me about the futures program at park city soccer club...",
            "expected": "futures program"
        },
        {
            "question": "What is the core philosophy of park city's competitive program?",
            "expected": "competitive program"
        },
        {
            "question": "What do you offer for goalkeepers?"
        },
        {
            "question": "What tournaments does the club host? What are their names?",
            "expected": "tournaments"
        },
        {
            "question": "How do I register my child for tryouts?",
            "expected": "register"
        }
    ]

class DynamicRAGTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the model (or system) that will be tested, based on input parameters.
        Initialize logging as well.
        """
        # For example purposes, we're using RAGWithChroma here
        # but this could be any other model passed dynamically.
        model_class = cls.model_class
        collection_name = cls.collection_name
        cls.model_instance = model_class(collection_name=collection_name)

        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    @classmethod
    def setUpTestConfig(cls, model_class, collection_name, test_cases):
        cls.model_class = model_class
        cls.collection_name = collection_name
        cls.test_cases = test_cases

    def run_query_test(self, query, expected=None):
        logging.info(f"Running test for query: {query}")
        # Measure performance
        start_time = time.time()

        try:
            # Dynamically calling the model's generate_answer function
            answer = self.model_instance.generate_answer(query)
            end_time = time.time()

            # Log the result and performance
            logging.info(f"Query: {query}")
            logging.info(f"Answer: {answer}")
            logging.info(f"Time Taken: {end_time - start_time:.2f} seconds")

            print(f'\nQUESTION: {query}')
            print(f'ANSWER: {answer}')
            print(f'Time Taken: {end_time - start_time:.2f} seconds')

            # Optional: Assert if an expected answer is provided
            if expected:
                self.assertIn(expected, answer, f"Expected '{expected}' in the answer.")

        except Exception as e:
            logging.error(f"Error running query: {e}")
            self.fail(f"Query test failed due to exception: {e}")

    def test_questions(self):
        for case in self.test_cases:
            query = case['question']
            expected = case.get('expected', None)  # Some cases may not have an expected answer
            self.run_query_test(query, expected)



# if __name__ == '__main__':
#     # Configure the model and tests dynamically
#     DynamicRAGTest.setUpTestConfig(
#         model_class=RAGWithChroma,  # Dynamically specify the model class
#         collection_name="web_pages_2",  # Specify the collection name
#         test_cases=test_cases  # Provide the test cases
#     )
#     # Run the test suite
#     unittest.main()
