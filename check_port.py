
import socket

def check_port(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((ip, port))
        print(f"Port {port} on {ip} is OPEN")
        s.close()
    except Exception as e:
        print(f"Port {port} on {ip} is CLOSED or UNREACHABLE: {e}")

if __name__ == "__main__":
    check_port("192.168.2.213", 8883)
