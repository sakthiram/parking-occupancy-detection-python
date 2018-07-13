import boto3
import json
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from PIL import Image
import io
import uuid
import datetime, time, pytz

# Function to convert a standard Python dict to a boto3 dynamodb item
def dict_to_item(raw):
    if type(raw) is dict:
        resp = {}
        for k,v in raw.items():
            if type(v) is str:
                resp[k] = {
                    'S': v
                }
            elif type(v) is int:
                resp[k] = {
                    'I': str(v)
                }
            elif type(v) is dict:
                resp[k] = {
                    'M': dict_to_item(v)
                }
            elif type(v) is list:
                resp[k] = []
                for i in v:
                    resp[k].append(dict_to_item(i))
        return resp
    elif type(raw) is str:
        return {
            'S': raw
        }
    elif type(raw) is int:
        return {
            'I': str(raw)
        }

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def label_the_boxes(image):
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
    print ("\nlambdaParams => ", lambdaParams, "\n")
    # TODO: Add to DynamoDB along with Application Attribute
    app_labels = ["Vehicle", "Automobile", "Transportation", "Car", "Bus", "Van"]

    rekognition = boto3.client("rekognition", "us-west-2")
    boxes = {}
    lambdaResults = {}
    for box_key, box_val in lambdaParams.items():
        region_coordinates = [int(x['I']) for x in box_val]
        boxes[box_key] = region_coordinates
        box_image = image.crop(region_coordinates)
        # box_image.show()
        imgByteArr = io.BytesIO()
        box_image.save(imgByteArr, format='JPEG')
        imgByteArr = imgByteArr.getvalue()

        try:
            response = rekognition.detect_labels(
                        Image = {
                            "Bytes": imgByteArr
                        }
                        # MaxLabels = 10
                        # MinConfidence = 60
            )
            print(box_key, ": ", response["Labels"], "\n")
            predicted_labels = [x['Name'] for x in response["Labels"]]
            if (any(x in predicted_labels for x in app_labels)):
                lambdaResults[box_key] = "OCCUPIED"
            else:
                lambdaResults[box_key] = "FREE"
        except:
            print("Error Message for: ", box_key, "\n")

    # table.update_item(
    #     Key = {
    #         'DSN': item_dsn,
    #         'Timestamp': item_timestamp
    #     },
    #     UpdateExpression='SET lambdaResults = :val1',
    #     ExpressionAttributeValues={
    #         ':val1': lambdaResults
    #     }
    # )

    utc_date = pytz.timezone('UTC').localize(datetime.datetime.utcnow())
    local_date = utc_date.astimezone(pytz.timezone('US/Pacific'))
    timestamp = local_date.strftime('%Y-%m-%dT%H:%M:%S')
    response = table.put_item(
    Item = {
        'DSN': 'W3',
        'Timestamp': timestamp,
        'BattVol': str(3450),
        'isBattPowered': True,
        'isOnline': False,
        'Application': 'car-parking-occupancy-detection',
        'lambdaParams': dict_to_item(boxes),
        'lambdaResults': dict_to_item(lambdaResults)
    }
    )
    print("Added the results to DynamoDB Table @ ", timestamp)

def lambda_handler(event, context):
    s3Client = boto3.client('s3')
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), key)
        s3Client.download_file(bucket, key, download_path)
        image = Image.open(download_path)
        label_the_boxes(image)

# image = Image.open("parking_7thfloor_4MP.jpg")
# label_the_boxes(image)