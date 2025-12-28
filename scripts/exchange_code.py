import asyncio
import httpx
import sys
import os
import urllib.parse
from base64 import b64encode

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

async def exchange_code():
    # URL-encoded code from user
    raw_code = "v%5E1.1%23i%5E1%23f%5E0%23r%5E1%23p%5E3%23I%5E3%23t%5EUl41Xzc6QzRFOUQ3RjAzRDQxMEJENDMzMTRBMTYxMjMwM0U4QjZfMV8xI0VeMTI4NA%3D%3D"
    code = urllib.parse.unquote(raw_code)
    
    print(f"Exchanging code: {code}")
    
    token_url = f"{settings.EBAY_API_BASE_URL}/identity/v1/oauth2/token"
    
    auth = httpx.BasicAuth(settings.EBAY_APP_ID, settings.EBAY_CERT_ID)
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.EBAY_RU_NAME
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(token_url, data=data, auth=auth)
            
            if response.status_code == 200:
                tokens = response.json()
                refresh_token = tokens.get("refresh_token")
                print(f"REFRESH_TOKEN:{refresh_token}")
            else:
                print(f"FAILED: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(exchange_code())
