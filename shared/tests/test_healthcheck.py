import logging
import unittest
import json
import config
from shared.rest_client.healthcheck import HealthCheck


class CreateHealthCheckTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger()

        self.rest_client = HealthCheck()
        self.application = config.APPLICATION_NAME
        self.api = config.API + "/healthcheck"

    def setUp(self):
        self.logger.info("Test %s Started" % (self._testMethodName))

    def tearDown(self):
        self.logger.info("Test %s Finished" % (self._testMethodName))


    def test_healthcheck_payload(self):
        health_response = self.rest_client.get_healthCheck(self.api)

        self.assertEqual(health_response.status_code, 200)

        res_json = json.loads(health_response.content)

        self.assertEqual(res_json["status"], "OK")
        self.assertEqual(res_json["application"], self.application)
