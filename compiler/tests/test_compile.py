import logging
import unittest
import json
import time
import config
import os
from shared.rest_client.qarrot_client import QarrotClient


class CreateCompileTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger()
        self.rest_client = QarrotClient()
        self.api = config.API + config.END_POINT
        self.upload_api = config.UPLOAD_API

        # Set up test input files
        self.input_path = "compiler/data/compiler_input_test.txt"
        upload_response = self.rest_client.post_request_file(self.input_path, self.upload_api)
        self.test_circuit_path = json.loads(upload_response.content)["fileName"]

    def setUp(self):
        self.logger.info("Test %s Started" % (self._testMethodName))

        with open(config.PAYLOAD, 'r') as file:
            json_data = file.read()

        self.test_request_body = json.loads(json_data)
        self.test_header = {"Content-Type": "application/json"}

        self.test_request_body["circuit_path"] = self.test_circuit_path


    def tearDown(self):
        self.logger.info("Test %s Finished" % (self._testMethodName))


    def test_post_compile_success_response(self):
        response = self.rest_client.post_request(
            self.test_request_body, self.api, self.test_header
        )
        status = json.loads(response.content)["status"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(status, "waiting")


    def test_post_compile_invalid_body(self):
        test_request = self.test_request_body

        # Remove required parameter
        test_request.pop("circuit_path")
        response = self.rest_client.post_request(
            test_request, self.api, self.test_header
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()[0]["msg"], "field required")


    def test_get_compile_unknown_request_404(self):
        unknown_request_id = "unknown_request_id"

        get_request = self.api + "/" + unknown_request_id

        response = self.rest_client.get_request(get_request, self.test_header)
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(result["detail"], f"Invalid request id: {unknown_request_id}.")


    def test_compile_invalid_circuit_path(self):
        test_request = self.test_request_body

        test_request["circuit_path"] = "invalid_path"
        # Post request
        post_decompose_response = self.rest_client.post_request(
            test_request, self.api, self.test_header
        )

        request_id = json.loads(post_decompose_response.content)["request_id"]
        retries = 0

        get_request = self.api + "/" + request_id

        while retries <= config.MAX_RETRIES:
            response = self.rest_client.get_request(get_request, self.test_header)

            result = json.loads(response.content)

            status = result["status"]

            if status == "failed":
                break

            if status == "done":
                self.fail("Test should have failed")

            else:
                wait = (retries + 1) * config.RETRY_TIME
                print(
                    "Request still calculating! Waiting %s secs and re-trying..." % wait
                )
                time.sleep(wait)

                retries += 1

        else:
            self.fail("Max retries reached")

        self.assertEqual(status, "failed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["request_id"], request_id)


    def test_end_to_end_compile(self):
        # Post request
        post_compile_response = self.rest_client.post_request(
            self.test_request_body, self.api, self.test_header
        )
        expected_number_of_ticks = 5290.0

        request_id = json.loads(post_compile_response.content)["request_id"]
        retries = 0

        get_request = self.api + "/" + request_id

        while retries <= config.MAX_RETRIES:
            response = self.rest_client.get_request(get_request, self.test_header)

            result = json.loads(response.content)

            status = result["status"]

            if status == "done":
                break

            if status == "failed":
                self.fail("End to end test failed")

            else:
                wait = (retries + 1) * config.RETRY_TIME
                print(
                    "Request still calculating! Waiting %s secs and re-trying..." % wait
                )
                time.sleep(wait)

                retries += 1

        else:
            self.fail("Max retries reached")

        self.assertEqual(status, "done")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["request_id"], request_id)
        self.assertEqual(result["schedule_metadata"]["expected_number_of_ticks"], expected_number_of_ticks)
