#!/usr/bin/env python3
"""
KaiTian Startup Script - Manage KaiTian, MediaCrawler, and Postiz services

This script helps you quickly start all services from source code with proper
configuration and dependency management.

Usage:
    python start.py                    # Start all services
    python start.py --help             # Show help
    python start.py --only kaitian     # Start only KaiTian
    python start.py --clone-deps       # Clone missing dependencies
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
        self.venv_path = self.base_dir / "venv"

    def _get_venv_python(self) -> str:
        """Get the path to Python in the virtual environment."""
        if os.name == "nt":  # Windows
            return str(self.venv_path / "Scripts" / "python.exe")
        else:  # Linux/macOS
            return str(self.venv_path / "bin" / "python")

    def _init_services_config(self):
        """Initialize service configurations."""
        # Service configurations
        self.services_config = {
            "kaitian": {
                "path": self.base_dir / ".",
                "name": "KaiTian",
                "description": "KaiTian API Service",
                "port": 8000,
                "cmd": [self._get_venv_python(), "main.py"],
                "env": self._get_kaitian_env(),
                "startup_msg": "Application startup complete",
            },
            "mediacrawler": {
                "path": self.base_dir / "../MediaCrawler",
                "name": "MediaCrawler",
                "description": "MediaCrawler Service",
                "port": 8888,
                "cmd": [self._get_venv_python(), "-m", "media_crawler.main"],
                "env": self._get_mediacrawler_env(),
                "startup_msg": "MediaCrawler started",
            },
            "postiz": {
                "path": self.base_dir / "../postiz-app",
                "name": "Postiz",
                "description": "Postiz Application",
                "port": 3000,
                "cmd": ["npm", "run", "dev"],
                "env": self._get_postiz_env(),
                "startup_msg": "ready in",
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

    def _get_postiz_env(self) -> dict:
        """Get environment variables for Postiz."""
        env = os.environ.copy()
        env.update(
            {
                "NODE_ENV": "development",
                "PORT": "3000",
            }
        )
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
            try:
                import media_crawler

                return True
            except ImportError:
                return False

        elif service == "postiz":
            # Check if node_modules exists
            postiz_path = config["path"]
            return (postiz_path / "node_modules").exists()

        return False

    def clone_repository(self, service: str) -> bool:
        """Clone repository if it doesn't exist."""
        config = self.services_config.get(service)
        if not config:
            return False

        service_path = config["path"]
        if service_path.exists():
            print(f"✓ {config['name']} already exists at {service_path}")
            return True

        print(f"\n📥 Cloning {config['name']}...")

        urls = {
            "mediacrawler": "https://github.com/NanmiCoder/MediaCrawler.git",
            "postiz": "https://github.com/gitroomhq/postiz-app.git",
        }

        if service not in urls:
            print(f"✗ Cannot clone {service} - no repository URL configured")
            return False

        try:
            cmd = ["git", "clone", urls[service], str(service_path)]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ {config['name']} cloned successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to clone {config['name']}: {e}")
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
            if service == "kaitian":
                # Install Python dependencies using venv Python
                venv_python = self._get_venv_python()
                cmd = [venv_python, "-m", "pip", "install", "-r", "requirements.txt"]
                subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)
                print(f"✓ {config['name']} dependencies installed")
                return True

            elif service == "mediacrawler":
                # Install MediaCrawler dependencies using venv Python
                venv_python = self._get_venv_python()
                cmd = [venv_python, "-m", "pip", "install", "-e", "."]
                subprocess.run(cmd, cwd=service_path, check=True, capture_output=True)
                print(f"✓ {config['name']} dependencies installed")
                return True

            elif service == "postiz":
                # Install Node.js dependencies
                cmd = ["npm", "install"]
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
                return True

        except Exception as e:
            print(f"✗ Failed to start {config['name']}: {e}")
            return False

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
            services = ["kaitian", "mediacrawler", "postiz"]

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
                "api": "http://localhost:8888",
            },
            "postiz": {
                "app": "http://localhost:3000",
            },
        }

        for service, links in endpoints.items():
            if service in self.processes:
                print(f"\n{service.upper()}:")
                for key, url in links.items():
                    print(f"  {key}: {url}")

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
        # Setup virtual environment first
        if not self.setup_venv():
            print("\n✗ Failed to setup virtual environment")
            sys.exit(1)

        # Initialize service configurations after venv path is determined
        self._init_services_config()

        # Handle specific commands
        if args.clone_deps:
            self.clone_repository("mediacrawler")
            self.clone_repository("postiz")
            return

        if args.install_deps:
            for service in ["kaitian", "mediacrawler", "postiz"]:
                self.install_dependencies(service)
            return

        # Start services
        services = args.only.split(",") if args.only else None
        if not self.start_all_services(services):
            print("\n✗ Failed to start services")
            sys.exit(1)

        # Print information
        self.print_status()
        self.print_endpoints()

        print("\n" + "=" * 60)
        print("✓ All services started successfully!")
        print("=" * 60)
        print("\n💡 Tips:")
        print("  - View logs: tail -f logs/{service}.log")
        print("  - KaiTian API docs: http://localhost:8000/docs")
        print("  - Press Ctrl+C to stop all services\n")

        # Keep running and handle shutdown
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for service, info in list(self.processes.items()):
                    process = info["process"]
                    if process.poll() is not None:
                        print(f"\n⚠ {service} process died (exit code: {process.returncode})")

        except KeyboardInterrupt:
            print("\n\n✋ Interrupt received")
            self.cleanup()
            sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="KaiTian Service Startup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                    # Start all services
  python start.py --only kaitian     # Start only KaiTian
  python start.py --clone-deps       # Clone missing repositories
  python start.py --install-deps     # Install dependencies
  python start.py --only kaitian,mediacrawler  # Start specific services
        """,
    )

    parser.add_argument(
        "--only",
        help="Comma-separated list of services to start (kaitian, mediacrawler, postiz)",
        type=str,
    )
    parser.add_argument(
        "--clone-deps",
        action="store_true",
        help="Clone required repositories",
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
