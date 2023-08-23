from drf_yasg import openapi

from log1.utils import DONT_HAVE_ACCESS
from utils_app.utils import generate_swagger_auto_schema


def list_petition(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'filter',
                'description': "To filter data based on 'my' petition or 'all' petition.",
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'type',
                'description': 'To filter data based on type of visa.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'employer',
                'description': 'To filter data based on employer company.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'status',
                'description': 'To filter data based on status of petition.',
                'type': openapi.TYPE_STRING
            },
            {
                'name': 'query',
                'description': 'To filter data based on some query.',
                'type': openapi.TYPE_STRING
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"results": [{"consultant": {"id": 1093,
                                                                                     "name": "Raghu Vamshi Sunkasari",
                                                                                     "email": "raghuvamshimailbox"
                                                                                              "@gmail.com",
                                                                                     "status": "on_bench",
                                                                                     "is_active": True}, "id": 271,
                                                                      "status": "doc_request_sent",
                                                                      "employer": "NetResolute", "expiry_date": None,
                                                                      "is_withdrawn": False,
                                                                      "petition_type": "h1b_fresh",
                                                                      "beneficiary_type": False,
                                                                      "assigned_to": "Vikalp Singh",
                                                                      "uploaded_documents": 0, "total_documents": 7}],
                                                         "total": 269}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def retrieve_petition(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "result": {"id": 234, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 1109, "name": "Ashwin Mulatkar", "email": "ashwinm02@gmail.com"},
                           "assigned_to": "Kanav Kakar", "beneficiary_type": False, "docs": [], "reasons": [],
                           "status": "doc_request_sent", "lca_no": None, "uscis_no": None, "fedex_no": None,
                           "premium_processing": None, "created_by": 379, "is_active": True, "rfe": False,
                           "expiry_date": None, "is_withdrawn": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def create_petition(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'support_required': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Support required or not'
                ),

                'consultant': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of consultant'
                ),
                'assign_to': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of poc'
                ),
                'petition_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Type of visa'
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of employer company'
                ),
                'beneficiary_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Consultant or inhouse employee'
                ),
                'expiry_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Expiry date of visa'
                ),
            },
            ['consultant', 'assign_to']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "status": "assigned",
                           "total_documents": 32, "uploaded_documents": 0, "expiry_date": "2023-07-31",
                           "is_withdrawn": False}, "message": "Petition Created"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def update_petition(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'assign_to': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of poc'
                ),
                'petition_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Type of visa'
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of employer company'
                ),
                'beneficiary_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Consultant or inhouse employee'
                ),
                'expiry_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Expiry date of visa'
                ),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "status": "assigned",
                           "total_documents": 32, "uploaded_documents": 0, "expiry_date": "2023-07-31",
                           "is_withdrawn": False}, "message": "Petition Updated"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_documents(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'petition',
                'description': "ID of petition",
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
            {
                'name': 'consultant',
                'description': 'ID of consultant',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": {"Beneficiary Documents from the petitioner": [
                {"remark": None, "id": 20, "name": "msa", "status": "not_uploaded",
                 "category": "Beneficiary Documents from the petitioner", "value": "Agreement (MSA)", "docs": []},
                {"remark": None, "id": 21, "name": "offer_letter", "status": "not_uploaded",
                 "category": "Beneficiary Documents from the petitioner", "value": "Offer Letter", "docs": []},
                {"remark": None, "id": 22, "name": "work_order", "status": "not_uploaded",
                 "category": "Beneficiary Documents from the petitioner", "value": "SOW (Work Order)", "docs": []},
                {"remark": None, "id": 23, "name": "employment_agreement", "status": "not_uploaded",
                 "category": "Beneficiary Documents from the petitioner", "value": "Employment Agreement", "docs": []},
                {"remark": None, "id": 24, "name": "consultadd_w2", "status": "not_uploaded",
                 "category": "Beneficiary Documents from the petitioner", "value": "Consultadd W2", "docs": []}],
                "Employer Relationship": [{"remark": None, "id": 15,
                                           "name": "client_letter",
                                           "status": "not_uploaded",
                                           "category": "Employer Relationship",
                                           "value": "Client Letter",
                                           "docs": []},
                                          {"remark": None, "id": 16,
                                           "name": "vendor_letter",
                                           "status": "not_uploaded",
                                           "category": "Employer Relationship",
                                           "value": "Vendor Letter",
                                           "docs": []},
                                          {"remark": None, "id": 17,
                                           "name": "timesheet",
                                           "status": "not_uploaded",
                                           "category": "Employer Relationship",
                                           "value": "Last 2 Month Timesheet",
                                           "docs": []}],
                "Employment": [
                    {"remark": None, "id": 8, "name": "I20",
                     "status": "not_uploaded",
                     "category": "Employment", "value": "Form I20",
                     "docs": []},
                    {"remark": None, "id": 9, "name": "paystub",
                     "status": "not_uploaded",
                     "category": "Employment",
                     "value": "Recent Paystub", "docs": []},
                    {"remark": None, "id": 10, "name": "sevis",
                     "status": "not_uploaded",
                     "category": "Employment",
                     "value": "SEVIS Certificate", "docs": []},
                    {"remark": None, "id": 11, "name": "job_desc",
                     "status": "not_uploaded",
                     "category": "Employment",
                     "value": "Detailed Job Description",
                     "docs": []},
                    {"remark": None, "id": 12, "name": "ead",
                     "status": "not_uploaded",
                     "category": "Employment",
                     "value": "Employment Authorization Card",
                     "docs": []}, {"remark": None, "id": 13,
                                   "name": "experience_letter",
                                   "status": "not_uploaded",
                                   "category": "Employment",
                                   "value": "Experience Letter",
                                   "docs": []},
                    {"remark": None, "id": 14,
                     "name": "performance_review_sheet",
                     "status": "not_uploaded",
                     "category": "Employment",
                     "value": "Performance Review Sheet",
                     "docs": []}], "Immigration History": [
                    {"remark": None, "id": 6, "name": "I94", "status": "not_uploaded",
                     "category": "Immigration History", "value": "I94 Record", "docs": []},
                    {"remark": None, "id": 7, "name": "previous_approval", "status": "not_uploaded",
                     "category": "Immigration History", "value": "Previous Approval Notices", "docs": []}], "Other": [
                    {"remark": None, "id": 18, "name": "insurance_card", "status": "not_uploaded", "category": "Other",
                     "value": "Insurance Cards", "docs": []},
                    {"remark": None, "id": 19, "name": "ssc", "status": "not_uploaded", "category": "Other",
                     "value": "Social Security Card", "docs": []}], "Passport and Visa": [
                    {"remark": None, "id": 4, "name": "visa", "status": "not_uploaded", "category": "Passport and Visa",
                     "value": "Visa", "docs": []},
                    {"remark": None, "id": 5, "name": "passport", "status": "not_uploaded",
                     "category": "Passport and Visa", "value": "Passport", "docs": []}], "Profile and Academic": [
                    {"remark": None, "id": 1, "name": "resume", "status": "not_uploaded",
                     "category": "Profile and Academic", "value": "Resume", "docs": []},
                    {"remark": None, "id": 2, "name": "degree", "status": "not_uploaded",
                     "category": "Profile and Academic", "value": "Degree Certificate", "docs": []},
                    {"remark": None, "id": 3, "name": "transcript", "status": "not_uploaded",
                     "category": "Profile and Academic", "value": "Academic Transcripts", "docs": []}]}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_extension(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'consultant': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of consultant'
                ),
                'assign_to': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of poc'
                ),
                'petition_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Type of visa'
                ),
                'employer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of employer company'
                ),
                'beneficiary_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Consultant or inhouse employee'
                ),
                'expiry_date': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Expiry date of visa'
                ),
            },
            ['consultant', 'assign_to', 'petition_type', 'employer']
        ],
        responses={
            201: {'description': 'Success',
                  'response': {"message": "Extension created", "data": {"petition": 494, "status": 'rfe'}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_types(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'consultant',
                'description': 'ID of consultant',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": [
                {"id": 281, "petition_type": {"name": "h1b_fresh", "display_name": "H1B New"}, "status": "assigned",
                 "created": "2023-08-23T10:19:52.292643Z"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_employer(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"result": ["Consultadd", "NetResolute", "Pythonwise", "Zioqu", "Boto3"]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_types_petition_types(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"result": [["gc", "Green Card"], ["j2_visa", "J2 visa"], ["h1b_fresh", "H1B New"],
                                          ["h1b_transfer", "H1B Transfer"], ["h1b_extension", "H1B Extension"],
                                          ["h1b_amendment", "H1B Amendment"], ["h1b_cap_exempt", "H1B Cap Exempt"],
                                          ["h1b_ext_amend", "H1B Extension with Amendment"]]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {
                      "result": [["rfe", "RFE"], ["denied", "Denied"], ["shipped", "Shipped"], ["approved", "Approved"],
                                 ["assigned", "Assigned"], ["reviewed", "Reviewed"], ["lca_filed", "LCA Filed"],
                                 ["print", "Sent for Print"], ["lca_approved", "LCA Approved"],
                                 ["under_review", "Under Review"], ["rfe_responded", "RFE Docs Sent"],
                                 ["doc_acknowledged", "Docs Acknowledged"],
                                 ["doc_request_sent", "Document Request Sent"],
                                 ["rfe_doc_acknowledged", "RFE Docs Acknowledged"]]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_upload_doc(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'petition',
                'description': 'ID of petition',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        body_params=[
            {
                'file_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='ID of file (like resume or marksheet etc.)'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='File to upload'
                ),
            },
            ['file_type', 'file']
        ],
        responses={
            201: {'description': 'Success', 'response': {"result": [
                {"id": 6698, "petition": 281, "doc_type_name": "transcript", "doc_type": 3, "file_name": "device.csv",
                 "verified": True, "category": "Profile and Academic", "remark": None}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_verify_doc(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'remark': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Remark of verification'
                ),
                'petition': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of petition'
                ),
                'file_type': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of file (like resume or marksheet etc.)'
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Status of verification'
                ),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {"result": [
                {"id": 6699, "petition": 281, "doc_type_name": "transcript", "doc_type": 3,
                 "file_name": "device_OoF53E8.csv", "verified": True, "category": "Profile and Academic",
                 "remark": "good"},
                {"id": 6698, "petition": 281, "doc_type_name": "transcript", "doc_type": 3, "file_name": "device.csv",
                 "verified": True, "category": "Profile and Academic", "remark": "good"}], "message": 'mail sent'}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_doc_request(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success',
                  'response': {"result": {"id": 281, "status": "doc_request_sent", "message": "mail sent"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_doc_url(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'document_id',
                'description': 'ID of document',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": "url"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_upload(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of file'
                ),
                'object_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of object'
                ),
            },
            ['file_name', 'object_id']
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": {"url": "url",
                                                                    "fields": {
                                                                        "key": "key",
                                                                        "x-amz-algorithm": "AWS4-HMAC-SHA256",
                                                                        "x-amz-credential": "credential",
                                                                        "x-amz-date": "date",
                                                                        "policy": "policy",
                                                                        "x-amz-signature": "signature"}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_lca(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'lca_no': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='No of LCA'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='File for LCA'
                ),
            },
            ['lca_no', 'file']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "docs": [], "reasons": [],
                           "status": "lca_filed", "lca_no": "2345", "uscis_no": None, "fedex_no": None,
                           "premium_processing": None, "created_by": 618, "is_active": True, "rfe": False,
                           "expiry_date": "2023-07-31", "is_withdrawn": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_file(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'doc_type_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of document'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='File for Petition'
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Status of petition'
                ),
            },
            []
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "docs": [], "reasons": [],
                           "status": "lca_filed", "lca_no": "2345", "uscis_no": None, "fedex_no": None,
                           "premium_processing": None, "created_by": 618, "is_active": True, "rfe": False,
                           "expiry_date": "2023-07-31", "is_withdrawn": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_shipping_status(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'rfe_doc': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='RFE document'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='File for Petition'
                ),
                'request_status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Status of petition'
                ),
                'fedex_no': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Fedex number of petition'
                ),
                'reason': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Reason for status'
                ),
                'receipt_no': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Receipt No'
                ),
                'denied_doc': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Document for deny'
                ),
                'approved_doc': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='Document for approval'
                ),
            },
            ['request_status']
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "docs": [], "reasons": [],
                           "status": "print", "lca_no": "2345", "uscis_no": None, "fedex_no": None,
                           "premium_processing": None, "created_by": 618, "is_active": True, "rfe": False,
                           "expiry_date": "2023-07-31", "is_withdrawn": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_document(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'doc_id',
                'description': 'ID of document',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            202: {'description': 'Success', 'response': {
                "result": {"id": 281, "petition_type": "h1b_fresh", "employer": "Consultadd",
                           "consultant": {"id": 793, "name": "Rohan Shah", "email": "rohanchetanshah9@gmail.com"},
                           "assigned_to": "Aashna Shrivastava", "beneficiary_type": False, "docs": [], "reasons": [],
                           "status": "print", "lca_no": "2345", "uscis_no": None, "fedex_no": None,
                           "premium_processing": None, "created_by": 618, "is_active": True, "rfe": False,
                           "expiry_date": "2023-07-31", "is_withdrawn": False}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_get_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"results": [
                {"id": 25, "comment_text": "Demo comment text", "parent_comment": None, "object_id": 256,
                 "user_type": "user", "user": {"employee_name": "Consultadd Admin", "id": 1}, "child_comment": [],
                 "created": "2023-08-23T11:26:50.121744Z"}]}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        },
        methods=['get']
    )(view_func)

    return decorated_view


def petition_post_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'comment_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Comment Text'
                ),
                'parent_comment': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of parent comment'
                ),
            },
            ['comment_text', 'parent_comment']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "result": {"id": 27, "comment_text": "Demo comment text", "parent_comment": 13, "object_id": 256,
                           "user_type": "user", "user": {"employee_name": "Consultadd Admin", "id": 1},
                           "child_comment": [], "created": "2023-08-23T11:30:52.871935Z"}}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        },
        methods=['post']
    )(view_func)

    return decorated_view


def petition_withdraw(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            202: {'description': 'Success', 'response': {"message": "Petition Withdrawn Successfully"}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def list_petition_docs(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"results": [
                {"id": 6440, "petition": 251, "doc_type_name": "transcript", "doc_type": 3,
                 "file_name": "Yash_Navdiwala_Transcript.pdf", "verified": None, "category": "Profile and Academic",
                 "remark": None}]}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def create_petition_docs(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'petition': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of petition'
                ),

                'file_type': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of file (like resume or marksheet etc.)'
                ),
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='File to upload'
                ),
            },
            ['petition', 'file_type', 'file']
        ],
        responses={
            201: {'description': 'Success', 'response': {"result": [
                {"id": 6707, "petition": 281, "doc_type_name": "transcript", "doc_type": 3,
                 "file_name": "device_XdOUblU.csv", "verified": None, "category": "Profile and Academic",
                 "remark": None}, {"id": 6699, "petition": 281, "doc_type_name": "transcript", "doc_type": 3,
                                   "file_name": "device_OoF53E8.csv", "verified": True,
                                   "category": "Profile and Academic", "remark": "good"},
                {"id": 6698, "petition": 281, "doc_type_name": "transcript", "doc_type": 3, "file_name": "device.csv",
                 "verified": True, "category": "Profile and Academic", "remark": "good"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def delete_petition_docs(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            204: {'description': 'Success', 'response': {"result": "File deleted"}, },
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_docs_contact_us(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'petition_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of petition'
                ),
            },
            ['petition']
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": {"message": "mail sent"}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_docs_get_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"results": [
                {"id": 29, "comment_text": "text", "parent_comment": None, "object_id": 251, "user_type": "consultant",
                 "user": {"employee_name": "Yash Navdiwala", "id": 731}, "child_comment": [],
                 "created": "2023-08-23T11:52:28.083990Z"}]}},
            400: {'description': 'Bad Request'},
            403: {'description': 'Unauthorized', 'response': DONT_HAVE_ACCESS}
        },
        methods=['get']
    )(view_func)

    return decorated_view


def petition_docs_post_comment(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'comment_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Comment Text'
                ),
                'parent_comment': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of parent comment'
                ),
            },
            ['comment_text', 'parent_comment']
        ],
        responses={
            201: {'description': 'Success', 'response': {
                "result": {"id": 30, "comment_text": "text", "parent_comment": 12, "object_id": 251,
                           "user_type": "consultant", "user": {"employee_name": "Yash Navdiwala", "id": 731},
                           "child_comment": [], "created": "2023-08-23T11:54:22.488162Z"}}},
            400: {'description': 'Bad Request'}
        },
        methods=['post']
    )(view_func)

    return decorated_view


def petition_docs_doc_types(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {
                "results": {
                    "Beneficiary Documents from the petitioner": [],
                    "Employer Relationship": [
                        {
                            "remark": None,
                            "id": 15,
                            "name": "client_letter",
                            "status": "in_review",
                            "category": "Employer Relationship",
                            "value": "Client Letter"
                        },
                        {
                            "remark": None,
                            "id": 16,
                            "name": "vendor_letter",
                            "status": "in_review",
                            "category": "Employer Relationship",
                            "value": "Vendor Letter"
                        },
                        {
                            "remark": None,
                            "id": 17,
                            "name": "timesheet",
                            "status": "not_uploaded",
                            "category": "Employer Relationship",
                            "value": "Last 2 Month Timesheet"
                        }
                    ],
                    "Employment": [
                        {
                            "remark": None,
                            "id": 8,
                            "name": "I20",
                            "status": "in_review",
                            "category": "Employment",
                            "value": "Form I20"
                        },
                        {
                            "remark": None,
                            "id": 9,
                            "name": "paystub",
                            "status": "not_uploaded",
                            "category": "Employment",
                            "value": "Recent Paystub"
                        },
                        {
                            "remark": None,
                            "id": 10,
                            "name": "sevis",
                            "status": "not_uploaded",
                            "category": "Employment",
                            "value": "SEVIS Certificate"
                        },
                        {
                            "remark": None,
                            "id": 11,
                            "name": "job_desc",
                            "status": "not_uploaded",
                            "category": "Employment",
                            "value": "Detailed Job Description"
                        },
                        {
                            "remark": None,
                            "id": 12,
                            "name": "ead",
                            "status": "in_review",
                            "category": "Employment",
                            "value": "Employment Authorization Card"
                        },
                        {
                            "remark": None,
                            "id": 13,
                            "name": "experience_letter",
                            "status": "in_review",
                            "category": "Employment",
                            "value": "Experience Letter"
                        },
                        {
                            "remark": None,
                            "id": 14,
                            "name": "performance_review_sheet",
                            "status": "not_uploaded",
                            "category": "Employment",
                            "value": "Performance Review Sheet"
                        }
                    ],
                    "Immigration History": [
                        {
                            "remark": None,
                            "id": 6,
                            "name": "I94",
                            "status": "in_review",
                            "category": "Immigration History",
                            "value": "I94 Record"
                        },
                        {
                            "remark": None,
                            "id": 7,
                            "name": "previous_approval",
                            "status": "not_uploaded",
                            "category": "Immigration History",
                            "value": "Previous Approval Notices"
                        }
                    ],
                    "Other": [
                        {
                            "remark": None,
                            "id": 18,
                            "name": "insurance_card",
                            "status": "not_uploaded",
                            "category": "Other",
                            "value": "Insurance Cards"
                        },
                        {
                            "remark": None,
                            "id": 19,
                            "name": "ssc",
                            "status": "in_review",
                            "category": "Other",
                            "value": "Social Security Card"
                        }
                    ],
                    "Passport and Visa": [
                        {
                            "remark": None,
                            "id": 5,
                            "name": "passport",
                            "status": "in_review",
                            "category": "Passport and Visa",
                            "value": "Passport"
                        },
                        {
                            "remark": None,
                            "id": 4,
                            "name": "visa",
                            "status": "in_review",
                            "category": "Passport and Visa",
                            "value": "Visa"
                        }
                    ],
                    "Petition Document": [
                        {
                            "remark": None,
                            "id": 25,
                            "name": "lca_document",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "LCA Document"
                        },
                        {
                            "remark": None,
                            "id": 26,
                            "name": "final_petition",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "Final Petition"
                        },
                        {
                            "remark": None,
                            "id": 27,
                            "name": "receipt_acknowledgement",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "Receipt Acknowledgement"
                        },
                        {
                            "remark": None,
                            "id": 28,
                            "name": "rfe",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "RFE Notice"
                        },
                        {
                            "remark": None,
                            "id": 29,
                            "name": "rfe_response",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "RFE Response"
                        },
                        {
                            "remark": None,
                            "id": 30,
                            "name": "denial_notice",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "Denial Notice"
                        },
                        {
                            "remark": None,
                            "id": 31,
                            "name": "approval_notice",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "Approval Notice"
                        },
                        {
                            "remark": None,
                            "id": 32,
                            "name": "other",
                            "status": "not_uploaded",
                            "category": "Petition Document",
                            "value": "Other"
                        }
                    ],
                    "Profile and Academic": [
                        {
                            "remark": None,
                            "id": 1,
                            "name": "resume",
                            "status": "in_review",
                            "category": "Profile and Academic",
                            "value": "Resume"
                        },
                        {
                            "remark": None,
                            "id": 2,
                            "name": "degree",
                            "status": "in_review",
                            "category": "Profile and Academic",
                            "value": "Degree Certificate"
                        },
                        {
                            "remark": None,
                            "id": 3,
                            "name": "transcript",
                            "status": "in_review",
                            "category": "Profile and Academic",
                            "value": "Academic Transcripts"
                        }
                    ]
                }
            }},
            400: {'description': 'Bad Request'}
        },
    )(view_func)

    return decorated_view


def petition_docs_doc_url(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'document_id',
                'description': 'ID of document',
                'type': openapi.TYPE_INTEGER,
                'required': True
            },
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": "url"}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def petition_docs_upload(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'file_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Name of file'
                ),
                'object_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of object'
                ),
            },
            ['file_name', 'object_id']
        ],
        responses={
            200: {'description': 'Success', 'response': {"result": {"url": "url",
                                                                    "fields": {
                                                                        "key": "key",
                                                                        "x-amz-algorithm": "AWS4-HMAC-SHA256",
                                                                        "x-amz-credential": "credential",
                                                                        "x-amz-date": "date",
                                                                        "policy": "policy",
                                                                        "x-amz-signature": "signature"}}}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view
