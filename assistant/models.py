from config import env

class EmbeddingsModels:
    OpenAI = "text-embedding-ada-002"
    Ollama = "nomic-embed-text"

class OpenAI:
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    GPT_4 = "gpt-4"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "gpt-4o-mini"
    URL = env("OPENAI_URL", 'https://api.openai.com/v1')
    KEY = env("OPENAI_API_KEY")

    def route(self, route=""):
        return f"http://{self.URL}{route}"

    def default_model(self, override:str=None):
        return env("DEFAULT_OPENAI_MODEL", override if override else self.GPT_4o_mini)

    def embeddings_model(self):
        return env("DEFAULT_OPENAI_EMBEDDING_MODEL", EmbeddingsModels.OpenAI)

class Ollama:
    LLAMA3_8B_latest = "llama3:latest"
    LLAMA_CODER_34B = "codellama:34b"
    IP = env("OLLAMA_HOST", 'localhost')
    PORT = env("OLLAMA_PORT", 11434)

    def route(self, route=""):
        return f"http://{self.IP}:{self.PORT}{route}"

    def default_model(self, override:str=None):
        return env("DEFAULT_OLLAMA_MODEL", override if override else self.LLAMA3_8B_latest)

    def embeddings_model(self):
        return env("DEFAULT_OLLAMA_EMBEDDING_MODEL", EmbeddingsModels.Ollama)

class ApiEngines:
    Embedding_MODELS = EmbeddingsModels()
    OPENAI = OpenAI()
    OLLAMA = Ollama()

