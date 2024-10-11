from rai import app

class EmbeddingsModels:
    OpenAI = "text-embedding-ada-002"
    Ollama = "nomic-embed-text"

class OpenAI:
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    GPT_4 = "gpt-4"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "gpt-4o-mini"
    URL = 'https://api.openai.com/v1'
    KEY = ""

    def __init__(self):
        self.KEY = app.state.config.OPENAI_API_KEY

    def route(self, route=""):
        return f"http://{self.URL}{route}"

    def default_model(self, override:str=None):
        return app.state.config.DEFAULT_OPENAI_MODEL if not override else override

    def embeddings_model(self):
        return app.state.config.DEFAULT_OPENAI_EMBEDDING_MODEL

class Ollama:
    LLAMA3_8B_latest = "llama3:latest"
    LLAMA_CODER_34B = "codellama:34b"
    IP = "localhost"
    PORT = "11434"

    def __init__(self):
        self.PORT = app.state.config.OLLAMA_PORT
        self.IP = app.state.config.OLLAMA_HOST

    def route(self, route=""):
        return f"http://{self.IP}:{self.PORT}{route}"

    def default_model(self, override:str=None):
        return app.state.config.DEFAULT_OLLAMA_MODEL if not override else override

    def embeddings_model(self):
        return app.state.config.DEFAULT_OLLAMA_EMBEDDING_MODEL

class ApiEngines:
    Embedding_MODELS = EmbeddingsModels()
    OPENAI = OpenAI()
    OLLAMA = Ollama()

