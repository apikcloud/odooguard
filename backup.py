# SPDX-License-Identifier: MIT
# Copyright 2025 apik (https://apik.cloud).
# OdooGuard

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ------------------
# CONFIG
# ------------------


@dataclass
class Config:
    db_name: str
    pg_host: str
    pg_port: int
    pg_user: str
    backup_dir: Path
    filestore_root: Path

    @classmethod
    def load(cls) -> "Config":
        db_name = os.getenv("DB_NAME")
        if not db_name:
            raise ValueError("Missing DB_NAME environment variable")

        return cls(
            db_name=db_name,
            pg_host=os.getenv("PGHOST", "postgres"),
            pg_port=int(os.getenv("PGPORT", "5432")),
            pg_user=os.getenv("PGUSER", "odoo"),
            backup_dir=Path("/backups"),
            filestore_root=Path(
                os.getenv("FILESTORE", "/var/lib/odoo/.local/share/Odoo/filestore/")
            ),
        )


# ------------------
# HELPERS
# ------------------


def get_backup_name(db_name: str) -> str:
    """
    Format decided: db_YYYYMMDD_HHMMSS
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{db_name}_{ts}"


def parse_backup_timestamp(filename: str) -> datetime | None:
    """
    Expected: <db>_<YYYYMMDD_HHMMSS>.zip
    Example: mydb_20250105_020000.zip
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) < 2:
        return None

    ts_str = "_".join(parts[-2:])
    try:
        return datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


# ------------------
# BACKUP STEPS
# ------------------


def run_pg_dump(work_dir: Path, config: Config) -> None:
    dump_path = work_dir / "dump.sql"

    cmd = [
        "pg_dump",
        "-h",
        config.pg_host,
        "-p",
        str(config.pg_port),
        "-U",
        config.pg_user,
        "-d",
        config.db_name,
        "-F",
        "p",
    ]

    logging.info(
        f"Running pg_dump: db='{config.db_name}' host={config.pg_host}:{config.pg_port}"
    )

    with dump_path.open("w") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

    if proc.returncode != 0:
        logging.error(f"pg_dump failed: {proc.stderr}")
        sys.exit(1)


def copy_filestore(work_dir: Path, config: Config) -> None:
    """
    Odoo filestore = /var/lib/odoo/filestore/<dbname>
    """
    src = Path(config.filestore_root) / config.db_name
    dst = work_dir / "filestore"

    if not src.exists():
        logging.error(f"Filestore missing: {src}")
        sys.exit(1)

    logging.info(f"Copying filestore {src} to {dst}")
    shutil.copytree(src, dst)


def create_zip(work_dir: Path, config: Config) -> Path:
    base_name = get_backup_name(config.db_name)
    dest_base = config.backup_dir / base_name

    config.backup_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"Creating ZIP: {dest_base}.zip")
    shutil.make_archive(str(dest_base), "zip", root_dir=work_dir)

    return dest_base.with_suffix(".zip")


# ------------------
# ROTATION
# ------------------


def rotate_backups(config: Config) -> None:
    """
    Retention:
      - daily:   last 7 days
      - weekly:  last 4 weeks
      - monthly: last 3 months
    """
    backup_dir = config.backup_dir
    db = config.db_name

    files = sorted([p for p in backup_dir.glob(f"{db}_*.zip")])

    if not files:
        return

    entries = []
    for f in files:
        ts = parse_backup_timestamp(f.name)
        if ts:
            entries.append((f, ts))
        else:
            logging.info(f"Skipping unparsable backup name {f.name}")

    if not entries:
        return

    now = datetime.now()
    keep = set()

    # --- Daily (7 days)
    daily_cutoff = now - timedelta(days=7)
    for f, ts in entries:
        if ts >= daily_cutoff:
            keep.add(f)

    # --- Weekly (4 weeks)
    weekly_cutoff = now - timedelta(weeks=4)
    weekly = {}
    for f, ts in entries:
        if weekly_cutoff <= ts < daily_cutoff:
            key = (ts.isocalendar().year, ts.isocalendar().week)
            if key not in weekly or ts > weekly[key][1]:
                weekly[key] = (f, ts)

    for f, _ in weekly.values():
        keep.add(f)

    # --- Monthly (3 months)
    monthly_cutoff = now - timedelta(days=90)
    monthly = {}
    for f, ts in entries:
        if monthly_cutoff <= ts < weekly_cutoff:
            key = (ts.year, ts.month)
            if key not in monthly or ts > monthly[key][1]:
                monthly[key] = (f, ts)

    for f, _ in monthly.values():
        keep.add(f)

    # --- Delete others
    for f, ts in entries:
        if f not in keep:
            logging.info(f"Deleting old backup {f.name}")
            try:
                f.unlink()
            except Exception as e:
                logging.warning(f"Cannot delete {f}: {e}")


# ------------------
# MAIN
# ------------------


def main() -> None:
    config = Config.load()

    logging.info(f"Starting backup for database: {config.db_name}")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)

        run_pg_dump(work_dir, config)
        copy_filestore(work_dir, config)
        archive = create_zip(work_dir, config)

        logging.info(f"Backup created: {archive}")

    rotate_backups(config)
    logging.info("Backup rotation done.")


if __name__ == "__main__":
    main()
