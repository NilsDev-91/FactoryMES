import ftplib
import ssl
import socket
import os

IP = "192.168.2.213"
ACCESS_CODE = "05956746"
TARGET_DIR = "/sdcard/factoryos"

# Custom class for Implicit TLS (Reused from commander.py fix)
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

def check_files():
    print(f"Connecting to {IP}:990...")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        ftps = ImplicitFTP_TLS(timeout=10)
        ftps.context = context
        ftps.connect(host=IP, port=990)
        ftps.login(user="bblp", passwd=ACCESS_CODE)
        ftps.prot_p()
        
        print("✅ Logged in.")
        
        # Start at root
        ftps.cwd("/")
        print("Listing Root...")
        root_files = []
        ftps.dir(root_files.append)
        for f in root_files: print(f"  {f}")

        # Try to go to factoryos directly in root
        if "factoryos" in str(root_files):
             print("Entering /factoryos...")
             ftps.cwd("/factoryos")
             
             final_files = []
             ftps.dir(final_files.append)
             print("\n--- FILE LIST (/factoryos) ---")
             found_target = False
             for line in final_files:
                print(line)
                if ".3mf" in line:
                    found_target = True
             print("-----------------")
             
             if not found_target:
                print("⚠️  No .3mf files found in target directory!")
             else:
                print("✅ .3mf files exist. Check file size (should not be 0).")
        
        # Fallback check for sdcard nesting
        elif "sdcard" in str(root_files):
            print("Entering /sdcard...")
            ftps.cwd("sdcard")
            sd_files = []
            ftps.dir(sd_files.append)
            for f in sd_files: print(f"  {f}")
            
            if "factoryos" in str(sd_files):
                 print("Entering /sdcard/factoryos...")
                 ftps.cwd("factoryos")
                 
                 final_files = []
                 ftps.dir(final_files.append)
                 print("\n--- FILE LIST (/sdcard/factoryos) ---")
                 found_target = False
                 for line in final_files:
                    print(line)
                    if ".3mf" in line:
                        found_target = True
                 print("-----------------")
                 
                 if not found_target:
                    print("⚠️  No .3mf files found in target directory!")
                 else:
                    print("✅ .3mf files exist. Check file size (should not be 0).")
            else:
                print("❌ 'factoryos' directory not found in /sdcard")
        else:
             print("❌ 'sdcard' directory not found in root")

        ftps.quit()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_files()
