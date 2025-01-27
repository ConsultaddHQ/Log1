from django.core.management import BaseCommand
from django.db.models import Q
from marketing.models import Submission
from constance import config
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from project.models import Project

ATTIO_URL = config.ATTIO_URL
API_KEY = config.ATTIO_API_KEY
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

class Command(BaseCommand):
    help = "This command is for fetching Submission and pushing data into Attio, including notes for interviews."

    def handle(self, *args, **options):
        try:
            submissions = Submission.objects.filter(
                created__gte='2025-01-01',
                rate__gt=0,
                employer='Consultadd',
            ).exclude(
                Q(client__isnull=True) | Q(client='')
            ).filter(
                vendor_contact_id__isnull=False
            ).order_by('created')

            for submission in submissions:
                deal_data = {
                    "vendor_company": submission.vendor.name,
                    "deal_rate": (submission.rate - submission.consultant.rate),
                    "client_name": submission.client,
                    "consultant_name": submission.consultant.name,
                    "unique_key": f"{submission.vendor.name} {submission.vendor_contact.region or ''} - {submission.client} - {submission.consultant.name}",
                    "deal_id": submission.id,
                }

                # Fetch associated company, person, and creator using _fetch_record
                associated_company = _fetch_record("companies", {"name": submission.vendor.name})
                associated_person = _fetch_record("people", {"name": submission.vendor_contact.name})
                associated_creator = _fetch_record("people", {"email": submission.created_by.email})

                if associated_company:
                    deal_data["associated_company"] = [associated_company.get("record_id", [{}])[0].get("value")]
                if associated_person:
                    deal_data["associated_people"] = [associated_person.get("record_id", [{}])[0].get("value")]
                if associated_creator:
                    deal_data["lead_owner"] = [associated_creator.get("record_id", [{}])[0].get("value")]

                if _update_or_create_deal(deal_data, "deal_2025"):
                    if submission.status in ['interview', 'in-offer', 'project']:
                        deal_data["deal_stage"] = "In Process"

                        # Add notes for interviews
                        interview_obj = submission.screening.include(status__in=["next_round", "failed", "offer"])
                        for interview in interview_obj:
                            title = f"Interview Details - R{interview.round}"
                            note_content = (
                                f"Interview Date: {interview.start_time.strftime('%Y-%m-%d')}\n"
                                f"Interview Feedback: {interview.feedback}"
                            )
                            _update_or_create_note(
                                object_slug="deals_2025",
                                deal_id=submission.id,
                                note_title=title,
                                note=note_content
                            )
                        if submission.status == 'project':       
                            project = Project.objects.filter(submission=submission)
                            if project.status == 'joined':
                                end_date = datetime.strptime(project.end_date, '%Y-%m-%d')
                                start_date = datetime.strptime(project.start_date, '%Y-%m-%d')
                                total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                                rate = (project.rate - project.consultant.rate) * 40 * 4 * total_months
                                deal_data['deal_rate'] = rate
                                deal_data["deal_stage"] = "Won"
                                note = f"{submission.consultant.name} - {submission.lead.job_title} - {submission.client} - ${submission.rate - submission.consultant.rate} - {total_months} months - Received offer, starting {project.start_date}"
                                _update_or_create_note("deals_2025", submission.id, "Project Details", note)

                        _update_or_create_deal(deal_data, "deal_2025")

        except Exception as error:
            print(f"An error occurred: {error}")


def _fetch_record(object_slug: str, filter_payload: Dict) -> Optional[Dict]:
    """Fetch a record from Attio based on the given filter."""
    try:
        url = f"{ATTIO_URL}/objects/{object_slug}/records/query"
        response = requests.post(url, headers=HEADERS, json={"filter": filter_payload})
        if response.status_code != 200:
            print("Error fetching record from Attio.")
            return None

        data = response.json().get("data", [])
        return data[0].get("values") if data else None
    except Exception as error:
        print(error)
        return None


def _update_or_create_note(object_slug: str, deal_id: str, note_title: str, note: str) -> bool:
    """Update or create a note in Attio."""
    try:
        record = _fetch_record(object_slug, {"deal_id": deal_id})
        if not record:
            return False

        deal_record_id = record.get("record_id", [{}])[0].get("value")
        note_url = f"{ATTIO_URL}/notes"
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
            print("Error adding a note to record in Attio.")
            return False

        return True
    except Exception as error:
        print(f"Error in _update_or_create_note: {error}")
        return False

def _update_or_create_deal(deal_data: Dict, object_slug: str) -> Optional[bool]:
    try:
        record = _fetch_record(object_slug, {"deal_id": deal_data["deal_id"]})
        if record:
            deal_record_id = record.get("record_id", [{}])[0].get("value")
            update_url = f"{ATTIO_URL}/objects/{object_slug}/records/{deal_record_id}"
            payload = {"data": {"values": deal_data}}
            response = requests.patch(update_url, headers=HEADERS, json=payload)
            if response.status_code != 200:
                print(f"Error updating deal record in Attio.")
            return True

        # Create a new record if not found
        create_url = f"{ATTIO_URL}/objects/{object_slug}/records"
        payload = {"data": {"values": deal_data}}
        response = requests.post(create_url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            print("Error creating deal record in Attio.")
            return False

        return True
    except Exception as error:
        print(str(error))
        return False
