import subprocess
from typing import List

from rai.agentic.ai_modules import mLog
from rai.ingest.clients import fVault


class AndroidADBClient(mLog):

    adb_path = 'adb'

    vault: fVault = None
    name: str = None
    host: str = None
    port: int = None

    @classmethod
    def from_vault(cls, vault: fVault):
        self = cls()
        self.log("Starting ADB from Vault Model.")
        self.vault = vault
        self.name = vault.name
        self.host = vault.host
        self.port = vault.port
        return self

    def _run_command(self, command: List[str]) -> str:
        result = subprocess.run([self.adb_path] + command, capture_output=True, text=True)
        if result.returncode != 0:
            return self.log_error(f"ADB command failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def list_devices(self) -> List[str]:
        output = self._run_command(['devices'])
        lines = output.split('\n')[1:]  # Skip header line
        self.log(f"ADB listing devices: {output}")
        return [line.split('\t')[0] for line in lines if '\tdevice' in line]

    def connect_device(self) -> str:
        self.log(f"Connecting to device: {self.host}:{self.port}")
        return self._run_command(['connect', self.host])

    def disconnect_device(self) -> str:
        self.log(f"Disconnecting from device: {self.host}:{self.port}")
        command = ['disconnect']
        if self.host:
            command.append(self.host)
        return self._run_command(command)

    def shell_command(self, device_id: str, shell_cmd: str) -> str:
        self.log(f"Executing shell command: {shell_cmd}")
        return self._run_command(['-s', device_id, 'shell', shell_cmd])

    def install_app(self, device_id: str, apk_path: str) -> str:
        self.log(f"Installing app: {apk_path}")
        return self._run_command(['-s', device_id, 'install', apk_path])

    def uninstall_app(self, device_id: str, package_name: str) -> str:
        self.log(f"Uninstalling app: {package_name}")
        return self._run_command(['-s', device_id, 'uninstall', package_name])
