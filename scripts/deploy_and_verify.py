import os
import sys
import paramiko
from pathlib import Path

# Ensure stdout uses utf-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

VPS_HOST = "31.97.180.176"
VPS_USER = "root"
VPS_PASS = "3,VUkqGrDeCT8D0G"
REMOTE_BASE = "/opt/ai-story-harness"

LOCAL_BASE = Path(__file__).resolve().parent.parent

def get_ssh_client():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
    return ssh

def run_remote(ssh, cmd):
    print(f"\n[REMOTE CMD] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(f"[STDOUT]\n{out.strip()}")
    if err.strip():
        print(f"[STDERR]\n{err.strip()}")
    return stdout.channel.recv_exit_status(), out, err

def sync_directory(sftp, local_dir: Path, remote_dir: str):
    for item in local_dir.rglob("*"):
        if item.is_file():
            # Skip caches and git
            if "__pycache__" in item.parts or ".pytest_cache" in item.parts or ".git" in item.parts or item.suffix == ".pyc":
                continue
            
            rel_path = item.relative_to(local_dir)
            remote_path = f"{remote_dir}/{rel_path.as_posix()}"
            remote_parent = os.path.dirname(remote_path)
            
            # Ensure remote directory exists
            try:
                sftp.stat(remote_parent)
            except IOError:
                # Create parent recursively
                parts = remote_parent.split("/")
                current = ""
                for part in parts:
                    if not part:
                        continue
                    current += f"/{part}"
                    try:
                        sftp.stat(current)
                    except IOError:
                        sftp.mkdir(current)

            print(f"Uploading: {rel_path} -> {remote_path}")
            sftp.put(str(item), remote_path)

def main():
    print("Connecting to VPS...")
    ssh = get_ssh_client()
    sftp = ssh.open_sftp()
    print("Connected successfully!")

    # 1. Sync backend files
    print("\n--- Syncing backend files ---")
    sync_directory(sftp, LOCAL_BASE / "backend", f"{REMOTE_BASE}/backend")

    # 2. Sync cli files
    print("\n--- Syncing cli files ---")
    sync_directory(sftp, LOCAL_BASE / "cli", f"{REMOTE_BASE}/cli")

    # 3. Sync prompts
    print("\n--- Syncing prompts ---")
    sync_directory(sftp, LOCAL_BASE / "prompts", f"{REMOTE_BASE}/prompts")

    sftp.close()

    # 4. Check permissions and restart backend service
    print("\n--- Restarting backend service ---")
    run_remote(ssh, f"systemctl restart ai-story-backend.service")
    run_remote(ssh, f"systemctl is-active ai-story-backend.service")

    # 5. Run CLI diagnostics
    print("\n--- Running CLI Doctor ---")
    run_remote(ssh, f"cd {REMOTE_BASE} && ./venv/bin/python cli/harness.py doctor")

    # 6. Check AutoPilot status
    print("\n--- Checking AutoPilot Status ---")
    run_remote(ssh, f"cd {REMOTE_BASE} && ./venv/bin/python cli/harness.py autopilot --status")

    ssh.close()
    print("\nDeployment and sync completed successfully!")

if __name__ == "__main__":
    main()
