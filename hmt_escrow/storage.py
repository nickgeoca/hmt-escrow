import logging
import codecs
import hashlib
import json
from typing import Dict, Tuple

import ipfsapi
import os

from eth_keys import keys
from p2p import ecies

SHARED_MAC_DATA = os.getenv(
    "SHARED_MAC",
    b'9da0d3721774843193737244a0f3355191f66ff7321e83eae83f7f746eb34350')

LOG = logging.getLogger("api.storage")

if not os.getenv("IPFS_DISABLE"):
    _host = os.getenv("IPFS_HOSTNAME", 'localhost')
    _port = int(os.getenv("IPFS_TCP_PORT", '5001'))
    try:
        API = ipfsapi.connect(_host, _port)
    except Exception as e:
        raise e
        LOG.error("Connection with IPFS failed because of: {}".format(e))


def download(key: str, private_key: bytes) -> Dict:
    """Download a key, decrypt it, and output it as a binary string.

    Args:
        key (str): This is the hash code returned when uploading.
        private_key (str): The private_key to decrypt this string with.

    Returns:
        Dict: returns the contents of the filename which was previously uploaded.
    
    Raises:
        Exception: if reading from IPFS fails.

    """
    try:
        ciphertext = API.cat(key)
    except Exception as e:
        LOG.error("Reading the key with IPFS failed because of: {}".format(e))
        raise e
    msg = _decrypt(private_key, ciphertext)
    return json.loads(msg)


def upload(msg: Dict, public_key: bytes) -> Tuple[str, str]:
    """Upload and encrypt a string for later retrieval.
    This can be manifest files, results, or anything that's been already
    encrypted.

    Args:
        msg (Dict): The message to upload and encrypt.
        public_key (bytes): The public_key to encrypt the file for.

    Returns:
        Tuple[str, str]: returns the contents of the filename which was previously uploaded.
    
    Raises:
        Exception: if adding bytes with IPFS fails.

    """
    manifest_ = json.dumps(msg, sort_keys=True, ensure_ascii=True)
    hash_ = hashlib.sha1(manifest_.encode('utf-8')).hexdigest()
    try:
        key = API.add_bytes(_encrypt(public_key, manifest_))
    except Exception as e:
        LOG.error("Adding bytes with IPFS failed because of: {}".format(e))
        raise e
    return hash_, key


def _decrypt(private_key: bytes, msg: bytes) -> str:
    """Use ECIES to decrypt a message with a given private key and an optional MAC.

    Args:
        private_key (bytes): The private_key to decrypt the message with.
        msg (bytes): The message to be decrypted.
    
    Returns:
        str: returns the plaintext equivalent to the originally encrypted one.

    """
    priv_key = keys.PrivateKey(codecs.decode(private_key, 'hex'))
    e = ecies.decrypt(msg, priv_key, shared_mac_data=SHARED_MAC_DATA)
    return e.decode(encoding='utf-8')


def _encrypt(public_key: bytes, msg: str) -> bytes:
    """Use ECIES to encrypt a message with a given public key and optional MAC.

    Args:
        public_key (bytes): The public_key to encrypt the message with.
        msg (str): The message to be encrypted.
    
    Returns:
        bytes: returns the cryptotext encrypted with the public key.

    """
    pub_key = keys.PublicKey(codecs.decode(public_key, 'hex'))
    msg_bytes = msg.encode(encoding='utf-8')
    return ecies.encrypt(msg_bytes, pub_key, shared_mac_data=SHARED_MAC_DATA)
