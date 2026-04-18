#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
import boto3
from botocore.config import Config
import os
import uuid
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from getSignedUrl import getSignedUrl

load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################


@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):
    """
    Crée un nouveau post.
    - Le titre et le corps viennent du body de la requête
    - L'auteur vient du header 'authorization'
    - Un id unique est généré (préfixé POST#)
    """
    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")

    post_id = f"POST#{uuid.uuid4()}"

    item = {
        "user": authorization,      # clé de partition
        "id": post_id,              # clé de tri
        "title": post.title,
        "body": post.body,
        "image": None,
        "labels": []
    }

    res = table.put_item(Item=item)

    # On retourne l'item créé (utile pour récupérer l'id côté front)
    return item


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    """
    Récupère tous les posts.
    - Si un user est fourni en query param : on fait un QUERY (efficace)
    - Sinon : on fait un SCAN de toute la table
    """
    if user:
        logger.info(f"Récupération des postes de : {user}")
        res = get_posts_by_user(user)
    else:
        logger.info("Récupération de tous les postes")
        res = get_all_posts_scan()

    # Pour chaque post, si une image existe on génère une URL pré-signée
    posts = []
    for item in res:
        if item.get("image"):
            item["image"] = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    "Bucket": bucket,
                    "Key": item["image"],
                }
            )
        posts.append(item)

    return posts


def get_posts_by_user(user: str):
    """Récupère les posts d'un utilisateur via un QUERY sur la partition key."""
    from boto3.dynamodb.conditions import Key
    res = table.query(
        KeyConditionExpression=Key("user").eq(user)
    )
    return res["Items"]


def get_all_posts_scan():
    """Récupère tous les posts via un SCAN complet de la table."""
    res = table.scan()
    return res["Items"]


@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, authorization: str | None = Header(default=None)):
    """
    Supprime un post.
    - Récupère d'abord l'item pour savoir s'il a une image
    - Supprime l'image dans S3 si elle existe
    - Supprime l'item dans DynamoDB
    """
    logger.info(f"post id : {post_id}")
    logger.info(f"user: {authorization}")

    # Récupération de l'item pour savoir s'il a une image associée
    response = table.get_item(
        Key={
            "user": authorization,
            "id": post_id
        }
    )
    item = response.get("Item")

    # S'il y a une image, on la supprime du bucket S3
    if item and item.get("image"):
        s3_client.delete_object(
            Bucket=bucket,
            Key=item["image"]
        )
        logger.info(f"Image supprimée de S3 : {item['image']}")

    # Suppression de l'item dans DynamoDB
    result = table.delete_item(
        Key={
            "user": authorization,
            "id": post_id
        }
    )

    return result


#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str,filetype: str, postId: str,authorization: str | None = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################
