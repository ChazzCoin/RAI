import paramiko
import json
import threading
from typing import Dict, List, Optional, Callable

# Central registry to hold all commands
COMMAND_REGISTRY: Dict[str, Dict[str, str]] = {}


def register_command_group(group_name: str):
    def decorator(func: Callable[[], Dict[str, str]]):
        COMMAND_REGISTRY[group_name] = func()
        return func  # Returns the function unmodified

    return decorator


@register_command_group("system")
def ssh_loader_commands():
    return {
        "hostname": "hostname",
        "os_version": "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2",
        "uptime": "uptime -p",
        "cpu_info": "lscpu | grep 'Model name' | cut -d: -f2",
        "cpu_cores": "nproc",
        "memory": "free -h | grep Mem | awk '{print $2 \" total, \" $3 \" used, \" $4 \" free\"}'",
        "disk_usage": "df -h / | awk 'NR==2{print $2 \" total, \" $3 \" used, \" $4 \" free\"}'",
        "network_interfaces": "ip -o -4 addr show | awk '{print $2 \" - \" $4}'",
        "active_processes": "ps -eo comm | wc -l",
    }


# Registering Docker Commands
@register_command_group("docker")
def docker_commands():
    return {
        "docker_version": "docker --version",
        "docker_images": "docker images --format '{{.Repository}}:{{.Tag}} ({{.ID}})'",
        "docker_containers": "docker ps --format '{{.Names}} ({{.Image}}) - {{.Status}}'",
        "docker_networks": "docker network ls --format '{{.Name}} ({{.ID}})'",
        "docker_volumes": "docker volume ls --format '{{.Name}} ({{.Driver}})'",
        "docker_info": "docker info",
    }


# Registering Network Commands
@register_command_group("network")
def network_commands():
    return {
        "if_config": "ifconfig",
        "ip_address": "hostname -I | awk '{print $1}'",
        "network_interfaces": "ip -o -4 addr show | awk '{print $2 \" - \" $4}'",
        "default_gateway": "ip route | grep default | awk '{print $3}'",
        "dns_servers": "cat /etc/resolv.conf | grep 'nameserver' | awk '{print $2}'",
        "active_connections": "netstat -tulnp",
        "ping_google": "ping -c 4 8.8.8.8",
    }


ssh_host = "192.168.1.6"
ssh_username = "underthebunk"
ssh_password = "wonderwall"
ssh_port = 22

class SSHDataLoader:
    lock = threading.Lock()
    client = None

    @classmethod
    def get_registry(cls, name): return COMMAND_REGISTRY[name]

    @classmethod
    def execute(cls, name, command):
        self = cls()
        self.connect()

        if name == 'group':
            return self.run_group(command)
        if name == 'sudo': cmd = command
        else: cmd = self.get_registry(name)[command]
        return self.run(cmd)


    def connect(self):
        """Establishes an SSH connection to the server."""
        if self.client:
            return  # Already connected

        self.lock = threading.Lock()  # Ensures thread safety for SSH execution
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.client.connect(hostname=ssh_host, port=ssh_port, username=ssh_username, password=ssh_password)
        except paramiko.AuthenticationException:
            raise ValueError("Authentication failed, please verify credentials.")
        except paramiko.SSHException as e:
            raise ConnectionError(f"SSH connection error: {e}")

    def run(self, command: str) -> str:
        """
        Executes a command on the remote server and returns the output.

        :param command: The command to execute.
        :return: Command output as a string.
        """
        if not self.client:
            self.connect()

        stdin, stdout, stderr = self.client.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if error:
            raise RuntimeError(f"Error executing command '{command}': {error}")

        return output

    def run_group(self, name) -> Dict[str, str]:
        results = {}
        try:
            for key, cmd in self.get_registry(name).items():
                try:
                    results[key] = self.run(cmd)
                except Exception as e:
                    results[key] = f"Error: {str(e)}"
            return results
        except Exception as e:
            print(e)
            return None

    def get_server_info(self) -> Dict[str, str]:
        results = {}
        for key, cmd in self.get_registry('system').items():
            try:
                results[key] = self.run(cmd)
            except Exception as e:
                results[key] = f"Error: {str(e)}"
        return results

    def get_running_services(self) -> List[str]:
        command = "systemctl list-units --type=service --state=running | awk '{print $1}'"
        try:
            output = self.run(command)
            return output.split("\n") if output else []
        except Exception as e:
            return [f"Error retrieving services: {str(e)}"]

    def get_logged_in_users(self) -> List[str]:
        command = "who | awk '{print $1}' | sort | uniq"
        try:
            output = self.run(command)
            return output.split("\n") if output else []
        except Exception as e:
            return [f"Error retrieving users: {str(e)}"]

    def close_connection(self):
        """Closes the SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def fetch_all_data(self) -> str:
        with self.lock:  # Ensuring thread safety
            try:
                data = {
                    "server_info": self.get_server_info(),
                    "running_services": self.get_running_services(),
                    "logged_in_users": self.get_logged_in_users(),
                }
                return json.dumps(data, indent=4)
            finally:
                self.close_connection()  # Ensure the connection is closed after execution


# Example Usage:
if __name__ == "__main__":
    data = SSHDataLoader.execute('group', 'network')
    print(data)
