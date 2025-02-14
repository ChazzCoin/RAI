


class AiModels:

    DEFAULT_OPENAI_EMBEDDING = "text-embedding-3-large"
    DEFAULT_OLLAMA_EMBEDDING = "nomic-embed-text"

    DEFAULT_OPENAI = "gpt-4o"
    DEFAULT_OLLAMA = "llama3.2:latest"

    DEFAULT_OPENAI_FUNCTION = "o3-mini"
    DEFAULT_OLLAMA_FUNCTION = "llama3.2:latest"

    DEFAULT_OPENAI_FORMAT = "o3-mini"
    DEFAULT_OLLAMA_FORMAT = "llama3.2:latest"

    class OpenAi:
        # GPT-4 Series
        GPT4o = "gpt-4o"
        GPT4oMini = "gpt-4o-mini"
        GPT4_TURBO = "gpt-4-turbo"
        GPT4_8K = "gpt-4-8k"
        GPT4_32K = "gpt-4-32k"
        # GPT-3.5 Series
        GPT3_5_TURBO = "gpt-3.5-turbo"
        GPT3_5_TURBO_16K = "gpt-3.5-turbo-16k"
        # o1 Series
        O1_PREVIEW = "o1-preview"
        O1_MINI = "o1-mini"
        O3_HIGH = "o3-high"
        O3_MINI = "o3-mini"

        class Embed:
            DEFAULT = "text-embedding-ada-002"
            TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"  # Smaller, efficient model
            TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"  # Larger, more powerful model

    class Ollama:
        # Llama Series
        LLAMA3_LATEST = "llama3:latest"
        LLAMA3_2 = "llama3.2"
        LLAMA3_3 = "llama3.3"       # Latest version :contentReference[oaicite:3]{index=3}
        # Phi Series
        PHI3 = "phi3"               # Available model :contentReference[oaicite:4]{index=4}
        # Mistral Series
        MISTRAL = "mistral"         # Available model :contentReference[oaicite:5]{index=5}
        # Gemma Series
        GEMMA2 = "gemma2"           # Available model :contentReference[oaicite:6]{index=6}
        GEMMA7B = "gemma:7b"        # 7B parameter model :contentReference[oaicite:7]{index=7}
        # Qwen2 Math Series
        QWEN2_MATH = "qwen2-math"   # Specialized math language model :contentReference[oaicite:8]{index=8}
        DEEPSEEK_R1_7B = "deepseek-r1:7b"

        class Embed:
            DEFAULT = "nomic-embed-text"
            MXBAI_EMBED_LARGE = "mxbai-embed-large"  # Versatile model with 334M parameters
            ALL_MINILM = "all-minilm"  # Compact model with 22M parameters
