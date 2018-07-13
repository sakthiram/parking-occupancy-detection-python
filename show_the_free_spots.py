import boto3
import json
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from PIL import Image, ImageDraw

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

im = Image.open("parking_7thfloor_4MP.jpg")
draw = ImageDraw.Draw(im)

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('CE_Status_Table')

response = table.query(
    KeyConditionExpression = Key('DSN').eq('W3'), # Add constrain for application
    ScanIndexForward = False,
    Limit = 1
)

print(response['Items'][0])
# for i in response[u'Items']:
#     print(json.dumps(i, cls=DecimalEncoder))

item = json.dumps(response['Items'][0], cls=DecimalEncoder)
data = json.loads(item)

lambdaParams = data["lambdaParams"]
lambdaResults = data["lambdaResults"]

for box_key, box_val in lambdaParams.items():
    region_coordinates = [int(x['I']) for x in box_val]
    if lambdaResults[box_key]['S'] == "OCCUPIED":
        draw.rectangle(region_coordinates, outline=(255,51,0,255)) # RED
    else:
        draw.rectangle(region_coordinates, outline=(0,153,51,255)) # GREEN

im.show()