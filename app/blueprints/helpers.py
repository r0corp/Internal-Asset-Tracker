"""
Kumpulan helper function yang dipakai lintas domain
(asset, movement) - dipisah supaya tidak
ada duplikasi logic antar blueprint.
"""

import os
import re
import uuid

from datetime import datetime, date

from flask import current_app, url_for
from flask_babel import gettext as _
from werkzeug.utils import secure_filename

import qrcode

from flask_login import current_user

from .. import db
from ..models import Category, Location, Department, Vendor, AuditLog


def log_action(action, entity_type, entity_label=None, description=None):
    """
    Mencatat aktivitas user (tambah/ubah/hapus data) ke audit log.
    Dipanggil setelah db.session.commit() pada route yang mengubah data.
    """

    entry = AuditLog(
        user_id=(
            current_user.id
            if current_user.is_authenticated
            else None
        ),
        username=(
            current_user.username
            if current_user.is_authenticated
            else None
        ),
        action=action,
        entity_type=entity_type,
        entity_label=entity_label,
        description=description,
    )

    db.session.add(entry)
    db.session.commit()


def parse_date(value):
    """
    Mengubah nilai tanggal menjadi object datetime.date.

    Mendukung:
    - None
    - ""
    - datetime.date
    - datetime.datetime
    - format YYYY-MM-DD
    - format DD-MM-YYYY
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt
            ).date()
        except ValueError:
            continue

    return None

def get_master_data():
    """
    Mengambil seluruh data master
    untuk form asset.
    """

    categories = (
        Category.query
        .order_by(Category.name.asc())
        .all()
    )

    locations = (
        Location.query
        .order_by(Location.name.asc())
        .all()
    )

    departments = (
        Department.query
        .order_by(Department.name.asc())
        .all()
    )

    vendors = (
        Vendor.query
        .order_by(Vendor.name.asc())
        .all()
    )

    return (
        categories,
        locations,
        departments,
        vendors,
    )

# ============================================================
# HELPER FOTO ASSET
# ============================================================


ALLOWED_ASSET_PHOTO_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}


def allowed_asset_photo(filename):
    """
    Memastikan file foto asset menggunakan
    ekstensi yang diperbolehkan.
    """

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = (
        filename.rsplit(".", 1)[1]
        .lower()
        .strip()
    )

    return extension in ALLOWED_ASSET_PHOTO_EXTENSIONS


def get_asset_photo_folder():
    """
    Mengambil folder penyimpanan foto asset.
    """

    folder = os.path.join(
        current_app.static_folder,
        "uploads",
        "assets",
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    return folder


def delete_asset_photo(photo_filename):
    """
    Menghapus file foto asset jika ada.
    """

    if not photo_filename:
        return

    photo_folder = get_asset_photo_folder()

    photo_path = os.path.join(
        photo_folder,
        photo_filename,
    )

    if os.path.exists(photo_path):
        try:
            os.remove(photo_path)
        except OSError:
            pass


def save_asset_photo(photo_file, asset_tag):
    """
    Menyimpan foto asset dan mengembalikan
    nama file yang tersimpan.
    """

    if not photo_file:
        return None

    if not photo_file.filename:
        return None

    if not allowed_asset_photo(
        photo_file.filename
    ):
        raise ValueError(
            _("Photo format must be JPG, JPEG, PNG, or WEBP.")
        )

    original_filename = secure_filename(
        photo_file.filename
    )

    extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )

    safe_asset_tag = secure_filename(
        asset_tag
    )

    unique_suffix = uuid.uuid4().hex[:8]

    filename = (
        f"{safe_asset_tag}_{unique_suffix}.{extension}"
    )

    photo_folder = get_asset_photo_folder()

    photo_path = os.path.join(
        photo_folder,
        filename,
    )

    photo_file.save(
        photo_path
    )

    return filename


def generate_asset_qr(asset):
    """
    Membuat QR Code untuk asset.
    """

    qr_folder = os.path.join(
        current_app.static_folder,
        "qrcodes",
    )

    os.makedirs(
        qr_folder,
        exist_ok=True,
    )

    filename = f"{asset.asset_tag}.png"

    filepath = os.path.join(
        qr_folder,
        filename,
    )

    asset_url = url_for(
        "main.asset_detail",
        asset_id=asset.id,
        _external=True,
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(asset_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    image.save(filepath)

    return filename


# ============================================================
# DASHBOARD ASSET MANAGEMENT
# ============================================================


