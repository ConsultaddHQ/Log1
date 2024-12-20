import csv
from typing import Any

import requests
from constance import config
from django.core.management import BaseCommand

from marketing.models import Submission, Interview
from utils_app.attio import attio_trigger

# API_KEY = 'ea2a0a86dc88a3d5175d3bf16cc620e4374216a4d9588457700c19ca03fc4809'
API_KEY = config.ATTIO_API_KEY

ATTIO_URL = "https://api.attio.com/v2"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {API_KEY}"
}


def create_objects():
    data = {
        "data": {
            "singular_noun": "Log1 Vendor Company",
            "api_slug": "log1_vendor_company",
            "plural_noun": "Log1 Vendor Companies"
        }
    }
    response = requests.post(f"{ATTIO_URL}/objects", headers=headers, json=data)
    return response


def add_attribute(object_id: str) -> dict:
    attribute_data = [
            {
                "type": "text",
                "is_required": True,
                "is_unique": True,
                "is_multiselect": False,
                "title": "Vendor Company ID",
                "api_slug": "vendor_company_id",
                "description": "This field contains unique vendor company id",
                "config": {}
            },
            {
                "type": "text",
                "is_required": True,
                "is_unique": False,
                "is_multiselect": False,
                "title": "Vendor Company",
                "api_slug": "vendor_company_name",
                "description": "This field contains vendor company name",
                "config": {}
            },
            {
                "type": "text",
                "is_required": True,
                "is_unique": False,
                "is_multiselect": False,
                "title": "Company Query Name",
                "api_slug": "vendor_company_query_name",
                "description": "This field contains vendor company query name",
                "config": {}
            },
            {
                "type": "text",
                "is_required": False,
                "is_unique": False,
                "is_multiselect": False,
                "title": "Vendor Email",
                "api_slug": "vendor_email",
                "description": "This field contains vendor email information",
                "config": {}
            },
            {
                "type": "text",
                "is_required": False,
                "is_unique": False,
                "is_multiselect": False,
                "title": "Vendor Number",
                "api_slug": "vendor_number",
                "description": "This field contains vendor number information",
                "config": {}
            },
            {
                "type": "text",
                "is_required": True,
                "is_unique": False,
                "is_multiselect": False,
                "title": "Created By",
                "api_slug": "vendor_created_by",
                "description": "This field contains information of person who added vendor details",
                "config": {}
            }
        ]
    attributes = {}
    for item in attribute_data:
        payload = {
            "data": item
        }
        response = requests.post(f'{ATTIO_URL}/objects/{object_id}/attributes', headers=headers, json=payload)
        if response.status_code != 200:
            return {}
        attribute_id = response.json().get('data', {}).get('id').get('attribute_id')
        api_slug = response.json().get('data').get('api_slug', {})

        attributes.update({api_slug: attribute_id})
    return attributes


def add_records(attribute_map, object_id, data):
    api_endpoint = f"{ATTIO_URL}/objects/{object_id}/records"
    api_1_count = api_2_count = 0
    for item in data:
        record_data = dict()
        for key, value in attribute_map.items():
            record_data.update({value: item.get(key)})
        payload = {
            "data": {
                "values": record_data
            }
        }
        response = requests.post(api_endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            api_key = 'a182ef716c712d1eec561e9bc89b5dabde0ca0de8adbdfaaa20b3d6005765693'
            headers.update({"authorization": f"Bearer {api_key}"})
            response = requests.post(api_endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                api_1_count += 1
                print(api_1_count, "Done using API 1 access code\n")
        else:
            api_2_count += 1
            print(print(api_2_count), " Done using API 2 access code\n")
    return True


def create_list():

    payload = {
        "data": {
            "workspace_access": "full-access",
            "name": "TekSystem",
            "api_slug": "teksystem",
            "parent_object": "log1_vendor_company",
            # "workspace_member_access": [
            #     # {
            #     #     "workspace_member_id": "4663e4b7-21a6-488d-aa34-d03fe9a64975", "level": "full-access"
            #     # }
            # ]
        }
    }
    response = requests.post(f"{ATTIO_URL}/lists", json=payload, headers=headers)
    return response


def add_new_entries():

    payload = {
        "data": {
            "parent_record_id": "18938ca8-9349-4d8a-b799-d8f893df0ce1",
            "parent_object": "log1_vendor_company",
            "entry_values": {
                "client": "HCL",
                "job_title": "Software Engineer",
                "rate": "79",
                "final_status": "In Process"
    }}}
    response = requests.post(f"{ATTIO_URL}/lists/teksystems/entries", json=payload, headers=headers)
    return response


def get_new_entries():
    filter_payload = {
        "filter":
            {"submission_id": str(6789)}

    }
    get_entry_url = f"{ATTIO_URL}/lists/teksystems/entries/query"
    get_response = requests.post(get_entry_url, headers=headers, json=filter_payload)
    return True


class Command(BaseCommand):
    def handle(self, *args, **options):
        record_id = "a4628616-cbc2-45c6-a203-56b909169c45"
        entry_id = "0033eed4-0a0f-4077-8244-cbb3f88a9628"
        update_url = f"{ATTIO_URL}/lists/teksystems/entries/{entry_id}"
        data = {
            "entry_values": {
                "parent_record_id": "007af99a-12d9-4502-98b3-9e71646dafbc",
                "parent_object": "log1_vendor_company",
                "rate": 70,
                "client": "Roche Pharmaceuticals",
                "submission_id": "113149",
                "job_title": "Python Developer",
                "final_status": "Offer"
            }
        }
        update_response = requests.put(update_url, headers=headers, json=data)
