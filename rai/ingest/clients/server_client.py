from typing import Optional

import paramiko
import threading

from rai.agentic.ai_modules import mLog
from rai.internal.authority import AUTHORITY

class cServer(mLog):
    lock = threading.Lock()
    client: Optional[paramiko.SSHClient] = None
    sftp_client: Optional[paramiko.SFTPClient] = None

    name = AUTHORITY.get_env("SERVER_NAME_MASTER", "raiko-master")
    host = AUTHORITY.get_env("SERVER_HOST_MASTER", "192.168.1.6")
    port = int(AUTHORITY.get_env("SERVER_PORT_MASTER", "22"))
    username = AUTHORITY.get_env("SERVER_USER_MASTER", "underthebunk")
    password = AUTHORITY.get_env("SERVER_PASS_MASTER", "wonderwall")

    def connect(self):
        """Establishes an SSH and SFTP connection to the server."""
        if self.client and self.is_connected():
            return  # Already connected

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            self.sftp_client = self.client.open_sftp()
            self.log("SSH and SFTP connection established.")

        except paramiko.AuthenticationException:
            self.log_error("Authentication failed, please verify credentials.")
            self.client = None
        except paramiko.SSHException as e:
            self.log_error(f"SSH connection error: {e}")
            self.client = None

    def close_connection(self):
        """Closes the SSH and SFTP connections."""
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None
            self.log("SFTP client disconnected.")

        if self.client:
            self.client.close()
            self.client = None
            self.log("SSH client disconnected.")

    def is_connected(self):
        """Checks if the SSH client is connected."""
        if not self.client:
            return False
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()

    """ EXECUTE COMMANDS """
    def run(self, command: str) -> str:
        """Executes a command on the remote server and returns the output."""
        if not self.is_connected():
            self.connect()

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                return f"Error executing command '{command}': {error}"
            return output
        except Exception as e:
            return f"Exception during command execution '{command}': {e}"

    """ SFTP SUPPORT """
    def list_directory(self, path: str = "."):
        """Lists the contents of a directory on the remote server."""
        if not self.is_connected():
            self.connect()

        try:
            files = self.sftp_client.listdir(path)
            self.log(f"Contents of '{path}': {files}")
            return files
        except Exception as e:
            self.log_error(f"Error listing directory '{path}': {e}")
            return []

    def get_current_directory(self):
        """Returns the current working directory on the remote server."""
        if not self.is_connected():
            self.connect()

        try:
            cwd = self.sftp_client.getcwd()
            self.log(f"Current directory: {cwd}")
            return cwd
        except Exception as e:
            self.log_error(f"Error getting current directory: {e}")
            return None

    def change_directory(self, path: str):
        """Changes the current working directory on the remote server."""
        if not self.is_connected():
            self.connect()

        try:
            self.sftp_client.chdir(path)
            self.log(f"Changed directory to '{path}'.")
            return True
        except Exception as e:
            self.log_error(f"Error changing directory to '{path}': {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Uploads a file to the server via SFTP."""
        if not self.is_connected():
            self.connect()

        try:
            self.sftp_client.put(local_path, remote_path)
            self.log(f"File '{local_path}' uploaded successfully to '{remote_path}'.")
            return True
        except Exception as e:
            self.log_error(f"Error uploading file: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Downloads a file from the server via SFTP."""
        if not self.is_connected():
            self.connect()

        try:
            self.sftp_client.get(remote_path, local_path)
            self.log(f"File '{remote_path}' downloaded successfully to '{local_path}'.")
            return True
        except Exception as e:
            self.log_error(f"Error downloading file: {e}")
            return False


if __name__ == "__main__":
    server = cServer()
    server.connect()
    print(server.list_directory(path="/home/"))