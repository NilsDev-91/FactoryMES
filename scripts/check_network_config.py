import socket
import sys
import os

def get_lan_ip():
    """
    Determines the outgoing LAN IP by connecting a dummy UDP socket to a public DNS.
    This method avoids iterating interfaces and gets the one the OS chooses for internet traffic.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_port_binding(port: int) -> bool:
    """
    Checks if a port can be bound (is free).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', port))
        return True
    except Exception as e:
        return False
    finally:
        s.close()

def main():
    print("🔍 Checking Network Configuration for PrinterCommander...")
    print("-" * 50)
    
    # 1. IP Check
    ip = get_lan_ip()
    print(f"Detected LAN IP: {ip}")
    
    if ip.startswith("127."):
        print("❌ CRITICAL: Resolved to Loopback. Printer will FAIL to download files.")
        print("   -> Ensure you are connected to a network.")
    elif ip.startswith("172."):
        print("⚠️ WARNING: Detected Docker Bridge IP range.")
        print("   -> If running in Docker, this is normal.")
        print("   -> If running on Host, ensure Printer is on the same subnet.")
    elif ip.startswith("192.168.") or ip.startswith("10."):
        print("✅ Looks like a valid LAN IP.")
    else:
        print(f"ℹ️ Note: IP {ip} is valid but not standard Home/Office LAN range.")
    
    print("-" * 50)
    
    # 2. Port Check
    port = 9000
    if check_port_binding(port):
        print(f"✅ Port {port} is FREE. Backend can bind to it.")
    else:
        print(f"⚠️ WARNING: Port {port} is BUSY or Restricted.")
        print("   -> FactoryOS Backend might fail to start if it needs this port.")
        print("   -> Or, FactoryOS is ALREADY running (which is good).")

if __name__ == "__main__":
    main()
