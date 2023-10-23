import os

# Maximum timeout and retry settings
TIMEOUT_MAX = 20
RETRY_TIME = 10
MAX_RETRIES = 5

# Application details
API = os.environ.get("API_URL")
UPLOAD_API = os.environ.get("UPLOAD_API_URL")
APPLICATION_NAME = "transpiler"
END_POINT = "/transpile"
PAYLOAD = "transpiler/data/payload.json"
