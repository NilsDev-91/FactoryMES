import asyncio
import aioftp
import ssl
import logging

# Configure Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("DebugFTPS")

IP = "192.168.2.213"
ACCESS_CODE = "05956746"

async def test_ftps():
    logger.info(f"Testing aioftp (Implicit TLS) to {IP}:990...")
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        async with aioftp.Client.context(
            host=IP,
            port=990,
            user="bblp",
            password=ACCESS_CODE,
            ssl=context,
            socket_timeout=10, 
            path_timeout=10
        ) as client:
            logger.info("✅ Connected & Logged In!")
            
            print("Listing files in /...")
            files = await client.list("/")
            for path, info in files:
                print(f" - {path}")
                
            logger.info("✅ Directory List Success!")
            
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        # Print full traceback
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        # aioftp might have issues with Proactor on Windows?
        # Standard loop policy is safer for some SSL things?
        pass
    asyncio.run(test_ftps())
