
from typing import Dict, Callable

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
