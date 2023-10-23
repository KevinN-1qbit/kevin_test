import os

# Maximum timeout and retry settings
TIMEOUT_MAX = 20
RETRY_TIME = 10
MAX_RETRIES = 5

# Application details
API = os.environ.get("API_URL")
APPLICATION_NAME = "QARENode"
END_POINT = "/generate_report"
PAYLOAD = "qare/data/payload.json"