#!/bin/bash
# KaiTian Startup Script - Bash version
# Start KaiTian, MediaCrawler, and Postiz from source code
#
# Usage:
#   ./start.sh                    # Start all services
#   ./start.sh kaitian            # Start only KaiTian
#   ./start.sh kaitian mediacrawler  # Start specific services
#   ./start.sh --install-deps     # Install all dependencies
#   ./start.sh --clone-deps       # Clone repositories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$(dirname "$SCRIPT_DIR")}"
LOGS_DIR="$SCRIPT_DIR/logs"
PIDS_FILE="$LOGS_DIR/.pids"

# Service URLs
MEDIACRAWLER_URL="https://github.com/NanmiCoder/MediaCrawler.git"
POSTIZ_URL="https://github.com/gitroomhq/postiz-app.git"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Functions
log_info() {
	echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
	echo -e "${GREEN}✓${NC} $1"
}

log_error() {
	echo -e "${RED}✗${NC} $1"
}

log_warning() {
	echo -e "${YELLOW}⚠${NC} $1"
}

log_section() {
	echo ""
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo -e "${BLUE}$1${NC}"
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo ""
}

print_usage() {
	cat <<EOF
KaiTian Service Startup Manager

Usage:
  ./start.sh [OPTIONS] [SERVICES]

Options:
  --install-deps    Install all dependencies
  --clone-deps      Clone required repositories
  --help           Show this help message

Services (default: all):
  kaitian          KaiTian API Service (port 8000)
  mediacrawler     MediaCrawler Service (port 8888)
  postiz           Postiz Application (port 3000)

Examples:
  ./start.sh                           # Start all services
  ./start.sh kaitian                   # Start only KaiTian
  ./start.sh kaitian postiz            # Start specific services
  ./start.sh --install-deps            # Install dependencies
  ./start.sh --clone-deps              # Clone repositories

EOF
}

check_command() {
	if ! command -v "$1" &>/dev/null; then
		log_error "$1 not found. Please install it first."
		return 1
	fi
}

clone_repo() {
	local service=$1
	local url=$2
	local path="$BASE_DIR/$service"

	if [ -d "$path" ]; then
		log_success "$service already exists at $path"
		return 0
	fi

	log_info "Cloning $service from $url..."
	if git clone "$url" "$path"; then
		log_success "$service cloned successfully"
		return 0
	else
		log_error "Failed to clone $service"
		return 1
	fi
}

install_kaitian_deps() {
	log_info "Installing KaiTian dependencies..."
	cd "$SCRIPT_DIR"

	if python -m pip install -q -r requirements.txt; then
		log_success "KaiTian dependencies installed"
		return 0
	else
		log_error "Failed to install KaiTian dependencies"
		return 1
	fi
}

install_mediacrawler_deps() {
	local path="$BASE_DIR/MediaCrawler"

	if [ ! -d "$path" ]; then
		log_error "MediaCrawler directory not found at $path"
		return 1
	fi

	log_info "Installing MediaCrawler dependencies..."
	cd "$path"

	if python -m pip install -q -e .; then
		log_success "MediaCrawler dependencies installed"
		return 0
	else
		log_error "Failed to install MediaCrawler dependencies"
		return 1
	fi
}

install_postiz_deps() {
	local path="$BASE_DIR/postiz-app"

	if [ ! -d "$path" ]; then
		log_error "Postiz directory not found at $path"
		return 1
	fi

	log_info "Installing Postiz dependencies..."
	cd "$path"

	if npm install -q; then
		log_success "Postiz dependencies installed"
		return 0
	else
		log_error "Failed to install Postiz dependencies"
		return 1
	fi
}

start_kaitian() {
	local log_file="$LOGS_DIR/kaitian.log"
	local port=8000

	if [ -z "$KAITIAN_RUNNING" ]; then
		log_info "Starting KaiTian (port $port)..."
		cd "$SCRIPT_DIR"

		python main.py >"$log_file" 2>&1 &
		local pid=$!
		echo $pid >>"$PIDS_FILE"

		log_success "KaiTian started (PID: $pid)"
		log_info "Log: tail -f $log_file"
		log_info "API: http://localhost:$port/api/v1"
		log_info "Docs: http://localhost:$port/docs"

		KAITIAN_RUNNING=true
	else
		log_warning "KaiTian is already running"
	fi
}

start_mediacrawler() {
	local path="$BASE_DIR/MediaCrawler"
	local log_file="$LOGS_DIR/mediacrawler.log"
	local port=8888

	if [ ! -d "$path" ]; then
		log_error "MediaCrawler directory not found at $path"
		return 1
	fi

	if [ -z "$MEDIACRAWLER_RUNNING" ]; then
		log_info "Starting MediaCrawler (port $port)..."
		cd "$path"

		python -m media_crawler.main >"$log_file" 2>&1 &
		local pid=$!
		echo $pid >>"$PIDS_FILE"

		log_success "MediaCrawler started (PID: $pid)"
		log_info "Log: tail -f $log_file"
		log_info "API: http://localhost:$port"

		MEDIACRAWLER_RUNNING=true
	else
		log_warning "MediaCrawler is already running"
	fi
}

start_postiz() {
	local path="$BASE_DIR/postiz-app"
	local log_file="$LOGS_DIR/postiz.log"
	local port=3000

	if [ ! -d "$path" ]; then
		log_error "Postiz directory not found at $path"
		return 1
	fi

	if [ -z "$POSTIZ_RUNNING" ]; then
		log_info "Starting Postiz (port $port)..."
		cd "$path"

		export NODE_ENV=development
		export PORT=$port
		npm run dev >"$log_file" 2>&1 &
		local pid=$!
		echo $pid >>"$PIDS_FILE"

		log_success "Postiz started (PID: $pid)"
		log_info "Log: tail -f $log_file"
		log_info "App: http://localhost:$port"

		POSTIZ_RUNNING=true
	else
		log_warning "Postiz is already running"
	fi
}

cleanup() {
	log_section "Shutting down services..."

	if [ -f "$PIDS_FILE" ]; then
		while read -r pid; do
			if kill -0 "$pid" 2>/dev/null; then
				log_info "Stopping process $pid..."
				kill "$pid" 2>/dev/null || true
				sleep 1
				kill -9 "$pid" 2>/dev/null || true
			fi
		done <"$PIDS_FILE"
		rm -f "$PIDS_FILE"
	fi

	log_success "All services stopped"
}

print_status() {
	log_section "Service Status"

	local kaitian_pid=$(pgrep -f "python main.py" | head -1)
	local mediacrawler_pid=$(pgrep -f "media_crawler" | head -1)
	local postiz_pid=$(pgrep -f "npm run dev" | head -1)

	echo -e "KaiTian:"
	if [ -n "$kaitian_pid" ]; then
		echo -e "  ${GREEN}✓ Running${NC} (PID: $kaitian_pid)"
		echo -e "  API: http://localhost:8000/api/v1"
		echo -e "  Docs: http://localhost:8000/docs"
	else
		echo -e "  ${RED}✗ Not running${NC}"
	fi

	echo ""
	echo -e "MediaCrawler:"
	if [ -n "$mediacrawler_pid" ]; then
		echo -e "  ${GREEN}✓ Running${NC} (PID: $mediacrawler_pid)"
		echo -e "  API: http://localhost:8888"
	else
		echo -e "  ${RED}✗ Not running${NC}"
	fi

	echo ""
	echo -e "Postiz:"
	if [ -n "$postiz_pid" ]; then
		echo -e "  ${GREEN}✓ Running${NC} (PID: $postiz_pid)"
		echo -e "  App: http://localhost:3000"
	else
		echo -e "  ${RED}✗ Not running${NC}"
	fi
}

# Trap signals for cleanup
trap cleanup EXIT INT TERM

# Parse arguments
if [ $# -eq 0 ]; then
	SERVICES=("kaitian" "mediacrawler" "postiz")
else
	case "$1" in
	--help)
		print_usage
		exit 0
		;;
	--install-deps)
		log_section "Installing dependencies..."
		check_command python || exit 1
		check_command npm || exit 1

		install_kaitian_deps || exit 1
		install_mediacrawler_deps || exit 1
		install_postiz_deps || exit 1

		log_success "All dependencies installed"
		exit 0
		;;
	--clone-deps)
		log_section "Cloning repositories..."
		check_command git || exit 1

		clone_repo "MediaCrawler" "$MEDIACRAWLER_URL" || exit 1
		clone_repo "postiz-app" "$POSTIZ_URL" || exit 1

		log_success "Repositories cloned"
		exit 0
		;;
	*)
		SERVICES=("$@")
		;;
	esac
fi

# Main execution
log_section "🎯 KaiTian Service Startup Manager"

# Check required commands
check_command python || exit 1

# For postiz, check npm
if [[ " ${SERVICES[@]} " =~ " postiz " ]]; then
	check_command npm || exit 1
fi

# Clone and install
log_section "📥 Cloning repositories..."
if [[ " ${SERVICES[@]} " =~ " mediacrawler " ]]; then
	clone_repo "MediaCrawler" "$MEDIACRAWLER_URL" || log_warning "MediaCrawler clone failed"
fi
if [[ " ${SERVICES[@]} " =~ " postiz " ]]; then
	clone_repo "postiz-app" "$POSTIZ_URL" || log_warning "Postiz clone failed"
fi

log_section "📦 Installing dependencies..."
if [[ " ${SERVICES[@]} " =~ " kaitian " ]]; then
	install_kaitian_deps || log_warning "KaiTian dependency install failed"
fi
if [[ " ${SERVICES[@]} " =~ " mediacrawler " ]]; then
	install_mediacrawler_deps || log_warning "MediaCrawler dependency install failed"
fi
if [[ " ${SERVICES[@]} " =~ " postiz " ]]; then
	install_postiz_deps || log_warning "Postiz dependency install failed"
fi

log_section "🚀 Starting services..."
for service in "${SERVICES[@]}"; do
	case "$service" in
	kaitian)
		start_kaitian
		;;
	mediacrawler)
		start_mediacrawler
		;;
	postiz)
		start_postiz
		;;
	*)
		log_error "Unknown service: $service"
		;;
	esac
	sleep 2
done

# Print status
print_status

log_section "✓ Services startup complete!"
echo ""
echo "💡 Tips:"
echo "  - View logs: tail -f logs/{service}.log"
echo "  - KaiTian API docs: http://localhost:8000/docs"
echo "  - Press Ctrl+C to stop all services"
echo ""

# Keep running
while true; do
	sleep 1
done
