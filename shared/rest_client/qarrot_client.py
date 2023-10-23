import logging
import requests
import json
import config

logger = logging.getLogger()

class QarrotClient:
    TIMEOUT_MAX = config.TIMEOUT_MAX

    @classmethod
    def get_request(self, api_endpoint, headers=None):
        logger.debug("GET Request")
        logger.debug("URL: " + api_endpoint)

        response = requests.get(
            api_endpoint, headers=headers, verify=True, timeout=QarrotClient.TIMEOUT_MAX
        )

        return response

    @classmethod
    def post_request(self, req_body, api_endpoint, headers=None):
        logger.debug("POST Request")
        logger.debug("URL: " + api_endpoint)

        response = requests.post(
            api_endpoint,
            headers=headers,
            verify=True,
            data=json.dumps(req_body),
            timeout=QarrotClient.TIMEOUT_MAX,
        )

        return response

    @classmethod
    def post_request_file(self, file_path, api_endpoint, headers=None):
        logger.debug("POST Request File")
        logger.debug("URL: " + api_endpoint)

        files = {"file": (file_path, open(file_path, 'rb'), "application/octet-stream")}

        response = requests.post(api_endpoint, files=files, headers=headers)

        return response
