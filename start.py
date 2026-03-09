#!/usr/bin/env python3
"""
KaiTian Startup Script - Manage KaiTian service

KaiTian is a standalone service providing web scraping and AI capabilities.
No external dependencies required - all crawling is done via Playwright.

Usage:
    python start.py                    # Start KaiTian service
    python start.py --help             # Show help
    python start.py start              # Start service
    python start.py stop               # Stop service
    python start.py status             # Show service status
"""

import os
import sys
import subprocess
import argparse
import time
import signal
import socket
from pathlib import Path
from typing import Optional
import json


class ServiceManager:
    """Manage KaiTian service using uv for dependency management."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).resolve()
        self.processes = {}
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)

    def _get_uv_path(self) -> str:
        return "uv"

    def _init_services_config(self):
        self.services_config = {
            "kaitian": {
                "path": self.base_dir / ".",
                "name": "KaiTian",
                "description": "KaiTian API Service - Web Scraping & AI Capabilities",
                "port": 8000,
                "cmd": [
                    self._get_uv_path(),
                    "run",
                    "uvicorn",
                    "main:app",
                    "--port",
                    "8000",
                    "--host",
                    "0.0.0.0",
                ],
                "env": self._get_kaitian_env(),
                "startup_msg": "Application startup complete",
                "health_endpoint": "/api/v1/health",
            },
            "mediacrawler": {
                "path": self.base_dir / "packages" / "MediaCrawler",
                "name": "MediaCrawler",
                "description": "MediaCrawler WebUI API - Social Media Crawler",
                "port": 8080,
                "cmd": [
                    self._get_uv_path(),
                    "run",
                    "uvicorn",
                    "api.main:app",
                    "--port",
                    "8080",
                    "--host",
                    "0.0.0.0",
                ],
                "env": os.environ.copy(),
                "startup_msg": "Application startup complete",
                "health_endpoint": "/api/health",
            },
        }

    def _get_kaitian_env(self) -> dict:
        """Get environment variables for KaiTian."""
        env = os.environ.copy()
        env.update(
            {
                "KAITIAN_DEBUG": "false",
                "KAITIAN_LOG_LEVEL": "INFO",
                "DATABASE_URL": "sqlite:///./kaitian.db",
            }
        )
        return env

    def check_dependencies(self, service: str) -> bool:
        config = self.services_config.get(service)
        if not config:
            return False

        try:
            result = subprocess.run(
                ["uv", "sync", "--dry-run"],
                cwd=config["path"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and "Would install" not in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def install_dependencies(self, service: str) -> bool:
        """Install dependencies for a service."""
        config = self.services_config.get(service)
        if not config:
            return False

        if self.check_dependencies(service):
            print(f"✓ {config['name']} dependencies already installed")
            return True

        print(f"\n📦 Installing {config['name']} dependencies...")
        service_path = config["path"]

        try:
            cmd = ["uv", "sync"]
            subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)
            print(f"✓ {config['name']} dependencies installed")

            cmd = ["uv", "run", "playwright", "install"]
            subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)
            print(f"✓ Playwright browsers installed")

            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {config['name']} dependencies: {e}")
            return False
        except FileNotFoundError as e:
            print(f"✗ Required tool not found for {config['name']}: {e}")
            return False

    def start_service(self, service: str) -> bool:
        """Start a single service."""
        config = self.services_config.get(service)
        if not config:
            print(f"✗ Unknown service: {service}")
            return False

        service_path = config["path"]
        if not service_path.exists():
            print(f"✗ {config['name']} path not found: {service_path}")
            return False

        log_file = self.log_dir / f"{service}.log"

        if self._is_port_in_use(config["port"]):
            if self.check_service_health(service):
                print(
                    f"⚠ {config['name']} already running on port {config['port']} "
                    "(reusing existing process)"
                )
                self.processes[service] = {
                    "process": None,
                    "config": config,
                    "log_file": log_file,
                    "port": config["port"],
                    "external": True,
                }
                return True

            print(
                f"✗ Port {config['port']} is already in use, but {config['name']} health check failed. "
                "Please free the port or stop the conflicting process first."
            )
            return False

        print(f"🚀 Starting {config['name']} on port {config['port']}...")
        print(f"   Command: {' '.join(config['cmd'])}")
        print(f"   Working directory: {service_path}")
        print(f"   Log file: {log_file}")

        try:
            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    config["cmd"],
                    cwd=service_path,
                    env=config["env"],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self.processes[service] = {
                    "process": process,
                    "config": config,
                    "log_file": log_file,
                    "port": config["port"],
                    "external": False,
                }
                print(f"✓ {config['name']} started (PID: {process.pid})")

            self._save_pids()
            return True

        except Exception as e:
            print(f"✗ Failed to start {config['name']}: {e}")
            return False

    def _save_pids(self):
        """Save PIDs of running services to file."""
        pid_file = self.log_dir / "services.pid"
        pids = {
            service: info["process"].pid
            for service, info in self.processes.items()
            if info.get("process") is not None
        }
        with open(pid_file, "w") as f:
            json.dump(pids, f)

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def wait_for_service(self, service: str, timeout: int = 30) -> bool:
        """Wait for service to be ready."""
        if service not in self.processes:
            return False

        config = self.services_config[service]
        startup_msg = config.get("startup_msg", "started")

        print(f"⏳ Waiting for {config['name']} to be ready...")

        log_file = self.processes[service]["log_file"]
        start_time = time.time()

        while time.time() - start_time < timeout:
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        content = f.read()
                        if startup_msg.lower() in content.lower():
                            print(f"✓ {config['name']} is ready")
                            return True
                except:
                    pass
            time.sleep(1)

        print(f"⚠ {config['name']} startup message not detected (continuing anyway)")
        return True

    def start_all_services(self, only: Optional[str] = None) -> bool:
        """Start services.

        Args:
            only: If specified, only start this service (kaitian or mediacrawler)
        """
        # Determine which services to start
        if only:
            if only not in self.services_config:
                print(f"✗ Unknown service: {only}")
                print(f"  Available services: {', '.join(self.services_config.keys())}")
                return False
            services = [only]
        else:
            services = list(self.services_config.keys())

        # Check if already running
        pid_file = self.log_dir / "services.pid"
        if pid_file.exists():
            try:
                with open(pid_file, "r") as f:
                    pids = json.load(f)

                running_services = []
                for service, pid in pids.items():
                    if service in services:
                        try:
                            os.kill(pid, 0)
                            running_services.append((service, pid))
                        except ProcessLookupError:
                            pass

                if running_services:
                    print("=" * 60)
                    print("⚠️  Services already running!")
                    print("=" * 60)
                    for service, pid in running_services:
                        print(f"  {service}: PID {pid}")
                    print("\nTo stop services, run: python start.py stop")
                    print("To check status, run: python start.py status")
                    return False
            except Exception:
                pass

        service_names = ", ".join([self.services_config[s]["name"] for s in services])
        print("=" * 60)
        print(f"🎯 Service Startup Manager - {service_names}")
        print("=" * 60)

        print("\n" + "=" * 60)
        print("📦 Checking and installing dependencies...")
        print("=" * 60)
        for service in services:
            self.install_dependencies(service)

        print("\n" + "=" * 60)
        print("🚀 Starting services...")
        print("=" * 60)
        for service in services:
            if not self.start_service(service):
                return False
            time.sleep(2)

        print("\n" + "=" * 60)
        print("⏳ Waiting for services to be ready...")
        print("=" * 60)
        for service in services:
            self.wait_for_service(service)

        return True

    def print_status(self):
        """Print status of all running services."""
        print("\n" + "=" * 60)
        print("📊 Service Status")
        print("=" * 60)

        for service, info in self.processes.items():
            process = info["process"]
            config = info["config"]
            if process is None:
                status = "✓ Running (external)"
                pid = "external"
            else:
                status = "✓ Running" if process.poll() is None else "✗ Stopped"
                pid = process.pid
            print(f"\n{config['name']}:")
            print(f"  Status: {status}")
            print(f"  PID: {pid}")
            print(f"  Port: {info['port']}")
            print(f"  Log: {info['log_file']}")

    def print_endpoints(self):
        """Print service endpoints."""
        print("\n" + "=" * 60)
        print("🌐 Service Endpoints")
        print("=" * 60)

        endpoints = {
            "kaitian": {
                "api": "http://localhost:8000/api/v1",
                "docs": "http://localhost:8000/docs",
                "health": "http://localhost:8000/api/v1/health",
            },
            "mediacrawler": {
                "api": "http://localhost:8080",
                "docs": "http://localhost:8080/docs",
                "health": "http://localhost:8080/api/health",
            },
        }

        for service, links in endpoints.items():
            if service in self.processes:
                print(f"\n{service.upper()}:")
                for key, url in links.items():
                    print(f"  {key}: {url}")

        print("\nKaiTian 使用说明:")
        print("  - API 文档: http://localhost:8000/docs")
        print("  - 健康检查: GET /api/v1/health")

        print("\nMediaCrawler:")
        print("  - WebUI: http://localhost:8080")
        print("  - API: http://localhost:8080/docs")

    def cleanup(self):
        """Clean up resources."""
        print("\n" + "=" * 60)
        print("🛑 Shutting down services...")
        print("=" * 60)

        for service, info in list(self.processes.items()):
            process = info["process"]
            config = info["config"]

            if process is None:
                print(f"Skipping external {config['name']} (managed by another process)")
                continue

            if process.poll() is None:
                print(f"Stopping {config['name']} (PID: {process.pid})...")
                process.terminate()

                try:
                    process.wait(timeout=5)
                    print(f"✓ {config['name']} stopped")
                except subprocess.TimeoutExpired:
                    print(f"⚠ Force killing {config['name']}")
                    process.kill()

    def run(self, args: argparse.Namespace):
        self._init_services_config()

        if args.command == "stop":
            self.stop_services()
            return

        if args.command == "status":
            self.show_status()
            return

        if args.install_deps:
            self.install_dependencies("kaitian")
            return

        only_service = getattr(args, "only", None)
        if not self.start_all_services(only=only_service):
            print("\n✗ Failed to start services")
            sys.exit(1)

        self.print_status()
        self.print_endpoints()

        started = only_service if only_service else "all services"
        print("\n" + "=" * 60)
        print(f"✓ {started} started successfully!")
        print("=" * 60)
        print("\n💡 Tips:")
        print("  - View logs: tail -f logs/<service>.log")
        print("  - API docs: http://localhost:8000/docs (KaiTian)")
        print("  - MediaCrawler: http://localhost:8080")
        print("  - Stop service: python start.py stop")
        print("  - Press Ctrl+C to stop\n")

        try:
            while True:
                time.sleep(1)
                for service, info in list(self.processes.items()):
                    process = info["process"]
                    if process is None:
                        continue
                    if process.poll() is not None:
                        print(f"\n⚠ {service} process died (exit code: {process.returncode})")

        except KeyboardInterrupt:
            print("\n\n✋ Interrupt received")
            self.cleanup()
            sys.exit(0)

    def stop_services(self):
        """Stop all running services with proper cleanup."""
        print("=" * 60)
        print("🛑 Stopping services...")
        print("=" * 60)

        pid_file = self.log_dir / "services.pid"
        if not pid_file.exists():
            print("No running services found (no PID file)")
            return

        try:
            with open(pid_file, "r") as f:
                pids = json.load(f)

            for service, pid in pids.items():
                try:
                    os.kill(pid, 0)
                    print(f"Stopping {service} (PID: {pid})...")
                    os.kill(pid, signal.SIGTERM)

                    try:
                        for _ in range(10):
                            time.sleep(0.5)
                            os.kill(pid, 0)
                    except ProcessLookupError:
                        print(f"✓ {service} stopped gracefully")
                        continue

                    print(f"⚠ {service} did not stop gracefully, force killing...")
                    os.kill(pid, signal.SIGKILL)
                    print(f"✓ {service} force stopped")

                except ProcessLookupError:
                    print(f"⚠ {service} (PID: {pid}) not running")
                except PermissionError:
                    print(f"✗ Permission denied to stop {service} (PID: {pid})")
                except Exception as e:
                    print(f"✗ Failed to stop {service}: {e}")

            if pid_file.exists():
                pid_file.unlink()
            print("\n✓ All services stopped")

        except Exception as e:
            print(f"✗ Error stopping services: {e}")

    def check_service_health(self, service: str) -> bool:
        """Check if service is responding to health requests."""
        config = self.services_config.get(service)
        if not config:
            return False

        try:
            import requests

            url = f"http://localhost:{config['port']}{config.get('health_endpoint', '/health')}"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except ImportError:
            return False
        except Exception:
            return False

    def show_status(self):
        """Show status of all services with health checks."""
        self._init_services_config()
        print("=" * 60)
        print("📊 Service Status")
        print("=" * 60)

        pid_file = self.log_dir / "services.pid"
        if not pid_file.exists() or pid_file.stat().st_size == 0:
            print("  No running services found\n")
            print("Available services:")
            for name, config in self.services_config.items():
                print(f"  - {name}: port {config['port']}")
            return

        try:
            with open(pid_file, "r") as f:
                pids = json.load(f)

            if not pids:
                print("  No running services found")
                return

            for service, pid in pids.items():
                config = self.services_config.get(service, {})
                port = config.get("port", "?")

                try:
                    os.kill(pid, 0)
                    is_healthy = self.check_service_health(service)
                    health_str = "✓ Healthy" if is_healthy else "⚠ Starting"
                    print(f"  {service}:")
                    print(f"    Status: ✓ Running")
                    print(f"    PID: {pid}")
                    print(f"    Port: {port}")
                    print(f"    Health: {health_str}")
                except ProcessLookupError:
                    print(f"  {service}:")
                    print(f"    Status: ✗ Stopped (PID: {pid} not found)")
                    print(f"    Port: {port}")
                except PermissionError:
                    print(f"  {service}:")
                    print(f"    Status: ⚠ No permission (PID: {pid})")
                    print(f"    Port: {port}")
                except Exception as e:
                    print(f"  {service}:")
                    print(f"    Status: ? Unknown ({e})")
                    print(f"    Port: {port}")
        except json.JSONDecodeError:
            print("  Error: PID file corrupted")
        except Exception as e:
            print(f"  Error reading status: {e}")

        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="KaiTian Service Startup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python start.py                    # Start KaiTian service
    python start.py start              # Start service
    python start.py stop               # Stop service
    python start.py status             # Show service status
    python start.py --install-deps     # Install dependencies
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["start", "stop", "status"],
        default="start",
        help="Command to execute: start (default), stop, or status",
    )
    parser.add_argument(
        "--only",
        choices=["kaitian", "mediacrawler"],
        help="Start only specified service",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install all dependencies",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory for services",
    )

    args = parser.parse_args()
    manager = ServiceManager(args.base_dir)
    manager.run(args)


if __name__ == "__main__":
    main()
