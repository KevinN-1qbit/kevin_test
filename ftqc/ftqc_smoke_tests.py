import unittest
import time
import config
from shared.tests.test_healthcheck import CreateHealthCheckTestCase
from ftqc.tests.test_emulate import CreateEmulateTestCase


def suite():
    smoke_tests = unittest.TestSuite()

    # healthcheck
    smoke_tests.addTest(CreateHealthCheckTestCase("test_healthcheck_payload"))

    # emulate
    smoke_tests.addTest(CreateEmulateTestCase("test_post_emulate_success_response"))
    smoke_tests.addTest(CreateEmulateTestCase("test_post_emulate_invalid_body"))
    smoke_tests.addTest(CreateEmulateTestCase("test_get_emulate_unknown_request_404"))
    smoke_tests.addTest(CreateEmulateTestCase("test_emulate_invalid_number_of_cores"))
    smoke_tests.addTest(CreateEmulateTestCase("test_end_to_end_emulate"))

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
