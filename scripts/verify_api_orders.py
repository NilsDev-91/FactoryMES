import asyncio
import httpx
import json

API_URL = "http://localhost:8000/api/orders"

async def verify_api():
    print("🕵️ Verifying Orders API...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL)
            
            if response.status_code != 200:
                print(f"❌ API Request Failed: {response.status_code}")
                print(response.text)
                return

            orders = response.json()
            print(f"✅ Fetched {len(orders)} orders.")
            
            found_blue = False
            for order in orders:
                if not order.get("jobs"):
                    continue
                
                print(f"Order {order['ebay_order_id']} has {len(order['jobs'])} jobs:")
                for job in order['jobs']:
                    reqs = job.get('filament_requirements')
                    print(f"  - Job {job['id']} Status: {job['status']}")
                    print(f"    Requirements: {reqs}")
                    
                    if reqs and any(r.get('hex_color') == "#0000FF" for r in reqs):
                        found_blue = True

            if found_blue:
                print("\n✅ SUCCESS: Found Job with Blue Filament requirement in API response!")
            else:
                print("\n⚠️  WARNING: Did not find any job with Blue Filament requirement (Did you run simulate_blue_order.py?)")

    except Exception as e:
        print(f"❌ Script Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_api())
