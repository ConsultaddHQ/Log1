import json
import requests
import logging

from django.db.models import Q
from rest_framework import serializers
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from ckiller.models import *

logger = logging.getLogger(__name__)


class CkillerVendorClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = CkillerVendorClient
        fields = ('name', 'address')


class CkillerSubmissionSerializer(serializers.ModelSerializer):
    vendor = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()

    @staticmethod
    def get_consultant(self):
        return "{} {}".format(self.consultant.name, self.consultant.email)

    @staticmethod
    def get_client(self):
        return CkillerVendorClientSerializer(self.vendors.filter(type='client'), many=True).data

    @staticmethod
    def get_vendor(self):
        return CkillerVendorClientSerializer(self.vendors.filter(type='vendor'), many=True).data

    class Meta:
        model = CkillerSubmission
        fields = ('id', 'submission_id', 'employer', 'project', 'sub_created', 'job_title', 'job_location', 'interview',
                  'marketer', 'consultant', 'created', 'vendor', 'client', 'rate', 'marketing_email', 'marketing_phone')


class CkillerSubmissionView(viewsets.ModelViewSet):
    queryset = CkillerSubmission.objects.all()
    serializer_class = CkillerSubmissionSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('query', None)
            consultant = request.query_params.get('consultant', None)
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size
            if 'superadmin' in request.user.roles:
                consultants = Consultant.objects.filter(marketing__status='open').values_list('id', flat=True)
            else:
                consultants = Consultant.objects.filter(
                    Q(marketing__status='open') &
                    (Q(marketing__in_pool=True) |
                     Q(marketing__marketer=request.user))
                ).values_list('id', flat=True)
            queryset = CkillerSubmission.objects.filter(consultant__in=list(consultants)).order_by('sub_created')
            if consultant:
                queryset = queryset.filter(consultant__id=consultant).order_by('sub_created')
            if query:
                queryset = queryset.filter(vendors__name__icontains=query).order_by('sub_created')

            total = queryset.count()
            serializer = self.serializer_class(queryset[first:last], many=True)
            return Response({"results": serializer.data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            email = request.data.get('email', None)
            tenants = {
                'cainc': 'Consultadd',
                'nzyme': 'Nzyme',
                'boto': 'Boto3',
                'okyte': 'Okyte',
                'ioneq': 'Ioneq',
                'zioqu': 'Zioqu',
                'octane': 'Octane',
                'induci': 'Induci',
                'gokronos': 'GoKronos',
                'pythonwise': 'Pythonwise',
                'netresolute': 'Netresolute',
            }
            if email:
                consultant = Consultant.objects.filter(email=email.lower())
                if not consultant:
                    return Response({"error": "Consultant not in your bench"}, status=status.HTTP_404_NOT_FOUND)

                result = []
                for tenant, employer in tenants.items():
                    login_url = 'http://{}.log1.com/api/rest/rest-auth/login/'.format(tenant)

                    header = {
                        'Content-Type': "application/json",
                    }
                    payload = {
                        "username": "bharat.b@consultadd.com",
                        "password": "bharat.bhate"
                    }
                    res = requests.request("POST", login_url, data=json.dumps(payload), headers=header)
                    if res.status_code == 200:
                        res = json.loads(res.text)
                        token = res["key"]
                    else:
                        logger.error("Unable to Login")
                        continue
                    header = {
                        'Content-Type': "application/json",
                        'cache-control': "no-cache",
                        'Authorization': "Token " + token
                    }
                    url = 'http://{}.log1.com/api/rest/new_log1/?email={}'.format(tenant, email)
                    response = requests.request("GET", url, data=json.dumps(payload), headers=header)
                    if response.status_code == 200:
                        data = json.loads(response.text)
                        for row in data["results"]:
                            if len(row["vendor"]) > 0:
                                ck_sub = CkillerSubmission.objects.filter(submission_id=row["id"], employer=employer,
                                                                          sub_created=row["created"])
                                if ck_sub:
                                    continue
                                else:
                                    ck_sub = CkillerSubmission.objects.create(submission_id=row["id"],
                                                                              employer=employer,
                                                                              sub_created=row["created"])
                                ck_sub.consultant = consultant.first()
                                ck_sub.project = row["project"]
                                ck_sub.rate = row["submission_rate"]
                                ck_sub.marketing_email = row["submission_email"]
                                ck_sub.marketing_phone = row["submission_phone"]
                                ck_sub.job_location = row["job_location"]
                                ck_sub.job_title = row["title"]
                                ck_sub.marketer = row["marketer"]
                                ck_sub.interview = [i['title'] for i in row["interviews"]]

                                ck_sub.save()

                                no_of_vendors = len(row["vendor"])
                                if no_of_vendors <= 2:
                                    for v in row["vendor"]:
                                        if v["level"] == 1:
                                            vendor_type = 'vendor'
                                        else:
                                            vendor_type = 'client'

                                        ck_vendor, created = CkillerVendorClient.objects.get_or_create(
                                            ckiller_sub=ck_sub,
                                            name=v["title"],
                                            type=vendor_type
                                        )
                                        ck_vendor.address = v["address"]
                                        ck_vendor.save()
                                else:
                                    for v in row["vendor"]:
                                        if v["level"] == 1 or v["level"] == 2:
                                            vendor_type = 'vendor'
                                        else:
                                            vendor_type = 'client'

                                        ck_vendor, created = CkillerVendorClient.objects.get_or_create(
                                            ckiller_sub=ck_sub,
                                            name=v["title"],
                                            type=vendor_type
                                        )
                                        ck_vendor.address = v["address"]
                                        ck_vendor.save()

                        res = {
                            "tenant": tenant,
                            "results": data
                        }
                        result.append(res)
                return Response({"result": result}, status=status.HTTP_201_CREATED)
            return Response({"error": "Email is empty"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
