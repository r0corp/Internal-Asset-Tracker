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
from ..models import (
    Asset,
    Category,
    Location,
    Department,
    Vendor,
    AuditLog,
    Role,
    ROLE_ADMINISTRATOR,
)


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
# RESTRIKSI KATEGORI PER ROLE (mis. role "Office Boy" yang cuma
# boleh lihat/kelola asset kategori tertentu, lihat Role.allowed_categories
# di models.py)
# ============================================================


def get_current_role():
    """
    Role object milik current_user, dicocokkan lewat nama (sama
    seperti requires_permission di auth.py) - None kalau user belum
    login atau nama role-nya tidak ketemu di tabel roles.
    """

    if not current_user.is_authenticated:
        return None

    return Role.query.filter_by(name=current_user.role).first()


def allowed_asset_categories():
    """
    None kalau current_user TIDAK dibatasi (administrator, atau
    role-nya tidak mengaktifkan restriksi kategori) - artinya boleh
    lihat semua kategori, filter tidak perlu diterapkan.

    Kalau dibatasi, mengembalikan list nama Category (bukan key
    field_template-nya) yang boleh diakses, untuk dipakai langsung
    di Asset.category.in_(...).
    """

    if (
        current_user.is_authenticated
        and current_user.role == ROLE_ADMINISTRATOR
    ):
        return None

    role = get_current_role()

    if not role or not role.restricts_categories():
        return None

    templates = role.allowed_category_templates()

    categories = (
        Category.query
        .filter(Category.field_template.in_(templates))
        .all()
    )

    return [c.name for c in categories]


def apply_asset_category_restriction(query):
    """
    Menerapkan filter Asset.category.in_(...) ke query SQLAlchemy
    kalau current_user dibatasi kategorinya - dipanggil di tiap
    tempat yang query Asset untuk listing/hitung jumlah.
    """

    allowed = allowed_asset_categories()

    if allowed is None:
        return query

    return query.filter(Asset.category.in_(allowed))


def generate_next_asset_tag(category):
    """
    Membuat Asset Tag otomatis format TCI-<code>-<tahun>-<urutan>
    (misal TCI-LP-2026-0001), berdasarkan Category.code. Urutan
    dihitung ulang tiap kategori+tahun dari tag tertinggi yang sudah
    ada (bukan counter terpisah), supaya tidak perlu tabel tambahan.

    Mengembalikan None kalau kategori tidak ditemukan atau belum
    punya code (berarti kategori ini belum ikut skema penomoran
    otomatis - asset_tag tetap harus diisi manual di form).
    """

    if not category or not category.code:
        return None

    year = datetime.now().year
    prefix = f"TCI-{category.code}-{year}-"

    existing_tags = (
        Asset.query
        .filter(Asset.asset_tag.like(f"{prefix}%"))
        .with_entities(Asset.asset_tag)
        .all()
    )

    max_sequence = 0

    for (tag,) in existing_tags:
        suffix = tag[len(prefix):]
        if suffix.isdigit():
            max_sequence = max(max_sequence, int(suffix))

    return f"{prefix}{max_sequence + 1:04d}"


def allowed_category_template_keys():
    """
    None kalau current_user tidak dibatasi (boleh lihat semua tab/
    filter kategori) - kalau dibatasi, mengembalikan list key
    field_template yang boleh diakses, untuk menyembunyikan tab
    filter dan opsi dropdown kategori yang tidak relevan ke role
    tersebut.
    """

    if (
        current_user.is_authenticated
        and current_user.role == ROLE_ADMINISTRATOR
    ):
        return None

    role = get_current_role()

    if not role or not role.restricts_categories():
        return None

    return role.allowed_category_templates()

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


