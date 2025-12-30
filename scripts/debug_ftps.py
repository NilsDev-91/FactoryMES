import ftplib
import ssl
import sys

IP = "192.168.2.213"
ACCESS_CODE = "05956746"

print(f"Testing Standard FTPS (Implicit) to {IP}...")

try:
    # Implicit TLS means we connect with SSL immediately on port 990
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    ftps = ftplib.FTP_TLS(context=context)
    ftps.connect(IP, 990)
    ftps.login("bblp", ACCESS_CODE)
    ftps.prot_p() # Secure data connection
    
    print("✅ Connected & Logged In!")
    
    print("Listing files...")
    ftps.retrlines('LIST /')
    
    print("✅ LIST successful.")
    ftps.quit()

except Exception as e:
    print(f"❌ Failed: {e}")
