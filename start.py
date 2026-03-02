#!/usr/bin/env python3
"""
KaiTian Startup Script - Manage KaiTian and MediaCrawler services

This script manages services in a monorepo structure:
- KaiTian API (port 8000) - Main API service
- MediaCrawler (port 8080) - Social media crawler WebUI

Usage:
    python start.py                    # Start all services
    python start.py --help             # Show help
    python start.py start              # Start all services
    python start.py stop               # Stop all services
    python start.py status             # Show service status
    python start.py --only kaitian     # Start only KaiTian
    python start.py --install-deps     # Install all dependencies
"""

import os
import sys
import subprocess
import argparse
import time
import signal
from pathlib import Path
from typing import List, Optional
import json


class ServiceManager:
    """Manage startup of multiple services."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).resolve()
        self.services = []
        self.processes = {}
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.venv_path = self.base_dir / ".venv"

    def _get_venv_python(self) -> str:
        if os.name == "nt":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")

    def _get_uv_path(self) -> str:
        return "uv"

    def _init_services_config(self):
        self.services_config = {
            "kaitian": {
                "path": self.base_dir / ".",
                "name": "KaiTian",
                "description": "KaiTian API Service",
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
            },
            "mediacrawler": {
                "path": self.base_dir / "packages" / "MediaCrawler",
                "name": "MediaCrawler",
                "description": "MediaCrawler Service - 小红书、抖音、快手、B站、微博、贴吧、知乎爬虫",
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
                "env": self._get_mediacrawler_env(),
                "startup_msg": "Uvicorn running on",
            },
        }

    def setup_venv(self) -> bool:
        """Setup and activate virtual environment."""
        if self.venv_path.exists():
            print(f"✓ Virtual environment already exists at {self.venv_path}")
            return True

        print(f"📦 Creating virtual environment at {self.venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_path)], check=True, capture_output=True
            )
            print(f"✓ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create virtual environment: {e}")
            return False

    def _get_kaitian_env(self) -> dict:
        """Get environment variables for KaiTian."""
        env = os.environ.copy()
        env.update(
            {
                "KAITIAN_DEBUG": "false",
                "KAITIAN_LOG_LEVEL": "INFO",
                "DATABASE_URL": "sqlite:///./kaitian.db",
                "CRAWL4AI_API_URL": "http://localhost:8001",
            }
        )
        return env

    def _get_mediacrawler_env(self) -> dict:
        """Get environment variables for MediaCrawler."""
        env = os.environ.copy()
        # Add MediaCrawler specific environment variables if needed
        return env

    def check_dependencies(self, service: str) -> bool:
        """Check if service dependencies are installed."""
        config = self.services_config.get(service)
        if not config:
            return False

        if service == "kaitian":
            try:
                import fastapi
                import uvicorn
                import sqlalchemy

                return True
            except ImportError:
                return False

        elif service == "mediacrawler":
            service_path = config["path"]
            venv_path = service_path / ".venv"
            return venv_path.exists()

        return False

    def clone_repository(self, service: str) -> bool:
        """Clone repository if it doesn't exist - for submodule, use git submodule commands."""
        config = self.services_config.get(service)
        if not config:
            return False

        service_path = config["path"]
        if service_path.exists():
            print(f"✓ {config['name']} already exists at {service_path}")
            return True

        if service == "mediacrawler":
            print(f"\n📥 Initializing MediaCrawler submodule...")
            try:
                subprocess.run(
                    [
                        "git",
                        "submodule",
                        "update",
                        "--init",
                        "--recursive",
                        "packages/MediaCrawler",
                    ],
                    cwd=self.base_dir,
                    check=True,
                    capture_output=True,
                )
                print(f"✓ MediaCrawler submodule initialized")
                self._setup_mediacrawler_config(service_path)
                return True
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to initialize MediaCrawler submodule: {e}")
                return False

        return False

    def _setup_mediacrawler_config(self, service_path: Path):
        """Setup MediaCrawler configuration files."""
        try:
            # Copy .env.example to .env if it exists
            env_example = service_path / ".env.example"
            env_file = service_path / ".env"

            if env_example.exists() and not env_file.exists():
                import shutil

                shutil.copy(env_example, env_file)
                print(f"✓ MediaCrawler .env file created from example")

            # Copy config/base_config.py example if needed
            config_dir = service_path / "config"
            if config_dir.exists():
                print(f"✓ MediaCrawler config directory ready")
                print(f"   Please edit {config_dir}/base_config.py to configure crawler settings")

        except Exception as e:
            print(f"⚠ Failed to setup MediaCrawler config: {e}")

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
            if service == "kaitian":
                # Install Python dependencies using venv Python
                venv_python = self._get_venv_python()
                cmd = [venv_python, "-m", "pip", "install", "-r", "requirements.txt"]
                subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)
                print(f"✓ {config['name']} dependencies installed")
                return True

            elif service == "mediacrawler":
                # Install MediaCrawler dependencies using uv
                cmd = ["uv", "sync"]
                subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)

                # Install playwright browsers
                cmd = ["uv", "run", "playwright", "install"]
                subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)

                print(f"✓ {config['name']} dependencies installed")
                return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {config['name']} dependencies: {e}")
            return False
        except FileNotFoundError as e:
            print(f"✗ Required tool not found for {config['name']}: {e}")
            return False

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
        pids = {service: info["process"].pid for service, info in self.processes.items()}
        with open(pid_file, "w") as f:
            json.dump(pids, f)

    def wait_for_service(self, service: str, timeout: int = 30) -> bool:
        """Wait for service to be ready."""
        if service not in self.processes:
            return False

        config = self.services_config[service]
        port = config["port"]
        startup_msg = config.get("startup_msg", "started")

        print(f"⏳ Waiting for {config['name']} to be ready...")

        # Check log file for startup message
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

    def start_all_services(self, services: Optional[List[str]] = None) -> bool:
        """Start all or specified services."""
        if not services:
            services = ["kaitian", "mediacrawler"]

        print("=" * 60)
        print("🎯 KaiTian Service Startup Manager")
        print("=" * 60)

        # Check and clone repositories
        for service in services:
            if service != "kaitian":
                self.clone_repository(service)

        # Install dependencies
        print("\n" + "=" * 60)
        print("📦 Checking and installing dependencies...")
        print("=" * 60)
        for service in services:
            self.install_dependencies(service)

        # Start services
        print("\n" + "=" * 60)
        print("🚀 Starting services...")
        print("=" * 60)
        for service in services:
            if not self.start_service(service):
                return False
            # Brief pause between service starts
            time.sleep(2)

        # Wait for services to be ready
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
            status = "✓ Running" if process.poll() is None else "✗ Stopped"
            print(f"\n{config['name']}:")
            print(f"  Status: {status}")
            print(f"  PID: {process.pid}")
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
                "webui": "http://localhost:8080",
                "docs": "http://localhost:8080/docs",
            },
        }

        for service, links in endpoints.items():
            if service in self.processes:
                print(f"\n{service.upper()}:")
                for key, url in links.items():
                    print(f"  {key}: {url}")

        if "mediacrawler" in self.processes:
            print("\nMediaCrawler 使用说明:")
            print("  - 访问 WebUI: http://localhost:8080")
            print("  - 支持平台: 小红书、抖音、快手、B站、微博、贴吧、知乎")
            print("  - 配置文件: ./MediaCrawler/config/base_config.py")
            print("  - 使用命令: uv run main.py --platform xhs --lt qrcode --type search")

    def cleanup(self):
        """Clean up resources."""
        print("\n" + "=" * 60)
        print("🛑 Shutting down services...")
        print("=" * 60)

        for service, info in list(self.processes.items()):
            process = info["process"]
            config = info["config"]

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
        """Run the startup manager."""
        if not self.setup_venv():
            print("\n✗ Failed to setup virtual environment")
            sys.exit(1)

        self._init_services_config()

        if args.command == "stop":
            self.stop_services()
            return

        if args.command == "status":
            self.show_status()
            return

        if args.install_deps:
            for service in ["kaitian", "mediacrawler"]:
                self.install_dependencies(service)
            return

        services = args.only.split(",") if args.only else None
        if not self.start_all_services(services):
            print("\n✗ Failed to start services")
            sys.exit(1)

        self.print_status()
        self.print_endpoints()

        print("\n" + "=" * 60)
        print("✓ All services started successfully!")
        print("=" * 60)
        print("\n💡 Tips:")
        print("  - View logs: tail -f logs/{service}.log")
        print("  - KaiTian API docs: http://localhost:8000/docs")
        print("  - Stop services: python start.py stop")
        print("  - Press Ctrl+C to stop all services\n")

        try:
            while True:
                time.sleep(1)
                for service, info in list(self.processes.items()):
                    process = info["process"]
                    if process.poll() is not None:
                        print(f"\n⚠ {service} process died (exit code: {process.returncode})")

        except KeyboardInterrupt:
            print("\n\n✋ Interrupt received")
            self.cleanup()
            sys.exit(0)

    def stop_services(self):
        """Stop all running services."""
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
                    import signal as sig

                    os.kill(pid, sig.SIGTERM)
                    print(f"✓ Stopped {service} (PID: {pid})")
                except ProcessLookupError:
                    print(f"⚠ {service} (PID: {pid}) not running")
                except Exception as e:
                    print(f"✗ Failed to stop {service}: {e}")

            pid_file.unlink()
            print("\n✓ All services stopped")

        except Exception as e:
            print(f"✗ Error stopping services: {e}")

    def show_status(self):
        """Show status of all services."""
        print("=" * 60)
        print("📊 Service Status")
        print("=" * 60)

        pid_file = self.log_dir / "services.pid"
        if pid_file.exists():
            with open(pid_file, "r") as f:
                pids = json.load(f)

            for service, pid in pids.items():
                try:
                    import signal as sig

                    os.kill(pid, 0)
                    print(f"  {service}: ✓ Running (PID: {pid})")
                except ProcessLookupError:
                    print(f"  {service}: ✗ Stopped (PID: {pid} not found)")
                except Exception as e:
                    print(f"  {service}: ? Unknown ({e})")
        else:
            print("  No running services found")

        print()
        for service, config in self.services_config.items():
            service_path = config["path"]
            if service_path.exists():
                print(f"  {service}: installed at {service_path}")
            else:
                print(f"  {service}: not installed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="KaiTian Service Startup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python start.py                    # Start all services
    python start.py start              # Start all services
    python start.py stop               # Stop all services
    python start.py status             # Show service status
    python start.py --only kaitian     # Start only KaiTian
    python start.py --install-deps     # Install dependencies

Monorepo Structure:
    kaitian/                # Main API service
    packages/MediaCrawler/  # Social media crawler (submodule)
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
        help="Comma-separated list of services to start (kaitian, mediacrawler)",
        type=str,
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
