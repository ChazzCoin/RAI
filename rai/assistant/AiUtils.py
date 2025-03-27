import tiktoken
from dataclasses import dataclass


@dataclass
class ModelTokenInfo:
    name: str
    max_tokens: int


class TokenProcessor:
    MODEL_TOKEN_LIMITS = {
        # Common GPT Models
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16385,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4o": 128000,  # GPT-4o
        "gpt-4.5": 128000,  # GPT-4.5
        "o1": 200000,
        "o1-pro": 200000,

        # Embedding Models
        "text-embedding-ada-002": 8191,
        "text-embedding-3-small": 8191,
        "text-embedding-3-large": 8191,

        # Additional User-defined Defaults
        "nomic-embed-text": 8192,  # Approximate embedding limit (standard nomic embeddings)
        "llama3.2:3b": 8192,  # Typical Llama 3 (3b) context length
        "qwen2.5:7b": 32768,  # Typical context limit for Qwen2.5 models
        "deepseek-r1:7b": 32768,  # DeepSeek typically has large context
        "o3-mini": 128000,  # Approximate limit for mini-OpenAI models (e.g., o3-mini)
    }

    DEFAULT_MODELS = {
        "DEFAULT_OPENAI_EMBEDDING": "text-embedding-3-large",
        "DEFAULT_OLLAMA_EMBEDDING": "nomic-embed-text",
        "DEFAULT_OPENAI": "gpt-4o",
        "DEFAULT_OLLAMA": "llama3.2:3b",
        "DEFAULT_OPENAI_FUNCTION": "o3-mini",
        "DEFAULT_OLLAMA_FUNCTION": "qwen2.5:7b",
        "DEFAULT_OPENAI_FORMAT": "o3-mini",
        "DEFAULT_OLLAMA_FORMAT": "llama3.2:3b",
        "DEFAULT_OPENAI_REASONING": "o3-mini",
        "DEFAULT_OLLAMA_REASONING": "deepseek-r1:7b",
    }

    @staticmethod
    def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding.encode(text))

    @classmethod
    def check_token_limit(cls, text: str, model_name: str) -> dict:
        if model_name in cls.DEFAULT_MODELS:
            model_name = cls.DEFAULT_MODELS[model_name]

        tokens = cls.count_tokens(text, model_name)
        limit = cls.MODEL_TOKEN_LIMITS.get(model_name)

        if limit is None:
            raise ValueError(f"Token limit for model '{model_name}' is not defined.")

        within_limit = tokens <= limit
        return {
            "model": model_name,
            "tokens": tokens,
            "limit": limit,
            "within_limit": within_limit,
            "tokens_over_limit": max(0, tokens - limit)
        }


# Example usage
if __name__ == "__main__":
    sample_text = "This is an example sentence." * 1000

    # Check various default models
    models_to_check = [
        "DEFAULT_OPENAI_EMBEDDING",
        "DEFAULT_OLLAMA_EMBEDDING",
        "DEFAULT_OPENAI",
        "DEFAULT_OLLAMA",
        "DEFAULT_OPENAI_FUNCTION",
        "DEFAULT_OLLAMA_FUNCTION",
        "DEFAULT_OPENAI_FORMAT",
        "DEFAULT_OLLAMA_FORMAT",
        "DEFAULT_OPENAI_REASONING",
        "DEFAULT_OLLAMA_REASONING",
    ]

    for model_key in models_to_check:
        result = Tokenizer.check_token_limit(sample_text, model_key)
        print(f"Model: {model_key} ({result['model']})")
        print(f"  - Tokens: {result['tokens']}")
        print(f"  - Limit: {result['limit']}")
        if result['within_limit']:
            print("  ✅ Within token limit.\n")
        else:
            print(f"  ❌ Exceeds token limit by {result['tokens_over_limit']} tokens.\n")
