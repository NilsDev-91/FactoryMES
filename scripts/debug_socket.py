import socket
import ssl
import sys

IP = "192.168.2.213"
PORT = 990

print(f"Testing Standard Socket to {IP}:{PORT}...")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30)
    print("Initiating TCP Connect (30s timeout)...")
    s.connect((IP, PORT))
    print("✅ Raw TCP Connect Success!")
    
    import time
    time.sleep(1.0) 
    
    # Try SSL Wrap manually with specific protocol
    print("Attempting SSL Wrap (TLS 1.2)...")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    ss = context.wrap_socket(s, server_hostname=IP)
    print("✅ SSL Handshake Success!")
    print("✅ SSL Handshake Success!")
    
    ss.close()

except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
