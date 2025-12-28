import asyncio
import sys
import os
import httpx
import webbrowser
import urllib.parse

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

# Override settings for script usage if needed, but assuming .env is loaded
# or config is populated from environment.

async def get_ebay_tokens():
    print("--- eBay User Token Generator ---")
    
    if not all([settings.EBAY_APP_ID, settings.EBAY_CERT_ID, settings.EBAY_RU_NAME]):
        print("Error: EBAY_APP_ID, EBAY_CERT_ID, and EBAY_RU_NAME must be set in your .env file.")
        return

    # 1. Build Authorization URL
    scopes = [
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        "https://api.ebay.com/oauth/api_scope/sell.inventory" # Optional, but good to have
    ]
    scope_string = " ".join(scopes)
    
    params = {
        "client_id": settings.EBAY_APP_ID,
        "redirect_uri": settings.EBAY_RU_NAME,
        "response_type": "code",
        "scope": scope_string,
        "prompt": "login"
    }
    
    auth_url = f"{settings.EBAY_AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    print("\n1. Opening browser to authorize application...")
    print(f"URL: {auth_url}")
    webbrowser.open(auth_url)
    
    print("\n2. After authorizing, you will be redirected to your RuName URL.")
    code = input("Paste the 'code' parameter from the URL here: ").strip()
    
    if not code:
        print("No code provided. Exiting.")
        return

    # 3. Exchange Code for Tokens
    print("\n3. Exchanging code for tokens...")
    
    token_url = f"{settings.EBAY_API_BASE_URL}/identity/v1/oauth2/token"
    
    # Basic Auth for the token endpoint
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
                print("\nSUCCESS! Here are your tokens:\n")
                print(f"Access Token (Expires in {tokens.get('expires_in')}s):")
                print(tokens.get("access_token")[:20] + "...")
                
                refresh_token = tokens.get("refresh_token")
                print("\nREFRESH TOKEN (Add this to your .env file as EBAY_REFRESH_TOKEN):")
                print("-" * 60)
                print(refresh_token)
                print("-" * 60)
                
                print(f"\nRefresh Token Expires in: {tokens.get('refresh_token_expires_in')} seconds")
                
            else:
                print(f"\nFailed to retrieve tokens. HTTP {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"\nError occurred: {e}")

if __name__ == "__main__":
    asyncio.run(get_ebay_tokens())
