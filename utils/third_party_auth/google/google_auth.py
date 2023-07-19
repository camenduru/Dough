from dotenv import load_dotenv
import os
from httpx_oauth.clients.google import GoogleOAuth2
import asyncio

from shared.constants import SERVER, ServerType

load_dotenv()

if SERVER != ServerType.PRODUCTION.value:
    GOOGLE_AUTH_CLIENT_ID = os.getenv('GOOGLE_AUTH_CLIENT_ID', '')
    GOOGLE_SECRET = os.getenv('GOOGLE_SECRET', '')
    REDIRECT_URI = os.getenv('REDIRECT_URI', '')
else:
    import boto3
    ssm = boto3.client("ssm", region_name="ap-south-1")

    GOOGLE_AUTH_CLIENT_ID = ssm.get_parameter(Name='/backend/banodoco/google_client_id')['Parameter']['Value']
    GOOGLE_SECRET = ssm.get_parameter(Name='/backend/banodoco/google_secret')['Parameter']['Value']
    REDIRECT_URI = ssm.get_parameter(Name='/backend/banodoco/google_redirect_url')['Parameter']['Value']

async def get_authorization_url(client: GoogleOAuth2, redirect_uri: str):
    authorization_url = await client.get_authorization_url(redirect_uri, scope=["profile", "email"])
    return authorization_url

def get_google_auth_url():
    client: GoogleOAuth2 = GoogleOAuth2(GOOGLE_AUTH_CLIENT_ID, GOOGLE_SECRET)
    authorization_url = asyncio.run(
        get_authorization_url(client, REDIRECT_URI))
    return f"""<a target='_self' href='{authorization_url}'> Google login </a>"""