import unittest
import time
import config
from shared.tests.test_healthcheck import CreateHealthCheckTestCase
from pre.tests.test_estimate import CreateEstimateTestCase


def suite():
    smoke_tests = unittest.TestSuite()

    # healthcheck
    smoke_tests.addTest(CreateHealthCheckTestCase("test_healthcheck_payload"))

    # estimate
    smoke_tests.addTest(CreateEstimateTestCase("test_post_estimate_success_response"))
    smoke_tests.addTest(CreateEstimateTestCase("test_post_estimate_invalid_body"))
    smoke_tests.addTest(CreateEstimateTestCase("test_get_estimate_unknown_request_404"))
    smoke_tests.addTest(CreateEstimateTestCase("test_estimate_invalid_total_num_operations"))
    smoke_tests.addTest(CreateEstimateTestCase("test_end_to_end_estimate"))

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
