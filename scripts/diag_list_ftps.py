import asyncio
import os
import sys
import socket
import ssl
import ftplib

sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer

async def list_printer_files():
    async with async_session_maker() as session:
        printer = await session.get(Printer, "03919C461802608")
        if not printer:
            print("Printer not found.")
            return

        output = []
        output.append(f"Connecting to {printer.ip_address}...")

        def _sync_list():
            class ImplicitFTP_TLS(ftplib.FTP_TLS):
                def connect(self, host='', port=0, timeout=-999):
                    if host != '': self.host = host
                    if port > 0: self.port = port
                    if timeout != -999: self.timeout = timeout
                    self.sock = socket.create_connection((self.host, self.port), self.timeout)
                    self.af = self.sock.family
                    self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
                    self.file = self.sock.makefile('r')
                    self.welcome = self.getresp()
                    return self.welcome

            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            ftps = ImplicitFTP_TLS(timeout=30)
            ftps.context = context
            ftps.connect(host=printer.ip_address, port=990)
            ftps.login(user="bblp", passwd=printer.access_code)
            ftps.prot_p()

            output.append("\n=== Root Directory (/) ===")
            files = []
            ftps.retrlines('LIST', files.append)
            for f in files:
                output.append(f)
                
            ftps.quit()
            return output

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _sync_list)
        
        with open("ftps_listing.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(result))
        print("\n".join(result))
        print("\nSaved to ftps_listing.txt")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_printer_files())
