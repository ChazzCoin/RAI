import os
import pandas as pd
from F.LOG import Log
from langchain_community.document_loaders import CSVLoader, UnstructuredExcelLoader
from rai.data.loaders.rai_loaders.LastResortDataLoader import LastResortDataLoader
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument, RaiBaseLoader
Log = Log("TableDataLoader")

class TableDataLoader(RaiBaseLoader):

    def __init__(self, file_path: str, metadata: dict = {'image': ''}):
        super().__init__(file_path, metadata)
        self._validate_file_path()

    def _validate_file_path(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not (self.file_path.endswith('.csv') or self.file_path.endswith(('.xls', '.xlsx'))):
            raise ValueError("Unsupported file type. Only CSV and Excel files are allowed.")

    def load(self) -> [str]:
        """
        Loads and extracts the text from the table file (CSV or Excel).
        The output is a list of formatted strings representing each row,
        useful for embeddings, querying, and AI processing.
        """
        try:
            if self.cache:
                Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
                return self.cache
            if self.file_path.endswith('.csv'):
                df = pd.read_csv(self.file_path)
            else:
                df = pd.read_excel(self.file_path)
            formatted_data = self.format_dataframe(df)
            if formatted_data:
                self.cache = RaiLoaderDocument.generate_documents(formatted_data, metadata=self.metadata)
                return self.cache
            else:
                raise ValueError("Dataframe is empty or could not be processed.")
        except Exception as e:
            # Fallback to alternative loaders if the primary method fails
            Log.w("TableLoader Failed, falling back.", e)
            if self.file_path.endswith('.csv'):
                loader = CSVLoader(self.file_path)
            else:
                loader = UnstructuredExcelLoader(self.file_path)
            if not self.verify_loader_data(loader):
                # Fallback to LastResortLoader if all else fails
                Log.w("TableLoader Failed, last resorting.", e)
                loader = LastResortDataLoader(self.file_path, metadata=self.metadata)
            self.cache = loader.load()
            return self.cache

    @staticmethod
    def format_dataframe(df: pd.DataFrame) -> [str]:
        """
        Formats the DataFrame into a list of strings,
        each representing a row in a consistent and structured format.
        """
        Log.i("Formatting Dataframe...")
        formatted_rows = []
        headers = df.columns.tolist()
        header_str = " | ".join(headers)

        # Add headers as the first line to provide context for embeddings.
        formatted_rows.append(f"Headers: {header_str}")

        for index, row in df.iterrows():
            row_data = [f"{header}: {str(value)}" for header, value in zip(headers, row)]
            row_str = " | ".join(row_data)
            formatted_rows.append(row_str)

        return formatted_rows