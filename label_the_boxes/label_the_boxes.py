import boto3
import json
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from PIL import Image
import io
import uuid

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

    rekognition = boto3.client("rekognition", "us-west-2")
    for box_key, box_val in lambdaParams.items():
        region_coordinates = [int(x['I']) for x in box_val]
        box_image = image.crop(region_coordinates)
        box_image.show()
        imgByteArr = io.BytesIO()
        box_image.save(imgByteArr, format='JPEG')
        imgByteArr = imgByteArr.getvalue()

        try:
            response = rekognition.detect_labels(
                        Image = {
                            "Bytes": imgByteArr
                        },
                        MaxLabels = 10
                        # MinConfidence = 60
            )
            print(box_key, ": ", response["Labels"], "\n")
        except:
            print("Error Message for: ", box_key, "\n")

def lambda_handler(event, context):
    s3Client = boto3.client('s3')
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), key)
        s3Client.download_file(bucket, key, download_path)
        image = Image.open(download_path)
        label_the_boxes(image)

image = Image.open("parking_7thfloor_12MP.jpg")
label_the_boxes(image)