import chromadb
from F.LOG import Log
from chromadb import Settings

from rai.internal.authority import AUTHORITY

Log = Log("Chromadb Database Client")


# Chroma
CHROMA_DATA_PATH = f"/chroma"
CHROMA_TENANT = AUTHORITY.get_env("CHROMA_TENANT", "")
CHROMA_DATABASE = AUTHORITY.get_env("CHROMA_DATABASE", "")
CHROMA_HTTP_HOST = AUTHORITY.get_env("DEFAULT_CHROMA_SERVER_HOST", "local") # "local" -OR- os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "local")
CHROMA_HTTP_PORT = int(AUTHORITY.get_env("DEFAULT_CHROMA_SERVER_PORT", 8000))

# Comma-separated list of header=value pairs
CHROMA_HTTP_HEADERS = AUTHORITY.get_env("CHROMA_HTTP_HEADERS", "")
if CHROMA_HTTP_HEADERS:
    CHROMA_HTTP_HEADERS = dict(
        [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
    )
else:
    CHROMA_HTTP_HEADERS = None
CHROMA_HTTP_SSL = AUTHORITY.get_env("CHROMA_HTTP_SSL", "false").lower() == "true"


class cChromadb:
    client = None
    def __init__(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):
        self.connect(host, port)

    def connect(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):

        if CHROMA_HTTP_HOST == "local":
            Log.w("\n--Chroma PersistentClient--\n")
            self.client = chromadb.PersistentClient(
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )
            Log.s("Successfully Connected to Local Chromadb Client.")
        else:
            Log.w("\n--Chroma HttpClient--\n")
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=chromadb.DEFAULT_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(allow_reset=True, anonymized_telemetry=False),
            )
            Log.w("Chroma Host:", CHROMA_HTTP_HOST)
            Log.w("Chroma Port:", CHROMA_HTTP_PORT)
            Log.w("Chroma Database:", CHROMA_DATABASE)
            Log.w("Chroma Tenant:", CHROMA_TENANT)
            Log.s("Successfully Connected to Remote Chromadb Client.")