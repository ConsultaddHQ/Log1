import requests
from typing import Any, Dict
from celery import shared_task

from constance import config
from log1.utils import write_exception

ATTIO_URL = config.ATTIO_URL
API_KEY = config.ATTIO_API_KEY
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


@shared_task
def attio_trigger(obj: Any, object_slug: str, request: Any = None) -> bool:
    """
    Trigger the process to synchronize vendor and interview data with Attio.
    param obj: Object containing the submission and other related details.
    param object_slug: The Attio object slug to interact with.
    return: Boolean indicating success or failure.
    """
    try:
        submission_obj = obj.submission
        vendor_data = _extract_vendor_data(submission_obj)

        # Check for existing vendor record
        vendor_record_id = _get_or_update_vendor_record(object_slug, vendor_data)
        if not vendor_record_id:
            write_exception("Failed to get or create vendor record.", request)
            return False

        # Update or create list entry
        vendor_list_data = _prepare_vendor_list_data(obj, submission_obj, vendor_record_id, object_slug)
        if not _update_or_create_list_entry(vendor_list_data):
            write_exception("Failed to update or create vendor list entry.", request)
            return False

        return True

    except Exception as error:
        write_exception(str(error), request)
        return False


def _extract_vendor_data(submission_obj: Any) -> Dict:
    """Extract vendor-related data from the submission object."""
    return {
        "vendor_company_name": submission_obj.vendor.name,
        "vendor_company_id": str(submission_obj.vendor.id),
        "vendor_email": submission_obj.vendor_contact.email or "",
        "vendor_created_by": submission_obj.vendor.created_by or "",
        "vendor_number": str(submission_obj.vendor_contact.number) or "",
        "vendor_company_query_name": submission_obj.vendor.name.replace(" ", "").lower()
    }


def _get_or_update_vendor_record(object_slug: str, vendor_data: Dict, request: Any = None) -> Any:
    """Query, update, or create a vendor record in Attio."""
    get_record_url = f"{ATTIO_URL}/objects/{object_slug}/records/query"
    filter_payload = {
        "filter": {
            "$or": [
                {"vendor_company_id": vendor_data["vendor_company_id"]},
                {"vendor_company_query_name": vendor_data["vendor_company_query_name"]}
            ]
        }
    }

    response = requests.post(get_record_url, headers=HEADERS, json=filter_payload)
    if response.status_code != 200:
        write_exception("Error fetching vendor record from Attio.", request)
        return None

    response_data = response.json().get("data", [])
    if response_data:
        existing_record = response_data[0].get("values")
        vendor_record_id = existing_record.get("record_id", [{}])[0].get("value")

        if record_needs_update(existing_record, vendor_data):
            update_url = f"{ATTIO_URL}/objects/{object_slug}/records/{vendor_record_id}"
            update_payload = {
                "data": {
                    "values": {
                        "vendor_email": vendor_data["vendor_email"],
                        "vendor_number": vendor_data["vendor_number"]
                    }
                }
            }
            update_response = requests.patch(update_url, headers=HEADERS, json=update_payload)
            if update_response.status_code != 200:
                write_exception("Error updating vendor record.", request)
                return None
        return vendor_record_id

    # Create a new record if none exists
    create_payload = {"data": {"values": vendor_data}}
    create_record_url = f"{ATTIO_URL}/objects/{object_slug}/records"
    create_response = requests.post(create_record_url, headers=HEADERS, json=create_payload)
    if create_response.status_code != 200:
        write_exception("Error creating vendor record.", request)
        return None
    return create_response.json().get("data", {}).get("id").get('record_id')


def record_needs_update(existing_record: Dict, vendor_data: Dict) -> bool:
    """Check if the vendor record needs to be updated."""
    existing_email = existing_record.get("vendor_email", [{}])[0].get("value", "")
    existing_number = existing_record.get("vendor_number", [{}])[0].get("value", "")

    return \
        (not existing_email and vendor_data["vendor_email"]) or (not existing_number and vendor_data["vendor_number"])


def _prepare_vendor_list_data(obj: Any, submission_obj: Any, vendor_record_id: str, object_slug: str) -> Dict:
    """Prepare data for the vendor list entry."""
    return {
        "parent_record_id": str(vendor_record_id),
        "parent_object": object_slug,
        "entry_values": {
            "rate": str(submission_obj.rate),
            "client": submission_obj.client,
            "submission_id": str(submission_obj.id),
            "job_title": submission_obj.lead.job_title,
            "consultant_name": submission_obj.consultant.name,
            "consultant_email": submission_obj.consultant.email,
            "final_status": obj.get_status_display()
            if obj.get_status_display() in ["Offer", "Cancelled", "Failed"] else "In Process"
        }
    }


def _update_or_create_list_entry(vendor_list_data: Dict, request: Any = None) -> bool:
    """Update or create a vendor list entry in Attio."""
    vendor_list_name = config.VENDOR_LIST_NAME
    get_entry_url = f"{ATTIO_URL}/lists/{vendor_list_name}/entries/query"
    filter_payload = {"filter": {"submission_id": vendor_list_data["entry_values"]["submission_id"]}}

    response = requests.post(get_entry_url, headers=HEADERS, json=filter_payload)
    if response.status_code != 200:
        write_exception("Error fetching vendor list entry from Attio.", request)
        return False

    list_data = response.json().get("data", [])
    list_payload = {"data": vendor_list_data}

    if list_data:
        entry_id = list_data[0].get('id').get('entry_id')
        list_payload.get("data").pop("parent_object")
        list_payload.get("data").pop("parent_record_id")
        update_url = f"{ATTIO_URL}/lists/{vendor_list_name}/entries/{entry_id}"
        update_response = requests.put(update_url, headers=HEADERS, json=list_payload)
        if update_response.status_code != 200:
            write_exception("Error updating vendor list entry.", request)
            return False
    else:
        create_url = f"{ATTIO_URL}/lists/{vendor_list_name}/entries"
        create_response = requests.post(create_url, headers=HEADERS, json=list_payload)
        if create_response.status_code != 200:
            write_exception("Error creating vendor list entry.", request)
            return False

    return True


@shared_task
def _remove_list_entry(obj_id: int, request: Any = None) -> bool:
    try:
        vendor_list_name = config.VENDOR_LIST_NAME
        get_entry_url = f"{ATTIO_URL}/lists/{vendor_list_name}/entries/query"
        filter_payload = {"filter": {"submission_id": obj_id}}
        response = requests.post(get_entry_url, headers=HEADERS, json=filter_payload)
        if response.status_code != 200:
            write_exception("Error fetching vendor list entry from Attio.", request)
            return False

        list_data = response.json().get("data", [])
        if list_data:
            entry_id = list_data[0].get('id').get('entry_id')
            remove_entry_url = f"{ATTIO_URL}/lists/{vendor_list_name}/entries/{entry_id}"
            response = requests.delete(remove_entry_url, headers=HEADERS)
            if response.status_code != 200:
                write_exception("Error removing list entry from Attio.", request)
                return False
            return True
        else:
            return True
    except Exception as error:
        write_exception(str(error), request)
        return False
