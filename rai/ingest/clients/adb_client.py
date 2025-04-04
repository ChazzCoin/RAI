import subprocess
from collections import defaultdict
from datetime import datetime
from typing import List

from pydantic import BaseModel

from rai.agentic.ai_modules.log import mLog
from rai.agentic.ai_modules.threads import MainLoop
from rai.internal.authority import fVault


class SMSMessage(BaseModel):
    address: str
    body: str
    date: datetime
    type: str  # "inbox" or "sent"
    contact_name: str = None

class AndroidADBClient(mLog, MainLoop):

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
    def _adb(self, command: List[str]) -> str:
        result = subprocess.run([self.adb_path] + command, capture_output=True, text=True)
        if result.returncode != 0:
            return self.log_error(f"ADB command failed: {result.stderr.strip()}")
        return result.stdout.strip()
    def list_devices(self) -> List[str]:
        output = self._run_command(['devices'])
        lines = output.split('\n')[1:]  # Skip header line
        self.log(f"ADB listing devices: {output}")
        return [line.split('\t')[0] for line in lines if '\tdevice' in line]

    def connect_device(self, host, port) -> str:
        self.log(f"Connecting to device: {host}:{port}")
        return self._run_command(['connect', f"{host}:{port}"])

    def pair_device(self, host: str, port: str, code: str) -> str:
        self.log(f"Pairing with device at {host}:{port} using code: {code}")
        try:
            process = subprocess.Popen(
                [self.adb_path, 'pair', f'{host}:{port}'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=code + '\n', timeout=10)

            if process.returncode != 0:
                return self.log_error(f"ADB pair failed: {stderr.strip()}")

            self.log(f"Pair result: {stdout.strip()}")
            return stdout.strip()

        except subprocess.TimeoutExpired:
            process.kill()
            return self.log_error("ADB pair command timed out.")

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

    def get_text_messages(self) -> List[SMSMessage]:
        raw_output = self._run_command(["shell", "content", "query", "--uri", "content://sms"])
        messages = []

        for block in raw_output.split("Row"):
            if not block.strip():
                continue

            msg_data = {}
            for item in block.strip().split(", "):
                if '=' in item:
                    key, val = item.split('=', 1)
                    # Replace NULL with empty string
                    val = None if val == 'NULL' else val
                    msg_data[key.strip()] = val.strip() if isinstance(val, str) else val

            try:
                # Parse timestamp safely
                timestamp = int(msg_data.get("date", 0))
                date_obj = datetime.fromtimestamp(timestamp / 1000) if timestamp else None

                # Determine message type
                type_code = msg_data.get("type", "0")
                msg_type = "inbox" if type_code == "1" else "sent"

                # Construct the SMS message
                msg = SMSMessage(
                    address=msg_data.get("address") or "Unknown",
                    body=msg_data.get("body") or "",
                    date=date_obj,
                    type=msg_type
                )
                messages.append(msg)
            except Exception as e:
                self.log_error(f"Failed to parse SMS row due to: {e}")

        # Sort messages chronologically
        messages.sort(key=lambda m: m.date)
        return messages

    def get_text_messages_sorted(self) -> dict[str, List[SMSMessage]]:
        raw_output = self._run_command(["shell", "content", "query", "--uri", "content://sms"])
        threads = defaultdict(list)

        for block in raw_output.split("Row"):
            if not block.strip():
                continue

            msg_data = {}
            for item in block.strip().split(", "):
                if '=' in item:
                    key, val = item.split('=', 1)
                    val = None if val == 'NULL' else val
                    msg_data[key.strip()] = val.strip() if isinstance(val, str) else val

            try:
                # Extract phone number and timestamp
                phone_number = str(msg_data.get("address")).replace("+", "") or "Unknown"
                if phone_number.startswith("1"): phone_number = phone_number[1:]
                timestamp = int(msg_data.get("date", 0))
                date_obj = datetime.fromtimestamp(timestamp / 1000) if timestamp else None

                # Determine inbox/sent
                type_code = msg_data.get("type", "0")
                msg_type = "inbox" if type_code == "1" else "sent"

                msg = SMSMessage(
                    address=phone_number if msg_type == "inbox" else "Me",
                    body=msg_data.get("body") or "",
                    date=date_obj,
                    type=msg_type,
                    contact_name=""
                )

                # Add to thread keyed by phone number
                threads[phone_number].append(msg)

            except Exception as e:
                self.log_error(f"Failed to parse SMS row due to: {e}")

        # Sort each thread by date
        for msg_list in threads.values():
            msg_list.sort(key=lambda m: m.date, reverse=True)
        # sorted_threads = dict(
        #     sorted(
        #         dict(threads).items(),
        #         key=lambda item: item[0].date if type(item) in [list, tuple] else datetime.min,
        #         reverse=True
        #     )
        # )
        return dict(threads)
    def get_text_messages_with_contacts(self) -> List[SMSMessage]:
        raw_output = self._run_command(["shell", "content", "query", "--uri", "content://sms"])
        messages = []

        for block in raw_output.split("Row"):
            if not block.strip():
                continue

            msg_data = {}
            for item in block.strip().split(", "):
                if '=' in item:
                    key, val = item.split('=', 1)
                    val = None if val == 'NULL' else val
                    msg_data[key.strip()] = val.strip() if isinstance(val, str) else val

            try:
                phone_number = msg_data.get("address") or "Unknown"

                # Lookup contact name
                contact_name = self.lookup_contact_name(phone_number)

                # Parse timestamp
                timestamp = int(msg_data.get("date", 0))
                date_obj = datetime.fromtimestamp(timestamp / 1000) if timestamp else None

                # Determine message type
                type_code = msg_data.get("type", "0")
                msg_type = "inbox" if type_code == "1" else "sent"

                msg = SMSMessage(
                    address=phone_number if msg_type == "inbox" else "Me",
                    body=msg_data.get("body") or "",
                    date=date_obj,
                    type=msg_type,
                    contact_name=contact_name
                )
                messages.append(msg)
            except Exception as e:
                self.log_error(f"Failed to parse SMS row due to: {e}")

        messages.sort(key=lambda m: m.date)
        return messages

    def lookup_contact_name(self, phone_number: str) -> str:
        if not phone_number or phone_number.lower() == "unknown":
            return "unknown"

        # Sanitize and quote the number
        sanitized = phone_number.replace("'", "")
        query = f"number='{sanitized}'"

        output = self._run_command([
            "shell", "content", "query",
            "--uri", "content://contacts/phones",
            "--where", query
        ])

        # Try to extract display_name
        for line in output.split(", "):
            if line.startswith("display_name="):
                name = line.split("=", 1)[1]
                return name.strip() if name != "NULL" else "unknown"

        return "unknown"

    def send_text_message(self, phone_number: str, message: str) -> str:
        self.log(f"Sending SMS to {phone_number} using low-level isms service")

        # Format the command
        command = [
            "shell",
            f"am start -a android.intent.action.SENDTO -d sms:{phone_number}",
            "–es sms_body",
            message
        ]

        result = self._run_command(command)

        # Check for common success marker
        if "Parcel" in result:
            self.log("Message send command issued successfully.")
            return "Message send command issued successfully."
        else:
            return self.log_error(f"Failed to send SMS via isms: {result}")


if __name__ == '__main__':
    client = AndroidADBClient()
    # client.pair_device("192.168.1.179", "36227", "658202")
    client.connect_device("192.168.1.179", "32777")
    messages = client.send_text_message("+12052155742", "I am chazzs agent. He wanted me to tell you something very important.... you. suck.")
    print(messages)
    # result = client._run_command(['shell', 'service', 'list'])
    # print(result)
