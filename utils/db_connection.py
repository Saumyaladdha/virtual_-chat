"""
Shared database infrastructure — SSH tunnel + MySQL connection.
All db_utils modules import from here.
"""
import logging
import socket
import subprocess
import time
from datetime import datetime, timezone, timedelta

import pymysql
import pymysql.cursors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

SSH_HOST = "13.205.33.122"
SSH_USER = "ubuntu"
SSH_KEY  = "/Users/saumyaladdha/.ssh/id_rsa"

RDS_HOST = "arivihannonprodrds.csammatrzuwu.ap-south-1.rds.amazonaws.com"
RDS_PORT = 3306

DB_CONFIG = {
    "user":            "saumyaladdha",
    "password":        "BgweuWCGhR2nH3lP",
    "database":        "arivihan_stage",
    "charset":         "utf8mb4",
    "connect_timeout": 10,
}


def _log(msg: str) -> None:
    logger.info(msg)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_connection():
    """Opens SSH tunnel to RDS and returns a pymysql connection."""
    local_port = _free_port()
    _log(f"🔌 Opening SSH tunnel → ubuntu@{SSH_HOST}  (local :{local_port} → RDS:3306) ...")

    proc = subprocess.Popen(
        [
            "ssh", "-N",
            "-L", f"{local_port}:{RDS_HOST}:{RDS_PORT}",
            "-i", SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            f"{SSH_USER}@{SSH_HOST}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                break
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError(f"SSH tunnel process exited early (rc={proc.returncode})")
            time.sleep(0.3)
    else:
        proc.kill()
        raise RuntimeError("SSH tunnel did not become ready within 10 seconds")

    _log(f"✅ SSH tunnel open  (local :{local_port} → RDS:3306)")
    _log("🔌 Connecting to arivihan_stage via tunnel ...")

    conn = pymysql.connect(
        host="127.0.0.1",
        port=local_port,
        cursorclass=pymysql.cursors.DictCursor,
        **DB_CONFIG,
    )
    _log("✅ Connected to arivihan_stage")
    conn._ssh_proc = proc
    return conn


def close_connection(conn) -> None:
    """Closes DB connection and SSH tunnel."""
    if conn:
        proc = getattr(conn, "_ssh_proc", None)
        conn.close()
        _log("🔌 DB connection closed")
        if proc:
            proc.kill()
            proc.wait()
            _log("🔌 SSH tunnel closed")


def epoch_ms_to_ist(epoch_ms: int) -> datetime:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=IST)


def format_time_hinglish(hour: int, minute: int = 0) -> str:
    if hour <= 11:
        prefix = "Subah"
    elif hour <= 15:
        prefix = "Dopahar"
    elif hour <= 18:
        prefix = "Shaam"
    else:
        prefix = "Raat"
    display_h = hour if hour <= 12 else hour - 12
    if minute == 0:
        return f"{prefix} {display_h} baje"
    return f"{prefix} {display_h}:{minute:02d} baje"
