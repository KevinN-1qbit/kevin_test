import json


def update_dict_from_json(my_dict, json_path):
    """
    Update a dictionary with values from a JSON file.

    Args:
        my_dict (dict): The dictionary to update.
        json_path (str): The path to the JSON file.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the JSON file contains invalid syntax.
    """
    try:
        with open(json_path, "r") as json_file:
            data = json.load(json_file)
            for key, value in data.items():
                if key in my_dict:
                    my_dict[key] = value
    except FileNotFoundError:
        print(f"Error: The JSON file '{json_path}' does not exist.")
        raise
    except json.JSONDecodeError:
        print(f"Error: The JSON file '{json_path}' contains invalid syntax.")
        raise
