import ftplib
import ssl
import socket
import os
import hashlib

IP = "192.168.2.213"
ACCESS_CODE = "05956746"
REMOTE_FILE = "/factoryos/debug_prot_c.3mf"
LOCAL_SOURCE = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf"
DOWNLOAD_DEST = "downloaded_check.3mf"

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
        
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile('r')
        self.welcome = self.getresp()
        return self.welcome

def calculate_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def verify_integrity():
    print(f"Verifying Integrity of {REMOTE_FILE}...")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        ftps = ImplicitFTP_TLS(timeout=30)
        ftps.context = context
        ftps.connect(host=IP, port=990)
        ftps.login(user="bblp", passwd=ACCESS_CODE)
        ftps.prot_p()
        print("✅ Logged in.")
        
        print(f"Downloading {REMOTE_FILE} -> {DOWNLOAD_DEST}...")
        
        with open(DOWNLOAD_DEST, "wb") as f:
            try:
                ftps.retrbinary(f"RETR {REMOTE_FILE}", f.write)
            except (ssl.SSLError, TimeoutError) as e:
                print(f"⚠️  Ignored SSL shutdown error during download: {e}")
            except ftplib.error_perm as e:
                print(f"❌ Download Failed: {e}")
                # Try fallback path
                if "550" in str(e):
                    alt_path = "/sdcard" + REMOTE_FILE
                    print(f"Trying alternative path: {alt_path}")
                    ftps.retrbinary(f"RETR {alt_path}", f.write)

        print("✅ Download Complete.")
        ftps.quit()
        
        # Compare MD5
        local_md5 = calculate_md5(LOCAL_SOURCE)
        remote_md5 = calculate_md5(DOWNLOAD_DEST)
        
        print(f"\n--- INTEGRITY CHECK ---")
        print(f"Local Source MD5: {local_md5}")
        print(f"Downloaded MD5:   {remote_md5}")
        
        if local_md5 == remote_md5:
            print("✅ HASH MATCH! The file on printer is identical.")
        else:
            print("❌ HASH MISMATCH! Upload corrupted.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_integrity()
