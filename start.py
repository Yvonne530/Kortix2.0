#!/usr/bin/env python3

import subprocess
import sys
import platform
import os
import json
import io

# --- 尽量把本进程的终端编码切到 UTF-8（对控制台输出更友好，不影响子进程读取逻辑）---
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="ignore")
except Exception:
    pass

IS_WINDOWS = platform.system() == "Windows"
PROGRESS_FILE = ".setup_progress"


# --- ANSI Colors ---
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# --- 子进程调用封装（核心修复点） ---
def run_cmd(cmd, check=False, passthrough=False):
    """
    运行命令：
    - passthrough=True：不捕获输出，直接让子进程向控制台写（零解码，最稳）。
    - passthrough=False：捕获为 bytes，函数内用 UTF-8 + ignore 解码成 str 返回。
    """
    if passthrough:
        # 不捕获输出 -> Python 不会起 reader 线程，自然没有 GBK 解码问题
        cp = subprocess.run(
            cmd,
            shell=IS_WINDOWS,
            stdout=None,
            stderr=None,
            check=check,
        )
        return "", "", cp.returncode

    # 捕获 bytes，自行解码
    cp = subprocess.run(
        cmd,
        shell=IS_WINDOWS,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False if not check else True,
    )
    out = cp.stdout.decode("utf-8", errors="ignore") if cp.stdout else ""
    err = cp.stderr.decode("utf-8", errors="ignore") if cp.stderr else ""
    return out, err, cp.returncode


def load_progress():
    """Loads the last saved step and data from setup."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                return json.load(f)
        except Exception:
            return {"step": 0, "data": {}}
    return {"step": 0, "data": {}}


def get_setup_method():
    """Gets the setup method chosen during setup."""
    progress = load_progress() or {}
    data = progress.get("data") or {}
    return data.get("setup_method")


def check_docker_available():
    """Check if Docker is available and running."""
    try:
        # 这里不捕获输出，避免任何编码问题；只看返回码
        _, _, code = run_cmd(["docker", "version"], passthrough=False)
        if code == 0:
            return True
        print(f"{Colors.RED}❌ Docker seems unavailable (non-zero exit).{Colors.ENDC}")
        print(f"{Colors.YELLOW}Please start Docker and try again.{Colors.ENDC}")
        return False
    except FileNotFoundError:
        print(f"{Colors.RED}❌ Docker is not installed or not in PATH.{Colors.ENDC}")
        print(f"{Colors.YELLOW}Please install/start Docker and try again.{Colors.ENDC}")
        return False


def check_docker_compose_up():
    # 这里需要读取输出 -> 捕获为 bytes 自己解码
    out, _, _ = run_cmd(["docker", "compose", "ps", "-q"], passthrough=False)
    return len(out.strip()) > 0


def print_manual_instructions():
    """Prints instructions for manually starting Suna services."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}🚀 Manual Startup Instructions{Colors.ENDC}\n")

    print("To start Suna, you need to run these commands in separate terminals:\n")

    print(f"{Colors.BOLD}1. Start Infrastructure (in project root):{Colors.ENDC}")
    print(f"{Colors.CYAN}   docker compose up redis -d{Colors.ENDC}\n")

    print(f"{Colors.BOLD}2. Start Frontend (in a new terminal):{Colors.ENDC}")
    print(f"{Colors.CYAN}   cd frontend && npm run dev{Colors.ENDC}\n")

    print(f"{Colors.BOLD}3. Start Backend (in a new terminal):{Colors.ENDC}")
    print(f"{Colors.CYAN}   cd backend && uv run api.py{Colors.ENDC}\n")

    print(f"{Colors.BOLD}4. Start Background Worker (in a new terminal):{Colors.ENDC}")
    print(
        f"{Colors.CYAN}   cd backend && uv run dramatiq run_agent_background{Colors.ENDC}\n"
    )

    print("Once all services are running, access Suna at: http://localhost:3000\n")

    print(
        f"{Colors.YELLOW}💡 Tip:{Colors.ENDC} You can use '{Colors.CYAN}./start.py{Colors.ENDC}' to start/stop the infrastructure services."
    )


def main():
    setup_method = get_setup_method()

    if "--help" in sys.argv:
        print("Usage: ./start.py [OPTION]")
        print("Manage Suna services based on your setup method")
        print("\nOptions:")
        print("  -f\tForce start containers without confirmation")
        print("  --help\tShow this help message")
        return

    # If setup hasn't been run or method is not determined, default to docker
    if not setup_method:
        print(
            f"{Colors.YELLOW}⚠️  Setup method not detected. Run './setup.py' first or using Docker Compose as default.{Colors.ENDC}"
        )
        setup_method = "docker"

    if setup_method == "manual":
        print(f"{Colors.BLUE}{Colors.BOLD}Manual Setup Detected{Colors.ENDC}")
        print("Managing infrastructure services (Redis)...\n")

        force = "-f" in sys.argv
        if force:
            print("Force awakened. Skipping confirmation.")

        out, _, _ = run_cmd(["docker", "compose", "ps", "-q", "redis"])
        is_up = len(out.strip()) > 0

        if is_up:
            action = "stop"
            msg = "🛑 Stop infrastructure services? [y/N] "
        else:
            action = "start"
            msg = "⚡ Start infrastructure services? [Y/n] "

        if not force:
            response = input(msg).strip().lower()
            if action == "stop":
                if response != "y":
                    print("Aborting.")
                    return
            else:
                if response == "n":
                    print("Aborting.")
                    return

        if action == "stop":
            # 不捕获输出，直接透传，避免任何编码问题
            run_cmd(["docker", "compose", "down"], passthrough=True)
            print(f"\n{Colors.GREEN}✅ Infrastructure services stopped.{Colors.ENDC}")
        else:
            run_cmd(["docker", "compose", "up", "redis", "-d"], passthrough=True)
            print(f"\n{Colors.GREEN}✅ Infrastructure services started.{Colors.ENDC}")
            print_manual_instructions()

    else:  # docker setup
        print(f"{Colors.BLUE}{Colors.BOLD}Docker Setup Detected{Colors.ENDC}")
        print("Managing all Suna services with Docker Compose...\n")

        force = "-f" in sys.argv
        if force:
            print("Force awakened. Skipping confirmation.")

        if not check_docker_available():
            return

        is_up = check_docker_compose_up()

        if is_up:
            action = "stop"
            msg = "🛑 Stop all Suna services? [y/N] "
        else:
            action = "start"
            msg = "⚡ Start all Suna services? [Y/n] "

        if not force:
            response = input(msg).strip().lower()
            if action == "stop":
                if response != "y":
                    print("Aborting.")
                    return
            else:
                if response == "n":
                    print("Aborting.")
                    return

        if action == "stop":
            run_cmd(["docker", "compose", "down"], passthrough=True)
            print(f"\n{Colors.GREEN}✅ All Suna services stopped.{Colors.ENDC}")
        else:
            run_cmd(["docker", "compose", "up", "-d"], passthrough=True)
            print(f"\n{Colors.GREEN}✅ All Suna services started.{Colors.ENDC}")
            print(f"{Colors.CYAN}🌐 Access Suna at: http://localhost:3000{Colors.ENDC}")


if __name__ == "__main__":
    main()
