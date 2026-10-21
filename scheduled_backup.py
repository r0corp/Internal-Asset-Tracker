"""
Backup otomatis terjadwal - supaya backup tetap jalan tiap hari
walau tidak ada admin yang sempat klik tombol "Create New Backup"
secara manual di menu Backup Database.

Backup lama (lebih tua dari RETENTION_DAYS hari) otomatis dihapus,
supaya folder backups/ tidak membengkak terus tanpa batas.

Cara pasang di server (PowerShell, sebagai Administrator - sesuaikan
path-nya dengan lokasi instalasi sebenarnya):

    schtasks /create /tn "AssetTracker Backup Harian" /sc daily /st 23:30 /ru SYSTEM /tr "'C:\\AssetTracker\\venv\\Scripts\\python.exe' 'C:\\AssetTracker\\scheduled_backup.py'"

Cek hasilnya lewat log aplikasi (instance/logs/app.log) kalau backup
gagal, atau lewat menu Backup Database di web untuk lihat daftar
backup yang berhasil dibuat.
"""

import os
from datetime import datetime, timedelta

from app import create_app
from app.blueprints.backup import create_backup_zip, get_backup_folder


RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))


def delete_old_backups(folder, retention_days):
    """
    Menghapus file .zip di folder backup yang lebih tua dari
    retention_days hari. Mengembalikan daftar nama file yang dihapus.
    """

    cutoff = datetime.now() - timedelta(days=retention_days)

    deleted = []

    for filename in os.listdir(folder):

        if not filename.endswith(".zip"):
            continue

        file_path = os.path.join(folder, filename)

        modified_at = datetime.fromtimestamp(
            os.path.getmtime(file_path)
        )

        if modified_at < cutoff:

            try:
                os.remove(file_path)
                deleted.append(filename)
            except OSError:
                pass

    return deleted


def run():

    app = create_app()

    with app.app_context():

        try:
            zip_filename = create_backup_zip(prefix="scheduled")

        except Exception as exc:

            app.logger.error("Backup terjadwal gagal: %s", exc)
            print(f"GAGAL membuat backup: {exc}")

            raise SystemExit(1)

        print(f"Backup berhasil dibuat: {zip_filename}")

        deleted = delete_old_backups(
            get_backup_folder(),
            RETENTION_DAYS,
        )

        if deleted:
            print(
                f"Backup lama dihapus ({len(deleted)} file, "
                f">{RETENTION_DAYS} hari): {', '.join(deleted)}"
            )


if __name__ == "__main__":
    run()
