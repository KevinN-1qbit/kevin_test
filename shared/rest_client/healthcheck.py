import logging
import requests
import json

import config


logger = logging.getLogger()


class HealthCheck:
    TIMEOUT_MAX = config.TIMEOUT_MAX

    @classmethod
    def get_healthCheck(self, api_endpoint, headers=None):
        logger.debug("GET HealthCheck")
        logger.debug("URL: " + api_endpoint)

        response = requests.get(
            api_endpoint, headers=headers, verify=True, timeout=HealthCheck.TIMEOUT_MAX
        )

        return response
