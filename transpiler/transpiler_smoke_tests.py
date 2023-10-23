import unittest
import time
import config
from shared.tests.test_healthcheck import CreateHealthCheckTestCase
from transpiler.tests.test_transpile import CreateTranspileTestCase


def suite():
    smoke_tests = unittest.TestSuite()

    # healthcheck
    smoke_tests.addTest(CreateHealthCheckTestCase("test_healthcheck_payload"))

    # transpiler
    smoke_tests.addTest(CreateTranspileTestCase("test_post_transpile_success_response"))
    smoke_tests.addTest(CreateTranspileTestCase("test_post_transpile_invalid_body"))
    smoke_tests.addTest(CreateTranspileTestCase("test_get_transpile_unknown_request_404"))
    smoke_tests.addTest(CreateTranspileTestCase("test_transpile_invalid_file_path"))
    smoke_tests.addTest(CreateTranspileTestCase("test_end_to_end_transpile"))

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