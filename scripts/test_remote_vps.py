import paramiko
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("31.97.180.176", username="root", password="3,VUkqGrDeCT8D0G", timeout=10)

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
