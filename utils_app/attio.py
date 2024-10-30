import requests
from typing import Any

from constance import config

from log1.utils import write_exception


def attio_trigger(obj: Any, object_slug: str, request: Any) -> bool:
    try:
        ATTIO_URL = config.ATTIO_URL
        API_KEY = config.ATTIO_API_KEY

        # Vendor data extracted from the object
        vendor_data = {
            "vendor_company_name": obj.vendor.name,
            "vendor_company_id": str(obj.vendor.id),
            "vendor_company_query_name": obj.vendor.name.replace(" ", "").lower(),
            "vendor_created_by": obj.vendor.created_by if obj.vendor.created_by else "",
            "vendor_email": obj.vendor_contact.email if obj.vendor_contact.email else "",
            "vendor_number": str(obj.vendor_contact.number) if obj.vendor_contact.number else ""
        }

        # Prepare API request to Attio
        get_record_url = f"{ATTIO_URL}/objects/{object_slug}/records/query"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        # Filter to check for existing vendor record by company ID or query name
        filter_payload = {
            "filter": {
                "$or": [
                    {"vendor_company_id": str(vendor_data["vendor_company_id"])},
                    {"vendor_company_query_name": vendor_data["vendor_company_query_name"]}
                ]
            }
        }

        # Query Attio for existing vendor record
        get_response = requests.post(get_record_url, headers=headers, json=filter_payload)

        # Check if the request was successful
        if get_response.status_code != 200:
            write_exception("Error while fetching vendor record from Attio", request)
            return False

        response_data = get_response.json().get("data", [])

        # Check if a record was found
        if response_data:
            existing_record = response_data[0]  # Assuming the first record is relevant

            # Extract the nested values from the existing record
            existing_email = existing_record["values"].get("vendor_email", [{}])[0].get("value")
            existing_number = existing_record["values"].get("vendor_number", [{}])[0].get("value")

            # Check if email and number need updating
            if (not existing_email and not existing_number) and \
                    (vendor_data["vendor_email"] and vendor_data["vendor_number"]):
                # Prepare data to update the existing record
                update_payload = {
                    "data": {
                        "vendor_email": vendor_data["vendor_email"],
                        "vendor_number": vendor_data["vendor_number"]
                    }
                }
                update_url = f"{ATTIO_URL}/objects/{object_slug}/records/{existing_record['id']['record_id']}"
                update_response = requests.patch(update_url, headers=headers, json=update_payload)

                if update_response.status_code != 200:
                    write_exception("Error while updating Attio vendor record", request)
                    return False
            return True
        else:
            # If no existing record is found, create a new record
            create_payload = {
                "data": {"values": vendor_data}
            }
            create_record_url = f"{ATTIO_URL}/objects/{object_slug}/records"
            create_response = requests.post(create_record_url, headers=headers, json=create_payload)

            if create_response.status_code != 200:
                write_exception("Error while creating new Attio vendor record", request)
                return False

        return True

    except Exception as error:
        write_exception(str(error), request)
        return False
