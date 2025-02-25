from abc import abstractmethod

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

COMMAND_AGENT_REGISTRY = {}


def register_command_config(name: str):
    def decorator(cls):
        COMMAND_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator


class IngestServerProvider:
    lock = threading.Lock()
    client = None

    @classmethod
    def get_registry(cls): return COMMAND_AGENT_REGISTRY
    @abstractmethod
    def hostname(self): pass
    @abstractmethod
    def host(self): pass
    @abstractmethod
    def username(self): pass
    @abstractmethod
    def password(self): pass
    @abstractmethod
    def port(self): pass
    @abstractmethod
    def commands(self): pass

    @classmethod
    def execute(cls, name, command):
        cmd_cls = COMMAND_AGENT_REGISTRY.get(name)[0]()
        cmd_cls.connect()
        cmd = cmd_cls.commands()[command]
        return cmd_cls.run(cmd)

    def connect(self):
        """Establishes an SSH connection to the server."""
        if self.client:
            return  # Already connected

        self.lock = threading.Lock()  # Ensures thread safety for SSH execution
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.client.connect(
                hostname=self.host(),
                port=self.port(),
                username=self.username(),
                password=self.password()
            )
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

        if error: return f"Error executing command '{command}': {error}"
        return output

    def close_connection(self):
        """Closes the SSH connection."""
        if self.client:
            self.client.close()
            self.client = None



@register_command_config("system")
class SystemProvider(IngestServerProvider):

    def hostname(self) -> str: return "Under The Bunk Server"
    def host(self) -> str: return "192.168.1.6"
    def port(self) -> int: return 22
    def username(self) -> str: return "underthebunk"
    def password(self) -> str: return "wonderwall"

    def commands(self) -> dict: return {
        "hostname": "hostname",
        "os_version": "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2",
        "uptime": "uptime -p",
        "cpu_info": "lscpu | grep 'Model name' | cut -d: -f2",
        "cpu_cores": "nproc",
        "memory": "free -h | grep Mem | awk '{print $2 \" total, \" $3 \" used, \" $4 \" free\"}'",
        "disk_usage": "df -h / | awk 'NR==2{print $2 \" total, \" $3 \" used, \" $4 \" free\"}'",
        "network_interfaces": "ip -o -4 addr show | awk '{print $2 \" - \" $4}'",
        "active_processes": "ps -eo comm | wc -l",
        "users": "who | awk '{print $1}' | sort | uniq",
        "daemons": "systemctl list-units --type=service --state=running | awk '{print $1}'",
    }

@register_command_config("docker")
class DockerProvider(IngestServerProvider):

    def hostname(self) -> str: return "Under The Bunk Server"
    def host(self) -> str: return "192.168.1.6"
    def port(self) -> int: return 22
    def username(self) -> str: return "underthebunk"
    def password(self) -> str: return "wonderwall"

    def commands(self) -> dict: return {
        "version": "docker --version",
        "images": "docker images --format '{{.Repository}}:{{.Tag}} ({{.ID}})'",
        "containers": "docker ps --format '{{.Names}} ({{.Image}}) - {{.Status}}'",
        "ps": "docker ps --format '{{.Names}} ({{.Image}}) - {{.Status}}'",
        "networks": "docker network ls --format '{{.Name}} ({{.ID}})'",
        "volumes": "docker volume ls --format '{{.Name}} ({{.Driver}})'",
        "info": "docker info",
    }
@register_command_config("network")
class NetworkProvider(IngestServerProvider):

    def hostname(self) -> str: return "Under The Bunk Server"
    def host(self) -> str: return "192.168.1.6"
    def port(self) -> int: return 22
    def username(self) -> str: return "underthebunk"
    def password(self) -> str: return "wonderwall"

    def commands(self) -> dict: return {
        "if_config": "ifconfig",
        "ip_address": "hostname -I | awk '{print $1}'",
        "network_interfaces": "ip -o -4 addr show | awk '{print $2 \" - \" $4}'",
        "default_gateway": "ip route | grep default | awk '{print $3}'",
        "dns_servers": "cat /etc/resolv.conf | grep 'nameserver' | awk '{print $2}'",
        "active_connections": "netstat -tulnp",
        "ping_google": "ping -c 4 8.8.8.8",
    }

# Example Usage:
if __name__ == "__main__":
    data = IngestServerProvider.execute('system', 'daemons')
    print(data)
