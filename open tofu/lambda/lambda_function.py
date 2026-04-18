import json
from urllib.parse import unquote_plus
import boto3
import os
import logging

print('Loading function')
logger = logging.getLogger()
logger.setLevel("INFO")

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')

table = dynamodb.Table(os.getenv("table"))


def lambda_handler(event, context):
    logger.info(json.dumps(event, indent=2))

    # Récupération du nom du bucket et de la clé depuis l'event S3
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    logger.info(f"Bucket: {bucket}, Key: {key}")

    # La clé est de la forme : alice/POST#uuid/nomimage.jpg
    # On extrait l'utilisateur et l'id du post
    parts = key.split('/')
    user = parts[0]    # ex: "alice"
    post_id = parts[1] # ex: "POST#uuid"

    logger.info(f"User: {user}, Post ID: {post_id}")

    # Appel à Rekognition : max 5 labels, confiance > 75%
    label_data = rekognition.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": key
            }
        },
        MaxLabels=5,
        MinConfidence=75
    )
    logger.info(f"Labels data : {label_data}")

    # Extraction des noms des labels
    labels = [label["Name"] for label in label_data["Labels"]]
    logger.info(f"Labels detected : {labels}")

    # Mise à jour DynamoDB : image (chemin S3) + labels détectés
    table.update_item(
        Key={
            "user": user,
            "id": post_id
        },
        UpdateExpression="SET image = :img, labels = :lbl",
        ExpressionAttributeValues={
            ":img": key,
            ":lbl": labels
        }
    )

    logger.info(f"DynamoDB updated for post {post_id} of user {user}")

    return {
        "statusCode": 200,
        "body": json.dumps({"labels": labels})
    }
