
import os
import re
from typing import List

from rai.ingest.loaders.rai_loaders.BaseLoad import RaiLoaderDocument, RaiBaseLoader
from rai.raigents.base.BaseLoaders import register_loader


@register_loader('code')
class CodeDataLoader(RaiBaseLoader):
    cache: List[RaiLoaderDocument] = None

    def __init__(self, directory_path: str, file_path: str, extensions=None, metadata=None):
        super().__init__(file_path, metadata)
        self.directory_path = directory_path
        self.extensions = extensions or [".swift", ".py", ".java", ".kt", ".js", ".ts"]
        self.metadata = metadata if metadata is not None else {}

    def load(self):
        if self.cache:
            print(f"Returning Cached Loader: [ {self.directory_path} ]")
            return self.cache

        # Collect all programming files in the directory
        code_files = self._get_code_files()

        # Parse sections (functions/classes) from all files
        documents = []
        for file_path in code_files:
            file_metadata = {"filename": file_path, **self.metadata}
            language = self._get_language(file_path)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except UnicodeDecodeError:
                # Retry with a fallback encoding
                print(f"Warning: UTF-8 decode failed for {file_path}. Retrying with ISO-8859-1.")
                try:
                    with open(file_path, "r", encoding="ISO-8859-1") as f:
                        code = f.read()
                except Exception as e:
                    print(f"Error: Could not read {file_path} - {e}")
                    continue  # Skip problematic file

            sections = self._extract_sections(code, os.path.splitext(file_path)[-1])
            for section_text, section_type, start_line, end_line in sections:
                section_metadata = {
                    "filename": file_path,
                    "language": language,
                    "type": section_type,  # e.g., function, class, or class function
                    "start_line": start_line,
                    "end_line": end_line,
                    **self.metadata
                }
                doc = RaiLoaderDocument(page_content=section_text, metadata=section_metadata)
                documents.append(doc)

        self.cache = documents
        return self.cache

    def _get_code_files(self):
        """Recursively collects programming files based on the allowed extensions."""
        code_files = []
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.extensions):
                    code_files.append(os.path.join(root, file))
        return code_files
    def _get_language(self, file_path: str) -> str:
        """Infer the programming language based on file extension."""
        ext_to_language = {
            ".swift": "Swift",
            ".py": "Python",
            ".java": "Java",
            ".kt": "Kotlin",
            ".js": "JavaScript",
            ".ts": "TypeScript"
        }
        _, ext = os.path.splitext(file_path)
        return ext_to_language.get(ext.lower(), "Unknown")
    def _extract_sections(self, code: str, file_extension: str):
        """
        Extract both functions and classes from the code.
        Returns a list of tuples: (section_text, section_type, start_line, end_line).
        """
        if file_extension == ".swift":
            return self._extract_swift_sections(code)
        elif file_extension == ".py":
            return self._extract_python_sections(code)
        elif file_extension in [".java", ".kt"]:
            return self._extract_java_kotlin_sections(code)
        elif file_extension in [".js", ".ts"]:
            return self._extract_js_ts_sections(code)
        else:
            return []
    def _extract_swift_sections(self, code: str):
        """Extract Swift classes and functions."""
        return self._extract_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*{",
            method_pattern=r"func\s+\w+\s*\(.*?\)\s*(->.*)?\s*{"
        )
    def _extract_python_sections(self, code: str):
        """Extract Python classes and functions."""
        return self._extract_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*\(?.*?\)?:",
            method_pattern=r"def\s+\w+\s*\(.*?\)\s*:"
        )
    def _extract_java_kotlin_sections(self, code: str):
        """Extract Java/Kotlin classes and methods."""
        return self._extract_classes_and_methods(
            code,
            class_pattern=r"(public|private|protected)?\s*class\s+\w+\s*{",
            method_pattern=r"(public|private|protected|static)?\s+[\w<>\[\]]+\s+\w+\s*\(.*?\)\s*{"
        )
    def _extract_js_ts_sections(self, code: str):
        """Extract JavaScript/TypeScript classes, functions, and methods."""
        return self._extract_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*{",
            method_pattern=r"(function\s+\w+\s*\(.*?\)\s*{)|(const|let|var)\s+\w+\s*=\s*\(.*?\)\s*=>\s*{"
        )
    def _extract_classes_and_methods(self, code: str, class_pattern: str, method_pattern: str):
        """
        Extract both classes and their methods from the code.
        Returns a list of tuples: (section_text, section_type, start_line, end_line).
        """
        sections = []
        class_matches = list(re.finditer(class_pattern, code, re.MULTILINE))

        for class_match in class_matches:
            # Extract the full class block
            class_start = class_match.start()
            class_end = code.find("}", class_start) + 1  # Naive block detection
            class_text = code[class_start:class_end]
            class_start_line = code[:class_start].count("\n") + 1
            class_end_line = class_start_line + class_text.count("\n")

            # Add the class as a section
            sections.append((class_text, "class", class_start_line, class_end_line))

            # Extract methods within the class
            class_body = code[class_start:class_end]
            method_matches = re.finditer(method_pattern, class_body, re.MULTILINE)
            for method_match in method_matches:
                method_start = class_start + method_match.start()
                method_end = code.find("}", method_start) + 1
                method_text = code[method_start:method_end]
                method_start_line = code[:method_start].count("\n") + 1
                method_end_line = method_start_line + method_text.count("\n")

                sections.append((method_text, "class function", method_start_line, method_end_line))

        # Extract standalone methods (functions outside classes)
        standalone_methods = re.finditer(method_pattern, code, re.MULTILINE)
        for method_match in standalone_methods:
            if not any(class_start <= method_match.start() <= class_end for class_text, _, class_start, class_end in sections if _ == "class"):
                method_start = method_match.start()
                method_end = code.find("}", method_start) + 1
                method_text = code[method_start:method_end]
                method_start_line = code[:method_start].count("\n") + 1
                method_end_line = method_start_line + method_text.count("\n")

                sections.append((method_text, "function", method_start_line, method_end_line))

        return sections


if __name__ == "__main__":
    loader = CodeDataLoader(
        directory_path="/Users/chazzromeo/ChazzCoin/vsi-ios"
    )

    documents = loader.load()

    for doc in documents:
        print(f"File: {doc.metadata['filename']}")
        print(f"Language: {doc.metadata['language']}")
        print(f"Type: {doc.metadata['type']}")  # function, class, or class function
        print(f"Lines: {doc.metadata['start_line']}–{doc.metadata['end_line']}")
        print(doc.page_content)
        print("------")