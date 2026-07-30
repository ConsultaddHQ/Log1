from typing import Any, Optional

from constance import config
from django.core.management import BaseCommand

from consultant.models import Consultant
from marketing.models import Submission
from utils_app.attio import _fetch_record, _extract_deal_data, _update_or_create_deal
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


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
            deal_data = _extract_deal_data(obj, int(obj.rate), stage, associated_company_id, associated_person_id,
                                           associated_creator_id)
            breakpoint()
            _update_or_create_deal(deal_data, object_slug, request)

        return True
    except Exception as error:
        return False


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            sub_obj = Submission.objects.get(id=116343)

            check = attio_create_deal_trigger(sub_obj, config.ATTIO_DEAL_NAME, request=None)
        except Exception as error:
            print(error)
