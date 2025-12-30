import urllib.request
import urllib.parse
import json
import os
import uuid

def test_upload():
    url = "http://127.0.0.1:8000/api/products/upload"
    filepath = "test_dummy.3mf"
    boundary = "boundary" + str(uuid.uuid4())
    
    # Create dummy file
    with open(filepath, "wb") as f:
        f.write(b"dummy content")
        
    try:
        with open(filepath, "rb") as f:
            file_content = f.read()

        # Build multipart/form-data
        data = []
        data.append(f'--{boundary}'.encode('utf-8'))
        data.append(f'Content-Disposition: form-data; name="file"; filename="{filepath}"'.encode('utf-8'))
        data.append(b'Content-Type: application/octet-stream')
        data.append(b'')
        data.append(file_content)
        data.append(f'--{boundary}--'.encode('utf-8'))
        data.append(b'')
        
        body = b'\r\n'.join(data)
        
        req = urllib.request.Request(url, data=body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        
        with urllib.request.urlopen(req) as response:
            print(f"Status Code: {response.getcode()}")
            print(f"Response Body: {response.read().decode('utf-8')}")
            
    except urllib.error.HTTPError as e:
         print(f"HTTP Error: {e.code}")
         print(f"Response: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == "__main__":
    test_upload()
