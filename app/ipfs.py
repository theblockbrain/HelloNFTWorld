import requests
from app.main import IPFS_AUTH


def read_ipfs_file(URI):
    BASE_URL = "https://ipfs.infura.io:5001/api/v0/cat?arg="
    if "ipfs://" in URI:
        id = URI[7:].strip("/")
        r = requests.post(f"{BASE_URL}{id}", headers={"Authorization": IPFS_AUTH})
        try:
            metadata = r.json()
            return metadata
        except:
            print("Received something that wasn't JSON :(")
    else:
        print("I don't know how to handle that IPFS URI yet!")
        return None


def get_whole_directory(URI):
    BASE_URL = "https://ipfs.infura.io:5001/api/v0/get?arg="
    if "ipfs://" in URI:
        id = URI[7:].strip("/")
        r = requests.post(f"{BASE_URL}{id}", auth=IPFS_AUTH)
        return r.text
    else:
        return None
