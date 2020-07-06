import os
import logging
import requests
from datetime import date, datetime, timezone
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City
from api_key.models import APIKey
from consultant.models import ConsultantRateRevision, Consultant

logger = logging.getLogger(__name__)


class CityViewSets(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query')
        city = City.objects.filter(name__istartswith=query)
        data = city[:40].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)


def get_contact_data(object_id):
    key = os.getenv('HUBSPOT_KEY')
    url = f"https://api.hubapi.com/contacts/v1/contact/vid/{object_id}/profile?hapikey={key}"
    headers = {}
    data = requests.get(url=url, headers=headers)
    return data.json()


def get_rate_by_email(email):
    key = os.getenv('HUBSPOT_KEY')
    url = f"https://api.hubapi.com/contacts/v1/contact/email/{email}/profile?hapikey={key}&property=candidate_rate"
    headers = {}
    data = requests.get(url=url, headers=headers)
    if "errors" in data.json():
        return data.json()['message'], 'error'
    return data.json()['properties']['candidate_rate']['versions'], 'data'


class WebHookViewSet(GenericViewSet):
    queryset = City.objects.all()

    @action(methods=["post"], detail=False, url_path='hubspot')
    def hubspot(self, request):
        api_key = request.query_params.get('api_key', None)
        if not APIKey.objects.is_valid(api_key):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        if request.data['propertyName'] == 'candidate_rate':
            contact_obj = get_contact_data(request.data['objectId'])
            email = contact_obj['properties']['email']['value']
            data = contact_obj['properties']['candidate_rate']['versions']
            consultant = Consultant.objects.filter(email=email).first()
            if consultant:
                rates = consultant.rates.all()
                if len(rates) != len(data) - 1:
                    rates.delete()
                    for i, rate in reversed(list(enumerate(data))):
                        prev_rate = 0
                        if i != len(data) - 1:
                            prev_rate = data[i + 1]['value']

                        ConsultantRateRevision.objects.create(
                            rate=rate["value"],
                            previous_rate=prev_rate,
                            consultant=consultant,
                            start=datetime.fromtimestamp((rate['timestamp'] / 1000)).strftime('%Y-%m-%d'),
                            end=datetime.fromtimestamp((data[i - 1]['timestamp'] / 1000)).strftime(
                                '%Y-%m-%d') if i != 0 else None
                        )
                else:
                    prev_rate = consultant.rates.filter(end=None).first()
                    rate = 0
                    if prev_rate:
                        rate = prev_rate.rate
                        prev_rate.end = date.today()
                        prev_rate.save()
                    ConsultantRateRevision.objects.create(
                        rate=request.data['propertyValue'],
                        previous_rate=rate,
                        start=date.today(),
                        consultant=consultant,
                    )
                return Response({"result": "ok"}, status=status.HTTP_200_OK)
            return Response({"error": "Candidate not match"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["put"], detail=True, url_path='sync')
    def hubspot_sync(self, request, *args, **kwargs):
        try:
            consultant = get_object_or_404(Consultant, id=kwargs.get('pk'))
            data, msg = get_rate_by_email(consultant.email)
            if msg == 'error':
                return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)
            rates = consultant.rates.all()
            if len(rates) == len(data):
                return Response({"result": "Already in Sync with Hubspot"}, status=status.HTTP_200_OK)
            rates.delete()
            for i, rate in reversed(list(enumerate(data))):
                prev_rate = 0
                if i != len(data)-1:
                    prev_rate = data[i+1]['value']
                ConsultantRateRevision.objects.create(
                    rate=rate["value"],
                    previous_rate=prev_rate,
                    consultant=consultant,
                    start=datetime.fromtimestamp((rate['timestamp']/1000)).strftime('%Y-%m-%d'),
                    end=datetime.fromtimestamp((data[i-1]['timestamp']/1000)).strftime('%Y-%m-%d') if i != 0 else None
                )
            result = consultant.rates.all().order_by('-id').values('id', 'rate', 'start', 'end', 'previous_rate',
                                                                   'feedback', 'consultant')
            return Response({"result": result}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
