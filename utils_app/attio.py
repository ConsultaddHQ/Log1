import requests
from typing import Any, Dict, Optional
from celery import shared_task
from datetime import datetime
from constance import config
from log1.utils import write_exception
from django.utils import timezone

ATTIO_URL = config.ATTIO_URL
API_KEY = config.ATTIO_API_KEY
ATTIO_DEAL_NAME = config.ATTIO_DEAL_NAME
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


@shared_task
def attio_trigger(obj: Any, object_slug: str, status_change: Optional[bool], request: Any = None) -> bool:
    """
    Trigger the process to synchronize vendor and interview data with Attio.
    param obj: Object containing the submission and other related details.
    param object_slug: The Attio object slug to interact with.
    return: Boolean indicating success or failure.
    """
    try:
        submission_obj = obj.submission
        vendor_data = _extract_vendor_data(submission_obj)

        # deal stage change
        if submission_obj.status in ['interview', "in_offer"]:
            stage = "Failed" if obj.get_status_display() in ["Failed", "Cancelled"] else "In Process"
            update_deal_stage_trigger(ATTIO_DEAL_NAME, submission_obj, stage, request)
        
        # add note for interview status update with feedback
        if obj.get_status_display() in ["Next Round", "offer", "Failed", "Cancelled"] and status_change:
            note = f"Interview Date - {obj.start_time.strftime('%Y-%m-%d')},\nFeedback: {obj.feedback}"
            title = f"Interview Details - R{obj.round}"
            _update_or_create_note(ATTIO_DEAL_NAME, submission_obj.id, title, note, request)

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


@shared_task
def attio_create_deal_trigger(obj: Any, object_slug: str, stage: Optional[str] = "Lead", request: Any = None) -> bool:
    try:
        company_obj = _fetch_record("companies", {"name": obj.vendor.name}, request)
        associated_company_id = (
            company_obj.get("record_id")[0].get("value")
            if company_obj and "record_id" in company_obj and company_obj["record_id"]
            else None
        )
        person_obj = _fetch_record("people", {"name": obj.vendor_contact.name}, request)
        associated_person_id = (
            person_obj.get("record_id")[0].get("value")
            if person_obj and "record_id" in person_obj and person_obj["record_id"]
            else None
        )
        creator_obj = _fetch_record("people", {"email_addresses": obj.created_by.email}, request)
        associated_creator_id = (
            creator_obj.get("record_id")[0].get("value")
            if creator_obj and "record_id" in creator_obj and creator_obj["record_id"]
            else None
        )
        if obj.rate:
            deal_data = _extract_deal_data(obj, int(obj.rate), stage, associated_company_id, associated_person_id, associated_creator_id)
            _update_or_create_deal(deal_data, object_slug, request)
        
        return True
    except Exception as error:
        write_exception(f"Error in attio_create_deal_trigger: {str(error)}", request)
        return False


@shared_task
def attio_deal_won_trigger(object_slug: str, obj: Any, request: Any = None) -> bool:
    try:
        submission = obj.submission
        rate = get_rate(obj)
        deal_data = _extract_deal_data(submission, rate, "Won", company_id=None, person_id=None, creator_id=None)
        _update_or_create_deal(deal_data, object_slug, request)

        note = f"{submission.consultant.name} - {submission.lead.job_title} - {submission.client} - ${int(submission.rate)} - {obj.duration} months - Received offer, starting {obj.start_date}"
        _update_or_create_note(object_slug, submission.id, "Project Details", note, request)
        return True
    except Exception as error:
        write_exception(str(error), request)
        return False
    
def get_rate(obj: Any) -> int:
    submission = obj.submission
    if int(obj.duration) % 3 == 0:
        rate = (int(submission.rate) - int(submission.consultant.rate)) *  520 * (int(int(obj.duration) / 3)) 
    else:
        rate = (int(submission.rate) - int(submission.consultant.rate)) * 40 * 4 * int(obj.duration)
    return rate

def update_deal_stage_trigger(object_slug: str, obj: Any, stage: str, request: Any = None) -> None:
    try:
        record = _fetch_record(object_slug, {"deal_id": obj.id}, request)
        if not record:
            if obj.work_type == "c2c" and obj.employer == 'Consultadd' and obj.vendor_contact and obj.client and obj.consultant.status != 'on_project':
                attio_create_deal_trigger(obj, object_slug, stage, request)
            return

        deal_record_id = record.get("record_id", [{}])[0].get("value")
        update_url = f"{ATTIO_URL}/objects/{object_slug}/records/{deal_record_id}"
        payload = {"data": {"values": {"deal_stage": stage}}}
        response = requests.patch(update_url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            write_exception("Error updating deal stage in Attio.", request)
    except Exception as error:
        write_exception(str(error), request)


def _extract_deal_data(submission_obj: Any, rate: int, stage: str, company_id: Optional[str], person_id: Optional[str], creator_id: Optional[str]) -> Dict:
    deal_data = {
        "vendor_company": f"{submission_obj.vendor.name}",
        "deal_rate": rate,
        "deal_stage": stage,
        "client_name": submission_obj.client,
        "consultant_name": submission_obj.consultant.name,
        "unique_key": f"{submission_obj.vendor.name} {submission_obj.vendor_contact.region or ''} - {submission_obj.client} - {submission_obj.consultant.name}",
        "deal_id": submission_obj.id,
        "vendor_region": submission_obj.vendor_contact.region or ''
    }

    if company_id:
        deal_data["associated_company"] = [company_id]
    if person_id:
        deal_data["associated_people"] = [person_id]
    if creator_id:
        deal_data["lead_source"] = [creator_id]

    return deal_data


def _update_or_create_deal(deal_data: Dict, object_slug: str, request: Any = None) -> Optional[bool]:
    try:
        record = _fetch_record(object_slug, {"deal_id": deal_data["deal_id"]}, request)
        if record:
            deal_record_id = record.get("record_id", [{}])[0].get("value")
            update_url = f"{ATTIO_URL}/objects/{object_slug}/records/{deal_record_id}"
            payload = {"data": {"values": deal_data}}
            response = requests.patch(update_url, headers=HEADERS, json=payload)
            if response.status_code != 200:
                write_exception("Error updating deal record in Attio.", request)
            return True

        # Create a new record if not found
        create_url = f"{ATTIO_URL}/objects/{object_slug}/records"
        payload = {"data": {"values": deal_data}}
        response = requests.post(create_url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            write_exception("Error creating deal record in Attio.", request)
            return False

        return True
    except Exception as error:
        write_exception(str(error), request)
        return False

def _update_or_create_note(object_slug: str, deal_id: str, note_title: str, note: str, request: Any = None) -> bool:
    try:
        record = _fetch_record(object_slug, {"deal_id": deal_id}, request)
        if not record:
            return False

        deal_record_id = record.get("record_id", [{}])[0].get("value")
        note_url = f"{ATTIO_URL}/notes"
        query_params = {
            "parent_object": object_slug,
            "parent_record_id": deal_record_id
        }
        response = requests.get(note_url, headers=HEADERS, params=query_params)
        if response.status_code != 200:
            write_exception("Error fetching notes from Attio.", request)
            return None

        data = response.json().get("data", [])
        note_exist = next((note for note in data if note.get("title") == note_title), None)
        if note_exist:
            note_id = note_exist['id']['note_id']
            response = requests.delete(f"{note_url}/{note_id}", headers=HEADERS)
            if response.status_code != 200:
                write_exception("Error fetching notes from Attio.", request)
                return None

        payload = {
            "data": {
                "parent_object": object_slug,
                "parent_record_id": deal_record_id,
                "title": note_title,
                "format": "plaintext",
                "content": note
            }
        }
        response = requests.post(note_url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            write_exception("Error adding a note to record in Attio.", request)
            return False

        return True
    except Exception as error:
        write_exception(str(error), request)
        return False


def _fetch_record(object_slug: str, filter_payload: Dict, request: Any = None) -> Optional[Dict]:
    """Fetch a record from Attio based on the given filter."""
    try:
        url = f"{ATTIO_URL}/objects/{object_slug}/records/query"
        response = requests.post(url, headers=HEADERS, json={"filter": filter_payload})
        if response.status_code != 200:
            write_exception("Error fetching record from Attio.", request)
            return None

        data = response.json().get("data", [])
        return data[0].get("values") if data else None
    except Exception as error:
        write_exception(str(error), request)
        return None

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
