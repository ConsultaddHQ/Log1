from drf_yasg import openapi

from utils_app.utils import generate_swagger_auto_schema


def retrieve_twilio(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 21, "text": "Hey Mehul \nIt's ruchi \nHow are you ? ", "created": "2020-05-26T20:34:15.599970Z",
                 "is_sent": False, "conversation_id": 13, "read": True},
                {"id": 61, "text": "(248)-509-0470 \nGoogle voice number ", "created": "2020-06-02T18:46:22.844082Z",
                 "is_sent": False, "conversation_id": 13, "read": True}, {"id": 62,
                                                                          "text": "How does it gonna work ? I mean I have confusion if vendor call on this number didn't I get call on my phone ? ",
                                                                          "created": "2020-06-02T18:47:19.654316Z",
                                                                          "is_sent": False, "conversation_id": 13,
                                                                          "read": True},
                {"id": 63, "text": "306, highlands dr, \nCanton , MI \n48188 ",
                 "created": "2020-06-02T18:48:04.936094Z", "is_sent": False, "conversation_id": 13, "read": True}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def list_twilio(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'user1',
                'description': "ID of asset.",
                'type': openapi.TYPE_INTEGER,
                'required': True
            }
        ],
        responses={
            200: {'description': 'Success', 'response': {"data": [
                {"id": 165, "user2": "+12014676192", "created": "2020-07-22T13:11:47.084307Z",
                 "modified": "2020-07-22T18:34:03.927723Z", "text": "Hi Bharat - are you able to login now?",
                 "read": True}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def twilio_number_list(view_func):
    decorated_view = generate_swagger_auto_schema(
        responses={
            200: {'description': 'Success', 'response': {"data": [{"id": 1156, "number": "+15512268917"}]}},
            400: {'description': 'Bad Request'},
        }
    )(view_func)

    return decorated_view


def twilio_send(view_func):
    decorated_view = generate_swagger_auto_schema(
        body_params=[
            {
                'to': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of asset you want to send message."
                ),
                'user1': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of asset from which you want to send message."
                ),
                'message': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Message to send."
                ),

            },
            ['to', 'user1', 'message']
        ],
        responses={
            200: {'description': 'Success',
                  'response': {"data": {"id": 3329, "text": "hi there", "read": True, "is_sent": True,
                                        "created": "2023-09-12T09:54:26.587040Z", "conversation": 1224}}},
            400: {'description': 'Bad Request'}
        }
    )(view_func)

    return decorated_view


def twilio_receive_sms(view_func):
    decorated_view = generate_swagger_auto_schema(
        query_params=[
            {
                'name': 'api_key',
                'description': "API key.",
                'type': openapi.TYPE_STRING,
                'required': True
            }
        ],
        body_params=[
            {
                'To': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of asset you want to send message."
                ),
                'From': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of asset from which you want to send message."
                ),
                'Body': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Message to send."
                ),

            },
            ['To', 'From', 'Body']
        ],
        responses={
            201: {'description': 'Success'},
            400: {'description': 'Bad Request'},
            401: {'description': 'Invalid User'}
        },
        methods=['get', 'post']
    )(view_func)

    return decorated_view
