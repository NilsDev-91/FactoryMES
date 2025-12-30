import asyncio
import os
import sys
import logging
import ftplib
import ssl
import socket

# Ensure app modules are found
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.DEBUG)

IP = "192.168.2.213"
ACCESS_CODE = "05956746"
TEST_FILE = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf"
TARGET_FILENAME = "debug_prot_c.3mf"

def test_prot_c_upload():
    print(f"Testing Upload with PROT C to {IP}...")
    
    # Custom class for Implicit TLS
    class ImplicitFTP_TLS(ftplib.FTP_TLS):
        def __init__(self, host='', timeout=60):
            super().__init__(host=host, timeout=timeout)
            
        def connect(self, host='', port=0, timeout=-999):
            if host != '':
                self.host = host
            if port > 0:
                self.port = port
            if timeout != -999:
                self.timeout = timeout
                
            self.sock = socket.create_connection((self.host, self.port), self.timeout)
            self.af = self.sock.family
            
            # IMPLICIT TLS: Wrap immediately
            self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
            self.file = self.sock.makefile('r')
            self.welcome = self.getresp()
            return self.welcome

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        ftps = ImplicitFTP_TLS(timeout=30)
        ftps.context = context
        ftps.connect(host=IP, port=990)
        ftps.login(user="bblp", passwd=ACCESS_CODE)
        
        # Revert to PROT P (Secure Data Channel)
        ftps.prot_p()
        print("✅ PROT P enabled.")

        # Ensure directory exists on clean SD
        print("Creating directory structure...")
        try:
            ftps.cwd("/")
        except:
            pass

        # Try to make factoryos dir
        target_dir_name = "factoryos"
        full_target_dir = f"/sdcard/{target_dir_name}" # Common Bambu path
        
        try:
            # Try absolute path first
            ftps.mkd(full_target_dir)
            print(f"✅ Created {full_target_dir}")
        except Exception as e:
            print(f"⚠️ MKD {full_target_dir} failed: {e}")
            # Try relative if we are already in sdcard
            try: 
                ftps.mkd(target_dir_name)
                print(f"✅ Created {target_dir_name} (relative)")
                full_target_dir = target_dir_name # Update target
            except Exception as e2:
                 print(f"⚠️ MKD {target_dir_name} failed: {e2}")

        print(f"CWD to {full_target_dir}...")
        ftps.cwd(full_target_dir)
        
        # Delete if exists to ensure fresh write
        try:
             ftps.delete(TARGET_FILENAME)
             print(f"🗑️ Deleted old {TARGET_FILENAME}")
        except:
             pass

        print(f"STOR {TARGET_FILENAME}")
        local_size = os.path.getsize(TEST_FILE)
        print(f"Local text file size: {local_size} bytes")

        with open(TEST_FILE, "rb") as f:
            try:
                ftps.storbinary(f"STOR {TARGET_FILENAME}", f)
            except (TimeoutError, ssl.SSLError, socket.timeout) as e:
                 print(f"⚠️  Ignored expected SSL Shutdown error: {e}")
        
        print("✅ Upload Complete! Verifying size...")
        
        # Verify size
        files = []
        ftps.dir(files.append)
        for line in files:
            if TARGET_FILENAME in line:
                print(f"Remote File: {line}")
                # Parse size roughly if needed, or just visual check
        
        ftps.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prot_c_upload()
