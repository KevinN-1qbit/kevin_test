import logging
import unittest
import json
import time
import config
from shared.rest_client.qarrot_client import QarrotClient


class CreateGenerateReportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger()
        self.rest_client = QarrotClient()
        self.api = config.API + config.END_POINT

    def setUp(self):
        self.logger.info("Test %s Started" % (self._testMethodName))

        with open(config.PAYLOAD, 'r') as file:
            json_data = file.read()

        self.test_request_body = json.loads(json_data)
        self.test_header = {"Content-Type": "application/json"}


    def tearDown(self):
        self.logger.info("Test %s Finished" % (self._testMethodName))


    def test_post_generate_report_success_response(self):
        response = self.rest_client.post_request(
            self.test_request_body, self.api, self.test_header
        )
        result = json.loads(response.content)

        expected_num_physical_qubits = 443361

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["summary"]["num_physical_qubits"], expected_num_physical_qubits)


    def test_post_generate_report_invalid_body(self):
        test_request = self.test_request_body

        # Remove required parameter
        test_request.pop("circuit")
        response = self.rest_client.post_request(
            test_request, self.api, self.test_header
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()[0]["msg"], "field required")

    def test_post_generate_report_invalid_500(self):
        test_request = self.test_request_body

        # set invalid value
        test_request["pre"]["magic_state_factory"]["num_distillation_units"] = []
        response = self.rest_client.post_request(
            test_request, self.api, self.test_header
        )

        self.assertEqual(response.status_code, 500)
