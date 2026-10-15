import os
import sys
import paramiko

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

vps_host = os.environ.get("VPS_HOST", "31.97.180.176")
vps_user = os.environ.get("VPS_USER", "root")
vps_password = os.environ.get("VPS_SSH_PASSWORD", "")

if not vps_password:
    print("VPS_SSH_PASSWORD environment variable not set. Exiting.")
    sys.exit(0)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=10)

def run(cmd):
    print(">>> CMD:", cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err:
        print("ERR:", err)

run("journalctl -u ai-story-backend.service -n 35 --no-pager")

ssh.close()
