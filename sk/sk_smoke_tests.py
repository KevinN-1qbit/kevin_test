import unittest
import time
import config
from shared.tests.test_healthcheck import CreateHealthCheckTestCase
from sk.tests.test_decompose import CreateDecomposeTestCase


def suite():
    smoke_tests = unittest.TestSuite()

    # healthcheck
    smoke_tests.addTest(CreateHealthCheckTestCase("test_healthcheck_payload"))

    # decompose
    smoke_tests.addTest(CreateDecomposeTestCase("test_post_decompose_success_response"))
    smoke_tests.addTest(CreateDecomposeTestCase("test_post_decompose_invalid_body"))
    smoke_tests.addTest(CreateDecomposeTestCase("test_get_decompose_unknown_request_404"))
    smoke_tests.addTest(CreateDecomposeTestCase("test_decompose_invalid_circuit_path"))
    smoke_tests.addTest(CreateDecomposeTestCase("test_end_to_end_decompose"))

    return smoke_tests


if __name__ == "__main__":
    runner = unittest.TextTestRunner()

    start_time = time.time()
    test_result = runner.run(suite())
    execution_time = round(time.time() - start_time, 2)

    test_status = "FAILED"
    if test_result.wasSuccessful():
        test_status = "OK"

    print(f"Execution Time={execution_time}, {test_status} ")

    exit(not test_result.wasSuccessful())
