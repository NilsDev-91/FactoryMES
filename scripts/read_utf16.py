
import sys

def read_log(path):
    try:
        with open(path, 'rb') as f:
            content = f.read().decode('utf-16-le')
            print(content)
    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    read_log('test_output.log')
