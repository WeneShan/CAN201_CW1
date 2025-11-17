import argparse
import socket
import json
import struct
import hashlib
import os
import time
import sys
import mmap
import logging
from typing import Optional, Dict, Any, Tuple, Generator
from pathlib import Path

# Protocol constants
OP_SAVE, OP_DELETE, OP_GET, OP_UPLOAD, OP_DOWNLOAD, OP_BYE, OP_LOGIN, OP_ERROR = (
    'SAVE', 'DELETE', 'GET', 'UPLOAD', 'DOWNLOAD', 'BYE', 'LOGIN', "ERROR"
)
TYPE_FILE, TYPE_DATA, TYPE_AUTH, DIR_EARTH = 'FILE', 'DATA', 'AUTH', 'EARTH'
FIELD_OPERATION, FIELD_DIRECTION, FIELD_TYPE, FIELD_USERNAME, FIELD_PASSWORD, FIELD_TOKEN = (
    'operation', 'direction', 'type', 'username', 'password', 'token'
)
FIELD_KEY, FIELD_SIZE, FIELD_TOTAL_BLOCK, FIELD_MD5, FIELD_BLOCK_SIZE = (
    'key', 'size', 'total_block', 'md5', 'block_size'
)
FIELD_STATUS, FIELD_STATUS_MSG, FIELD_BLOCK_INDEX = 'status', 'status_msg', 'block_index'
DIR_REQUEST, DIR_RESPONSE = 'REQUEST', 'RESPONSE'

# Configuration
SERVER_PORT = 1379
RE_TRANSMISSION_TIME = 20
PROGRESS_BAR_LENGTH = 50
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB


class NetworkManager:
    """Handles network communication including packet packing, parsing and sending"""

    @staticmethod
    def pack_message(json_data: Dict[str, Any], bin_data: Optional[bytes] = None) -> bytes:
        """Pack JSON data and binary data into a network packet"""
        json_str = json.dumps(json_data, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        json_len = len(json_bytes)
        bin_len = len(bin_data) if bin_data else 0
        header = struct.pack('!II', json_len, bin_len)
        return header + json_bytes + (bin_data or b'')

    @staticmethod
    def unpack_message(client_socket: socket.socket) -> Tuple[Optional[Dict[str, Any]], Optional[bytes]]:
        """Unpack network packet into JSON data and binary data"""
        try:
            # Read 8-byte header
            header = b''
            while len(header) < 8:
                chunk = client_socket.recv(8 - len(header))
                if not chunk:
                    return None, None
                header += chunk
            json_len, bin_len = struct.unpack('!II', header)

            # Read JSON data
            json_data = b''
            while len(json_data) < json_len:
                chunk = client_socket.recv(json_len - len(json_data))
                if not chunk:
                    return None, None
                json_data += chunk

            # Read binary data
            bin_data = b''
            if bin_len > 0:
                while len(bin_data) < bin_len:
                    chunk = client_socket.recv(bin_len - len(bin_data))
                    if not chunk:
                        return None, None
                    bin_data += chunk

            return json.loads(json_data.decode('utf-8')), bin_data
        except Exception as e:
            logging.error(f"Message parsing error: {e}")
            return None, None

    @staticmethod
    def send_message(sock: socket.socket, operation: str, data_type: str,
                     payload: Dict[str, Any], bin_data: Optional[bytes] = None,
                     token: Optional[str] = None) -> bool:
        """Create and send a message through the socket"""
        message = {
            FIELD_OPERATION: operation,
            FIELD_TYPE: data_type,
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_TOKEN: token
        }
        message.update(payload)

        try:
            packed_data = NetworkManager.pack_message(message, bin_data)
            sock.sendall(packed_data)
            return True
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
            return False


class ErrorHandler:
    """Handles error checking and processing for server responses"""

    @staticmethod
    def check_error(json_data: Dict[str, Any], status_code: int, client_socket: socket.socket):
        """Check for error status codes and handle accordingly"""
        if 400 <= status_code < 500:
            error_msg = json_data.get(FIELD_STATUS_MSG, "Unknown error")
            logging.error(f"Server error: {error_msg} (code: {status_code})")
            print(f"\nServer response: {error_msg}")
            print(f"Status code: {status_code}")
            print("Client exit.")
            client_socket.close()
            sys.exit(1)


class AuthenticationService:
    """Manages user authentication and token management"""

    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.token = None

    def login(self, student_id: str) -> bool:
        """Perform user login and retrieve authentication token"""
        if student_id == "YeWenjie":
            self._sending_to_three_body()
            return False

        password = hashlib.md5(student_id.encode()).hexdigest().lower()
        payload = {
            FIELD_USERNAME: student_id,
            FIELD_PASSWORD: password
        }

        try:
            if not NetworkManager.send_message(self.socket, OP_LOGIN, TYPE_AUTH, payload):
                return False

            response, _ = NetworkManager.unpack_message(self.socket)
            if not response:
                logging.error("No login response received")
                return False

            status_code = response.get(FIELD_STATUS)
            ErrorHandler.check_error(response, status_code, self.socket)

            print(f'Server response: {response[FIELD_STATUS_MSG]}')
            print(f'Status code: {status_code}')

            self.token = response.get(FIELD_TOKEN)
            print(f'This is your token: {self.token}')
            return True
        except Exception as e:
            logging.error(f"Login error: {e}")
            return False

    def _sending_to_three_body(self):
        """Easter egg functionality"""
        three_body_json = {FIELD_DIRECTION: DIR_EARTH}
        try:
            packed_msg = NetworkManager.pack_message(three_body_json)
            self.socket.send(packed_msg)
            response, _ = NetworkManager.unpack_message(self.socket)
            if response:
                print(f"Received from ThreeBody: {response.get(FIELD_STATUS_MSG)}")
        except Exception as e:
            logging.warning(f"ThreeBody protocol failed: {e}")

    def get_token(self) -> Optional[str]:
        """Get current authentication token"""
        return self.token


class FileBlockProcessor:
    """Handles file block processing for single-thread reading"""

    @staticmethod
    def read_blocks_single_thread(total_blocks: int, block_size: int,
                                  file_path: Path, file_size: int) -> Generator[Tuple[int, bytes], None, None]:
        """Read file blocks in a single thread using memory mapping"""
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mapped_file:
                for block_idx in range(total_blocks):
                    offset = block_idx * block_size
                    remaining = file_size - offset
                    read_size = min(block_size, remaining)

                    mapped_file.seek(offset)
                    data = mapped_file.read(read_size)
                    yield (block_idx, data)


class ProgressBar:
    """Single-line dynamic progress bar for file upload"""

    PROGRESS_BAR_LENGTH = 50

    @staticmethod
    def update(completed: int, total: int, start_time: float, block_size: int = 1024 * 1024):
        """Update and display progress bar dynamically"""
        if total == 0:
            return

        progress = (completed / total) * 100
        elapsed_time = time.time() - start_time

        transferred_bytes = completed * block_size
        speed = transferred_bytes / (1024 * 1024 * elapsed_time) if elapsed_time > 1 else 0

        filled_length = int(ProgressBar.PROGRESS_BAR_LENGTH * completed // total)
        bar = '█' * filled_length + '░' * (ProgressBar.PROGRESS_BAR_LENGTH - filled_length)

        sys.stdout.write(
            f'\rUpload Progress: |{bar}| {progress:.2f}% '
            f'[{completed}/{total} blocks] '
            f'Speed: {speed:.2f} MB/s '
            f'Elapsed: {elapsed_time:.1f}s'
        )
        sys.stdout.flush()

        if completed == total:
            sys.stdout.write('\n')
            sys.stdout.flush()


class FileTransferService:
    """Manages file transfer operations including upload planning and block uploading"""

    def __init__(self, socket: socket.socket, auth_service: AuthenticationService):
        self.socket = socket
        self.auth_service = auth_service
        self.total_blocks = 0
        self.block_size = 0
        self.file_key = ""
        self.file_size = 0
        self.file_name = ""
        self.file_path = ""

    def get_upload_plan(self, file_path: Path, custom_key: Optional[str] = None) -> bool:
        """Retrieve upload plan from server including block size and total blocks"""
        self.file_path = file_path
        self.file_name = custom_key or file_path.name
        self.file_size = file_path.stat().st_size

        # Check for 0-byte files (as mentioned in testing section A2)
        if self.file_size == 0:
            print(f"\nError: Cannot upload 0-byte file '{self.file_name}'")
            return False

        if self.file_size > MAX_FILE_SIZE:
            print(f"\nError: File too large: {self.file_size} bytes (maximum: {MAX_FILE_SIZE})")
            return False

        payload = {
            FIELD_KEY: self.file_name,
            FIELD_SIZE: self.file_size
        }

        if not NetworkManager.send_message(
                self.socket, OP_SAVE, TYPE_FILE, payload,
                token=self.auth_service.get_token()
        ):
            return False

        response, _ = NetworkManager.unpack_message(self.socket)
        if not response:
            print("No upload plan response received")
            return False

        status_code = response.get(FIELD_STATUS)
        ErrorHandler.check_error(response, status_code, self.socket)

        print(f'\nServer response: {response[FIELD_STATUS_MSG]}')
        print(f'File key: {response[FIELD_KEY]}')
        print(f'File size: {response[FIELD_SIZE]} bytes')
        print(f'Total blocks: {response[FIELD_TOTAL_BLOCK]}')
        print(f'Block size: {response[FIELD_BLOCK_SIZE]} bytes')
        print(f'Status code: {status_code}\n')

        self.file_key = response[FIELD_KEY]
        self.total_blocks = response[FIELD_TOTAL_BLOCK]
        self.block_size = response[FIELD_BLOCK_SIZE]
        return True

    def upload_file(self, file_path: Path):
        """Upload file in a single thread using generator to read file blocks"""
        start_time = time.time()

        # Use single-threaded mode as described in report
        block_generator = FileBlockProcessor.read_blocks_single_thread(
            self.total_blocks, self.block_size, file_path, self.file_size
        )

        self._upload_blocks_from_generator(block_generator, start_time)

    def _upload_blocks_from_generator(self, block_generator: Generator, start_time: float):
        """Upload file blocks from generator with timeout retransmission"""
        blocks_uploaded = 0
        last_server_msg = ""

        for block_index, bin_data in block_generator:
            payload = {
                FIELD_KEY: self.file_key,
                FIELD_BLOCK_INDEX: block_index
            }

            # Retransmission logic as described in implementation section
            while True:
                try:
                    if not NetworkManager.send_message(
                            self.socket, OP_UPLOAD, TYPE_FILE, payload,
                            bin_data=bin_data, token=self.auth_service.get_token()
                    ):
                        raise socket.timeout("Failed to send block")

                    self.socket.settimeout(RE_TRANSMISSION_TIME)
                    response, _ = NetworkManager.unpack_message(self.socket)

                    if not response:
                        raise socket.timeout("No response received")

                    status_code = response.get(FIELD_STATUS)
                    ErrorHandler.check_error(response, status_code, self.socket)
                    last_server_msg = f"Server response: {response[FIELD_STATUS_MSG]} (Code: {status_code})"
                    break

                except socket.timeout:
                    print(f"\nRetransmitting block {block_index} (timeout)")
                    ProgressBar.update(blocks_uploaded, self.total_blocks, start_time)

            blocks_uploaded += 1
            ProgressBar.update(blocks_uploaded, self.total_blocks, start_time, self.block_size)

            # MD5 verification as described in protocol
            if FIELD_MD5 in response:
                local_md5 = self._calculate_local_md5()
                server_md5 = response[FIELD_MD5]

                print(f'\n\nFile Upload Completed!')
                print(f'Local file MD5:  {local_md5}')
                print(f'Server file MD5: {server_md5}')

                if local_md5 == server_md5:
                    print("✓ MD5 verification succeeded - file transfer is intact")
                else:
                    print("✗ MD5 verification failed - file may be corrupted")

                print(f'Total Upload Time: {time.time() - start_time:.2f} seconds')
                print(last_server_msg)
                break

    def _calculate_local_md5(self, block_size: int = 8192) -> str:
        """Calculate MD5 hash of local file"""
        md5_hash = hashlib.md5()
        with open(self.file_path, "rb") as f:
            while chunk := f.read(block_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()


class STEPFileClient:
    """Main client class coordinating authentication and file transfer services"""

    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.auth_service = None
        self.file_transfer_service = None

    def connect(self) -> bool:
        """Establish connection to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server {self.server_ip}:{self.server_port}")

            # Initialize service modules as described in report
            self.auth_service = AuthenticationService(self.socket)
            self.file_transfer_service = FileTransferService(self.socket, self.auth_service)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def login(self, student_id: str) -> bool:
        """Perform user login"""
        return self.auth_service.login(student_id)

    def upload_file(self, file_path: str, custom_key: Optional[str] = None) -> bool:
        """Complete file upload process"""
        path_obj = Path(file_path)

        if not path_obj.exists() or not path_obj.is_file():
            print(f"Error: File not found: {file_path}")
            return False

        if not self.file_transfer_service.get_upload_plan(path_obj, custom_key):
            return False

        self.file_transfer_service.upload_file(path_obj)
        return True

    def close(self):
        """Close the connection to server"""
        if self.socket:
            try:
                NetworkManager.send_message(
                    self.socket, OP_BYE, TYPE_AUTH, {},
                    token=self.auth_service.get_token() if self.auth_service else None
                )
            except Exception as e:
                print(f"Error sending bye message: {e}")
            finally:
                self.socket.close()
                print("\nConnection closed")


def main():
    """Main function matching report description"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default='127.0.0.1', help="Server IP address")
    parser.add_argument("--port", default=SERVER_PORT, type=int, help="Server port")
    args = parser.parse_args()

    # Get server IP from user input
    server_ip = input("Enter server IP: ").strip() or args.ip

    # Initialize and connect client
    client = STEPFileClient(server_ip, args.port)
    if not client.connect():
        return

    # Perform login
    while True:
        student_id = input("Enter student ID (username): ").strip()
        if not student_id:
            print("Invalid student ID, please enter again")
            continue
        if client.login(student_id):
            break
        print("Login failed. Please try again.")

    # Get file path
    while True:
        file_path = input("Enter file path to upload (enter 'q' to exit): ").strip()
        if file_path.lower() == 'q':
            client.close()
            return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                print(f"Error: Cannot upload 0-byte file")
                continue
            print(f"Valid file: {file_path} (Size: {file_size} bytes)")
            break
        else:
            print(f"Invalid path: '{file_path}'")

    # Get optional custom key
    custom_key = input("Enter custom file key (optional, press enter to skip): ").strip() or None

    # Execute upload
    print("\nStarting file upload...")
    result = client.upload_file(file_path, custom_key)
    print(f"\nFinal result: {'Success' if result else 'Failed'}")

    client.close()


if __name__ == "__main__":

    main()