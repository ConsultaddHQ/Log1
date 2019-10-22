# Email ids
FINANCE = "finance@consultadd.com"
RELATIONS = "relations@consultadd.com"
RECRUITMENT = "recruitment@consultadd.com"
ENGINEERING = "engineering@consultadd.com"

SUPERADMIN = ["sudeep.b@consultadd.com"]


# Discord Webhooks
# Announcement Channel
announcement_url = 'https://discordapp.com/api/webhooks/538357619190923265/2JLKDwILDNqLj7YlmGS-ZuQxx26r4JRK91TvE8cHMtLZbvCdUoHyXLZ20uuaGmFPE5fF'

# Offer Announcement Channel
offer_url = "https://discordapp.com/api/webhooks/541981508815028224/21xjw0j7AE3bfmcqJ7B-b19sFKzO5eIwpSXe8OTVtoRK65XQIy5FhN3LhJ1ktE1Wsth6"

# Recruitment Channel
recruitment_url = "https://discordapp.com/api/webhooks/626004000273072128/QH309Z7YfNr7ER9aFeWDpRJX_1eAR2soVzzkBaVAq7CWfOV3Nuzyz9n-IhnVrjuEAwX3"

# 45dayslimit Channel
pool_channel_url = "https://discordapp.com/api/webhooks/626001183076778004/KzKrcylbIantpPtFKLmNTGxILSTYBn4Q07MyDTLYbzB0Tj8m1JrMFBe97NJVTWKuXd_5"



import unittest
import boto3
from moto import mock_dynamodb2


class TestDynamo(unittest.TestCase):

    def setUp(self):
        pass

    @mock_dynamodb2
    def test_recoverBsaleAssociation(self):

        table_name = 'demo1'
        dynamodb = boto3.resource('dynamodb', 'us-east-1')

        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'key',
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

        item = {}
        item['key'] = 'value'

        table.put_item(Item=item)

        self.assertTrue("key" in item)
        self.assertEquals(item["key"], "value")


if __name__ == '__main__':
    unittest.main()
