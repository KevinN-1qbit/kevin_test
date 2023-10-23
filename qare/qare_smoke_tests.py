import unittest
import time
import config
from shared.tests.test_healthcheck import CreateHealthCheckTestCase
from qare.tests.test_generate_report import CreateGenerateReportTestCase


def suite():
    smoke_tests = unittest.TestSuite()

    # healthcheck
    smoke_tests.addTest(CreateHealthCheckTestCase("test_healthcheck_payload"))

    # generate_report
    smoke_tests.addTest(CreateGenerateReportTestCase("test_post_generate_report_success_response"))
    smoke_tests.addTest(CreateGenerateReportTestCase("test_post_generate_report_invalid_500"))
    smoke_tests.addTest(CreateGenerateReportTestCase("test_post_generate_report_invalid_body"))

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
