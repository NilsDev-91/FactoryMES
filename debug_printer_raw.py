
import asyncio
import sys
import aiomqtt
import ssl
import json

# Provided credentials
printer_ip = "192.168.2.213"
printer_access_code = "05956746"
printer_serial = "03919C461802608"

async def main():
    tls_params = aiomqtt.TLSParameters(
        cert_reqs=ssl.CERT_NONE,
        tls_version=ssl.PROTOCOL_TLS,
        ciphers=None
    )
    
    print("Connecting...")
    async with aiomqtt.Client(
        hostname=printer_ip,
        port=8883,
        username="bblp",
        password=printer_access_code,
        tls_params=tls_params,
        identifier=f"debug-{printer_serial}"
    ) as client:
        print("Connected!")
        await client.subscribe(f"device/{printer_serial}/report")
        
        async for message in client.messages:
            payload = message.payload
            if isinstance(payload, bytes):
                payload = payload.decode()
            print("RAW PAYLOAD:", payload)
            # Break after first message to avoid flooding
            break

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
