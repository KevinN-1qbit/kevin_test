from logging import StreamHandler

import requests
import json


class SlackHandler(StreamHandler):
    def __init__(self, slack_webhook_id):
        StreamHandler.__init__(self)
        self.slack_webhook_id = slack_webhook_id
        self._webhook_url_base = "https://hooks.slack.com/services/"

    def emit(self, record):
        msg = {"text": self.format(record)}
        payload = json.dumps(msg)
        webhook_url = self._webhook_url_base + self.slack_webhook_id
        requests.post(webhook_url, payload)
