


HEADERS = {'Content-Type': 'application/json'}

RESPONSE_FORMAT = {"type": "text"}


CHAT_MESSAGE_OPENAI = lambda system, user: [
      {"role": "system", "content": system },
      {"role": "user", "content": user }
    ]

CHAT_MESSAGE_OLLAMA = lambda system, user, model: {
        "model": model,
        "messages": [
            { "role": "system", "content": system },
            { "role": "user", "content": user }
        ],
        "stream": False
    }