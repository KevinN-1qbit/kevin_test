import logging
import requests
import json
import configparser

logger = logging.getLogger(__name__)
class DatabaseClient:
    def __init__(self, host_url):
        """
        Initialize the Database Manager.

        Args:
                host_url (str): Host url to database.
        """
        self.host_url = host_url

    def get_request(self, request_id, table, headers=None):
        """
        Sends GET request to CRUD server to get entry in table

        Args:
                request_id (str): Id of the entry in the table
                table (str): Name of the table to get entry from
        """
        logger.debug("GET Request")

        # Construct api endpoint
        api_endpoint = self.host_url + "read/" + request_id + "/" + table
        logger.debug(f"api_endpoint: {api_endpoint}")
        response = requests.get(
            api_endpoint, headers=headers, verify=True,
        )

        return response

    def post_request(self, req_body, headers=None):
        """
        Sends POST request to CRUD server to create new entry with given request body

        Args:
                req_body (dict): Dictionary containing info on entry to create.
        """
        logger.debug("POST Request")

        # Construct api endpoint
        api_endpoint = self.host_url + "create" 
        logger.debug(f"api_endpoint: {api_endpoint}")
        response = requests.post(
            api_endpoint,
            headers=headers,
            verify=True,
            data=json.dumps(req_body)
        )

        return response

    def put_request(self, req_body, headers=None):
        """
        Sends PUT request to CRUD server to update entry with given request body

        Args:
                req_body (dict): Dictionary containing info on entry to update.
        """
        logger.debug("PUT Request")

        # Construct api endpoint
        api_endpoint = self.host_url + "update"
        logger.debug(f"api_endpoint: {api_endpoint}")
        response = requests.put(
            api_endpoint,
            headers=headers,
            verify=True,
            data=json.dumps(req_body)
        )

        return response
