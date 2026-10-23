import secrets
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


# ============================================================
# USER (LOGIN & HAK AKSES)
# ============================================================

ROLE_ADMINISTRATOR = "administrator"
ROLE_ADMIN = "admin"
ROLE_USER = "user"

FIELD_TEMPLATE_PC_LAPTOP = "pc_laptop"
FIELD_TEMPLATE_PONSEL = "ponsel"
FIELD_TEMPLATE_SERVER = "server"
FIELD_TEMPLATE_NON_PC = "non_pc"
FIELD_TEMPLATE_ELEKTRONIK_INTERIOR = "elektronik_interior"
FIELD_TEMPLATE_ELEKTRONIK_EXTERIOR = "elektronik_exterior"
FIELD_TEMPLATE_KENDARAAN = "kendaraan"
FIELD_TEMPLATE_FURNITURE = "furniture"
FIELD_TEMPLATE_TOOLS_MEKANIK = "tools_mekanik"
FIELD_TEMPLATE_ATK = "atk"
FIELD_TEMPLATE_PANTRY = "pantry"
FIELD_TEMPLATE_TOOLS_PANTRY = "tools_pantry"
FIELD_TEMPLATE_SHOWCASE = "showcase"
FIELD_TEMPLATE_GUDANG_EVENT = "gudang_event"

FIELD_TEMPLATE_CHOICES = [
    FIELD_TEMPLATE_PC_LAPTOP,
    FIELD_TEMPLATE_PONSEL,
    FIELD_TEMPLATE_SERVER,
    FIELD_TEMPLATE_NON_PC,
    FIELD_TEMPLATE_ELEKTRONIK_INTERIOR,
    FIELD_TEMPLATE_ELEKTRONIK_EXTERIOR,
    FIELD_TEMPLATE_KENDARAAN,
    FIELD_TEMPLATE_FURNITURE,
    FIELD_TEMPLATE_TOOLS_MEKANIK,
    FIELD_TEMPLATE_ATK,
    FIELD_TEMPLATE_PANTRY,
    FIELD_TEMPLATE_TOOLS_PANTRY,
    FIELD_TEMPLATE_SHOWCASE,
    FIELD_TEMPLATE_GUDANG_EVENT,
]

# Template yang punya "Jumlah/Stok" + "Satuan" (barang consumable,
# bukan aset bertag unik dengan serial/brand/model) - dipakai
# Asset.is_incomplete() supaya kategori consumable tidak dianggap
# "belum lengkap" hanya karena tidak ada serial number/brand/model.
STOCK_FIELD_TEMPLATES = [
    FIELD_TEMPLATE_ATK,
    FIELD_TEMPLATE_PANTRY,
    FIELD_TEMPLATE_TOOLS_PANTRY,
    FIELD_TEMPLATE_SHOWCASE,
    FIELD_TEMPLATE_GUDANG_EVENT,
]

ROLE_CHOICES = [
    ROLE_ADMINISTRATOR,
    ROLE_ADMIN,
    ROLE_USER,
]


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    full_name = db.Column(
        db.String(100),
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default=ROLE_USER,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    last_seen = db.Column(
        db.DateTime,
        nullable=True,
    )

    security_stamp = db.Column(
        db.String(64),
        nullable=False,
        default=lambda: secrets.token_hex(32),
    )

    ONLINE_THRESHOLD_SECONDS = 120

    @property
    def is_online(self):

        if not self.last_seen:
            return False

        return (
            datetime.utcnow() - self.last_seen
        ).total_seconds() < self.ONLINE_THRESHOLD_SECONDS

    def rotate_security_stamp(self):
        """
        Mengganti "tanda tangan" sesi user dengan yang baru - membuat
        SEMUA sesi login yang sedang aktif untuk user ini (termasuk
        cookie yang mungkin sudah dicuri sebelumnya) langsung tidak
        valid lagi, bukan cuma menghapus cookie di browser yang
        sedang dipakai logout. Dipanggil saat logout - lihat
        blueprints/login.py dan pengecekannya di blueprints/__init__.py.
        """

        self.security_stamp = secrets.token_hex(32)

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password,
        )

    def __repr__(self):

        return f"<User {self.username} ({self.role})>"

# ============================================================
# MENU (NAVIGASI DINAMIS)
# ============================================================


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    label = db.Column(
        db.String(100),
        nullable=False,
    )

    icon = db.Column(
        db.String(50),
        nullable=True,
    )

    url = db.Column(
        db.String(255),
        nullable=True,
    )

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("menu_items.id"),
        nullable=True,
    )

    order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    # Comma-separated role list (administrator,admin,user).
    # Kosong/None berarti terlihat oleh semua role.
    roles = db.Column(
        db.String(100),
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    # Kalau True, item ini dirender sebagai garis pemisah di sidebar
    # (label/url/icon diabaikan) - bukan link yang bisa diklik.
    is_divider = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    children = db.relationship(
        "MenuItem",
        backref=db.backref(
            "parent",
            remote_side=[id],
        ),
        order_by="MenuItem.order, MenuItem.id",
        cascade="all, delete-orphan",
    )

    def allowed_roles(self):

        if not self.roles:
            return []

        return [
            r.strip()
            for r in self.roles.split(",")
            if r.strip()
        ]

    def is_visible_to(self, role):

        allowed = self.allowed_roles()

        return (
            not allowed
            or role in allowed
        )

    def __repr__(self):

        return f"<MenuItem {self.label}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Menentukan section field apa yang muncul di form Add/Edit
    # Asset saat kategori ini dipilih (lihat FIELD_TEMPLATE_CHOICES).
    field_template = db.Column(
        db.String(20),
        nullable=False,
        server_default=FIELD_TEMPLATE_PC_LAPTOP,
    )

    # Singkatan kategori (misal "LP" untuk Laptop, "HP" untuk Handphone)
    # dipakai sebagai bagian tengah format Asset Tag otomatis:
    # TCI-<code>-<tahun>-<urutan>, lihat generate_next_asset_tag()
    # di blueprints/assets.py.
    code = db.Column(
        db.String(10),
        nullable=True,
    )

    # Batas minimum stok (stock opname bulanan) - kalau Asset.stock_quantity
    # kategori ini turun sampai angka ini, dianggap perlu diajukan
    # pembelian ulang. None = tidak dipantau (bukan kategori stok).
    low_stock_threshold = db.Column(
        db.Integer,
        nullable=True,
    )

    # Nomor urut asli di form kertas stok opname (kolom "No."/"Kode
    # Barang" sumber, mis. A0004 -> 4) - dipakai supaya kolom "No."
    # di tabel Asset List tetap sama dengan kertas Sadam walaupun
    # tabelnya ditampilkan terurut abjad/dipaginasi. None = kategori
    # ini tidak berasal dari form tsb (urutan tabel pakai nomor baris
    # biasa).
    stock_sequence = db.Column(
        db.Integer,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True, nullable=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(150))
    address = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(
        db.Integer,
        primary_key=True,
        nullable=False
    )

    asset_tag = db.Column(
        db.String(30),
        nullable=False
    )

    asset_name = db.Column(
        db.String(100),
        nullable=False
    )

    photo = db.Column(
        db.String(255),
        nullable=True,
    )

    category = db.Column(
        db.String(50),
        index=True,
    )

    brand = db.Column(
        db.String(50)
    )

    model = db.Column(
        db.String(100)
    )

    serial_number = db.Column(
        db.String(100)
    )

    # Khusus kategori dengan field_template "kendaraan".
    plat_nomor = db.Column(
        db.String(20)
    )

    masa_pajak = db.Column(
        db.Date
    )

    asuransi = db.Column(
        db.String(100)
    )

    nomor_polis = db.Column(
        db.String(50)
    )

    masa_asuransi = db.Column(
        db.Date
    )

    warna = db.Column(
        db.String(30)
    )

    tahun_buat = db.Column(
        db.Integer
    )

    # Tanggal jatuh tempo uji KIR (uji kelayakan kendaraan bermotor) -
    # khusus kendaraan niaga/angkutan barang, tapi field ini dibuat
    # generik untuk semua kategori kendaraan (Mobil/Motor/Truck) biar
    # fleksibel - dikosongkan saja kalau memang tidak berlaku.
    masa_kir = db.Column(
        db.Date
    )

    # Khusus kategori dengan field_template "lengkap" (elektronik).
    office_email = db.Column(
        db.String(150)
    )

    personal_email = db.Column(
        db.String(150)
    )

    phone_number = db.Column(
        db.String(30)
    )

    # Khusus kategori dengan field_template "elektronik_interior"/"elektronik_exterior".
    specification = db.Column(
        db.String(150)
    )

    # Khusus kategori consumable (ATK/Pantry/Tools Pantry/Showcase/Gudang Event).
    stock_quantity = db.Column(
        db.Integer
    )

    unit = db.Column(
        db.String(20)
    )

    # Khusus kategori "showcase".
    selling_price = db.Column(
        db.Float
    )

    location = db.Column(
        db.String(100),
        index=True,
    )

    department = db.Column(
        db.String(100),
        index=True,
    )

    pic = db.Column(
        db.String(100)
    )

    purchase_date = db.Column(
        db.Date
    )

    purchase_price = db.Column(
        db.Float
    )

    status = db.Column(
        db.String(30),
        index=True,
    )

    description = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    vendor = db.Column(
        db.String(100),
        index=True,
    )

    movements = db.relationship(
        "AssetMovement",
        back_populates="asset",
        cascade="all, delete-orphan"
    )

    photos = db.relationship(
        "AssetPhoto",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="AssetPhoto.sort_order",
    )

    @property
    def cover_photo_filename(self):
        """
        Foto sampul: ambil dari asset_photos (is_cover, lalu urutan
        terlama) kalau ada, kalau belum punya data di sana fallback
        ke kolom `photo` lama (asset yang dibuat sebelum fitur multi
        foto ada).
        """

        for photo in self.photos:
            if photo.is_cover:
                return photo.filename

        if self.photos:
            return self.photos[0].filename

        return self.photo

    @property
    def is_incomplete(self):
        """
        True kalau data penting asset ini masih kosong - dipakai untuk
        badge "Data Belum Lengkap", BUKAN untuk mengisi data secara
        otomatis (data yang memang belum ada dari sumbernya sengaja
        dibiarkan kosong, bukan direka-reka).

        Kategori consumable (ATK/Pantry/dst, lihat STOCK_FIELD_TEMPLATES)
        tidak realistis punya serial/brand/model, jadi cuma dicek
        lokasi & departemennya saja.
        """

        category = (
            Category.query.filter_by(name=self.category).first()
            if self.category else None
        )

        field_template = (
            category.field_template if category else None
        )

        # ATK tidak melacak Departemen/PIC (lihat data-tpl-fields di
        # add.html/edit.html) - jadi kelengkapannya cuma dicek dari
        # lokasi, bukan lokasi+departemen seperti kategori stok lain.
        if field_template == FIELD_TEMPLATE_ATK:
            return not self.location

        missing_org = not (self.location and self.department)

        if field_template in STOCK_FIELD_TEMPLATES:
            return missing_org

        missing_identity = not (
            self.serial_number and self.brand and self.model
        )

        return missing_identity or missing_org


class AssetPhoto(db.Model):
    __tablename__ = "asset_photos"

    id = db.Column(
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    filename = db.Column(
        db.String(255),
        nullable=False,
    )

    is_cover = db.Column(
        db.Boolean,
        nullable=False,
        server_default=db.text("0"),
    )

    sort_order = db.Column(
        db.Integer,
        nullable=False,
        server_default=db.text("0"),
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    asset = db.relationship(
        "Asset",
        back_populates="photos",
    )

    def __repr__(self):
        return f"<AssetPhoto {self.asset_id} {self.filename}>"


class AssetMovementBatch(db.Model):
    """
    Satu "form serah-terima" - bisa mencakup beberapa asset sekaligus
    (mis. laptop + HP diserahkan ke satu orang di satu tanggal), dengan
    satu nomor dokumen dan satu pasang tanda tangan untuk semuanya.
    Field tujuan (to_*), alasan, catatan, dan tanda tangan disimpan di
    sini; masing-masing asset yang ikut dalam serah-terima ini jadi satu
    baris AssetMovement (lihat AssetMovement.batch_id) yang tetap
    menyimpan field-nya sendiri (nilainya sama untuk semua item satu
    batch) supaya halaman riwayat/laporan/koreksi yang sudah ada tidak
    perlu tahu soal batch sama sekali.
    """

    __tablename__ = "asset_movement_batches"

    id = db.Column(
        db.Integer,
        primary_key=True,
        nullable=False
    )

    movement_no = db.Column(
        db.String(30),
        unique=True,
        nullable=True
    )

    movement_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    to_location = db.Column(
        db.String(100)
    )

    to_department = db.Column(
        db.String(100)
    )

    to_pic = db.Column(
        db.String(100)
    )

    reason = db.Column(
        db.String(255)
    )

    notes = db.Column(
        db.Text
    )

    from_signer_name = db.Column(
        db.String(100),
        nullable=True
    )

    from_signer_position = db.Column(
        db.String(100),
        nullable=True
    )

    to_signer_name = db.Column(
        db.String(100),
        nullable=True
    )

    to_signer_position = db.Column(
        db.String(100),
        nullable=True
    )

    from_signature = db.Column(
        db.Text,
        nullable=True
    )

    to_signature = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime
    )

    items = db.relationship(
        "AssetMovement",
        back_populates="batch",
        cascade="all, delete-orphan"
    )


class AssetMovement(db.Model):
    __tablename__ = "asset_movements"

    id = db.Column(
        db.Integer,
        primary_key=True,
        nullable=False
    )

    batch_id = db.Column(
        db.Integer,
        db.ForeignKey("asset_movement_batches.id"),
        nullable=False,
        index=True,
    )

    movement_no = db.Column(
        db.String(30),
        nullable=True
    )

    from_signer_name = db.Column(
        db.String(100),
        nullable=True
    )

    from_signer_position = db.Column(
        db.String(100),
        nullable=True
    )

    to_signer_name = db.Column(
        db.String(100),
        nullable=True
    )

    to_signer_position = db.Column(
        db.String(100),
        nullable=True
    )

    from_signature = db.Column(
        db.Text,
        nullable=True
    )

    to_signature = db.Column(
        db.Text,
        nullable=True
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    movement_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    from_location = db.Column(
        db.String(100)
    )

    to_location = db.Column(
        db.String(100)
    )

    from_department = db.Column(
        db.String(100)
    )

    to_department = db.Column(
        db.String(100)
    )

    from_pic = db.Column(
        db.String(100)
    )

    to_pic = db.Column(
        db.String(100)
    )

    reason = db.Column(
        db.String(255)
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime
    )

    asset = db.relationship(
        "Asset",
        back_populates="movements"
    )

    batch = db.relationship(
        "AssetMovementBatch",
        back_populates="items"
    )

# ============================================================
# ASSET MOVEMENT CORRECTION LOG
# ============================================================


class AssetMovementCorrection(db.Model):

    __tablename__ = "asset_movement_corrections"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    movement_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "asset_movements.id"
        ),
        nullable=False
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "assets.id"
        ),
        nullable=False
    )

    # ========================================================
    # WAKTU KOREKSI
    # ========================================================

    corrected_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # ========================================================
    # DATA SEBELUM KOREKSI
    # ========================================================

    old_movement_date = db.Column(
        db.Date,
        nullable=True
    )

    old_from_location = db.Column(
        db.String(100),
        nullable=True
    )

    old_to_location = db.Column(
        db.String(100),
        nullable=True
    )

    old_from_department = db.Column(
        db.String(100),
        nullable=True
    )

    old_to_department = db.Column(
        db.String(100),
        nullable=True
    )

    old_from_pic = db.Column(
        db.String(100),
        nullable=True
    )

    old_to_pic = db.Column(
        db.String(100),
        nullable=True
    )

    old_reason = db.Column(
        db.String(255),
        nullable=True
    )

    old_notes = db.Column(
        db.Text,
        nullable=True
    )

    # ========================================================
    # DATA SESUDAH KOREKSI
    # ========================================================

    new_movement_date = db.Column(
        db.Date,
        nullable=True
    )

    new_from_location = db.Column(
        db.String(100),
        nullable=True
    )

    new_to_location = db.Column(
        db.String(100),
        nullable=True
    )

    new_from_department = db.Column(
        db.String(100),
        nullable=True
    )

    new_to_department = db.Column(
        db.String(100),
        nullable=True
    )

    new_from_pic = db.Column(
        db.String(100),
        nullable=True
    )

    new_to_pic = db.Column(
        db.String(100),
        nullable=True
    )

    new_reason = db.Column(
        db.String(255),
        nullable=True
    )

    new_notes = db.Column(
        db.Text,
        nullable=True
    )

    # ========================================================
    # KETERANGAN KOREKSI
    # ========================================================

    correction_reason = db.Column(
        db.Text,
        nullable=True
    )

    # ========================================================
    # RELATIONSHIP
    # ========================================================

    movement = db.relationship(
        "AssetMovement",
        backref=db.backref(
            "corrections",
            lazy=True
        )
    )

    asset = db.relationship(
        "Asset",
        backref=db.backref(
            "movement_corrections",
            lazy=True
        )
    )

# ============================================================
# COMPANY
# ============================================================


class Company(db.Model):

    __tablename__ = "companies"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    logo = db.Column(
        db.String(255),
        nullable=True
    )

    address = db.Column(
        db.Text,
        nullable=True
    )

    phone = db.Column(
        db.String(50),
        nullable=True
    )

    email = db.Column(
        db.String(150),
        nullable=True
    )

    website = db.Column(
        db.String(200),
        nullable=True
    )

    tax_number = db.Column(
        db.String(100),
        nullable=True
    )

    document_prefix = db.Column(
        db.String(50),
        nullable=True,
        default="MT"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Company {self.name}>"

# ============================================================
# AUDIT LOG
# ============================================================


class AuditLog(db.Model):

    __tablename__ = "audit_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # user_id sengaja tidak pakai ForeignKey CASCADE ke User -
    # kalau user dihapus, log aktivitasnya harus tetap ada
    # (pakai username yang disimpan terpisah di bawah).
    user_id = db.Column(
        db.Integer,
        nullable=True,
    )

    username = db.Column(
        db.String(50),
        nullable=True,
    )

    action = db.Column(
        db.String(20),
        nullable=False,
    )

    entity_type = db.Column(
        db.String(50),
        nullable=False,
    )

    entity_label = db.Column(
        db.String(200),
        nullable=True,
    )

    description = db.Column(
        db.String(255),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"<AuditLog {self.username} "
            f"{self.action} {self.entity_type}>"
        )

# ============================================================
# ROLE & PERMISSION (MATRIX HAK AKSES)
# ============================================================

# Daftar "object" yang izinnya bisa diatur per role. Manajemen
# User/Role/Menu/Backup/Audit Log sengaja TIDAK masuk daftar ini -
# itu tetap khusus administrator, supaya role custom tidak bisa
# menaikkan hak aksesnya sendiri (privilege escalation).
PERMISSION_OBJECTS = [
    ("asset", "Asset"),
    ("movement", "Mutasi Asset"),
    ("category", "Kategori"),
    ("location", "Lokasi"),
    ("department", "Departemen"),
    ("vendor", "Vendor"),
    ("company", "Company"),
    ("scrap", "Scrap"),
    ("stock_opname", "Stok Opname"),
    ("atk_pickup", "Pengambilan ATK"),
]

# Kunci field_template yang direstriksi per role (lihat ASSET_TYPE_TABS
# di blueprints/assets.py - daftar ini HARUS sama persis dengan key di
# sana, dipakai di form Role untuk kasih label yang sama dengan yang
# dilihat admin di form Category).
CATEGORY_RESTRICTION_CHOICES = [
    ("pc_laptop", "PC / Laptop"),
    ("ponsel", "Phone"),
    ("server", "Server & Network"),
    ("non_pc", "Other Electronics (monitor, printer, CCTV, etc.)"),
    ("elektronik_interior", "Interior Electronics (AC, dispenser, fridge, etc.)"),
    ("elektronik_exterior", "Exterior Electronics (generator, etc.)"),
    ("kendaraan", "Vehicle (adds plate number & tax due date)"),
    ("furniture", "Furniture"),
    ("tools_mekanik", "Mechanical Tools"),
    ("atk", "Office Stationery (ATK)"),
    ("pantry", "Pantry"),
    ("tools_pantry", "Pantry Tools"),
    ("showcase", "Showcase (for customers)"),
    ("gudang_event", "Event Stock"),
]

# Sama dengan field_template di atas, tapi label pendek + icon -
# dipakai untuk tab quick-filter di Asset List (asset/_list_fragment.html)
# dan untuk pecah menu sidebar "Asset" jadi beberapa menu per kategori
# saat role-nya dibatasi kategorinya (lihat inject_nav_menu di
# app/__init__.py).
ASSET_TYPE_TAB_CHOICES = [
    ("pc_laptop", "PC / Laptop", "bi-laptop"),
    ("ponsel", "Phone", "bi-phone"),
    ("server", "Server & Network", "bi-hdd-network"),
    ("non_pc", "Other Electronics", "bi-display"),
    ("elektronik_interior", "Interior Electronics", "bi-house"),
    ("elektronik_exterior", "Exterior Electronics", "bi-lightning-charge"),
    ("kendaraan", "Vehicle", "bi-car-front"),
    ("furniture", "Furniture", "bi-box2"),
    ("tools_mekanik", "Mechanical Tools", "bi-tools"),
    ("atk", "ATK", "bi-pencil"),
    ("pantry", "Pantry", "bi-cup-hot"),
    ("tools_pantry", "Pantry Tools", "bi-bucket"),
    ("showcase", "Showcase", "bi-shop-window"),
    ("gudang_event", "Event Stock", "bi-boxes"),
]

PERMISSION_OBJECT_KEYS = [key for key, _label in PERMISSION_OBJECTS]

PERMISSION_ACTIONS = ["create", "read", "edit", "delete"]


class Role(db.Model):

    __tablename__ = "roles"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    description = db.Column(
        db.String(255),
        nullable=True,
    )

    # Role bawaan (administrator) tidak boleh dihapus/diganti nama,
    # supaya selalu ada minimal 1 role dengan akses penuh.
    is_system = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    # Daftar key field_template (ASSET_TYPE_TABS di blueprints/assets.py)
    # yang boleh dilihat/dikelola role ini, dipisah koma - sama persis
    # polanya dengan MenuItem.roles. None/kosong = TIDAK dibatasi (lihat
    # semua kategori), supaya role lama (administrator/admin/user) yang
    # sudah ada tidak berubah perilakunya tanpa perlu migrasi data.
    allowed_categories = db.Column(
        db.Text,
        nullable=True,
    )

    permissions = db.relationship(
        "Permission",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def permission_for(self, object_name):

        for perm in self.permissions:
            if perm.object_name == object_name:
                return perm

        return None

    def restricts_categories(self):

        return bool(self.allowed_categories)

    def allowed_category_templates(self):

        if not self.allowed_categories:
            return []

        return [
            key.strip()
            for key in self.allowed_categories.split(",")
            if key.strip()
        ]

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(db.Model):

    __tablename__ = "permissions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
    )

    object_name = db.Column(
        db.String(50),
        nullable=False,
    )

    can_create = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    can_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    can_edit = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    can_delete = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    role = db.relationship(
        "Role",
        back_populates="permissions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "role_id",
            "object_name",
            name="uq_permission_role_object",
        ),
    )

    def allows(self, action):
        return bool(
            getattr(self, f"can_{action}", False)
        )

    def __repr__(self):
        return (
            f"<Permission role={self.role_id} "
            f"{self.object_name}>"
        )

# ============================================================
# APP SETTING (BRANDING APLIKASI - BUKAN DATA PERUSAHAAN)
# ============================================================


class AppSetting(db.Model):
    """
    Pengaturan tampilan aplikasi itu sendiri (nama, logo, footer,
    halaman login) - beda dengan Company yang isinya data bisnis
    perusahaan untuk kop dokumen. Cuma ada 1 baris (singleton).
    """

    __tablename__ = "app_settings"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    app_name = db.Column(
        db.String(100),
        nullable=False,
        default="Asset Tracker",
    )

    footer_text = db.Column(
        db.String(255),
        nullable=True,
    )

    login_message = db.Column(
        db.String(255),
        nullable=True,
    )

    # Logo lebar/horizontal - dipakai di brand sidebar.
    logo_wide = db.Column(
        db.String(255),
        nullable=True,
    )

    # Logo kotak/square - dipakai di halaman login & favicon.
    logo_square = db.Column(
        db.String(255),
        nullable=True,
    )

    # Cara menampilkan identitas aplikasi di sidebar: "logo_only",
    # "name_only", atau "logo_and_name". Kalau logo belum diupload,
    # semua mode otomatis fallback ke icon + nama aplikasi.
    brand_display_mode = db.Column(
        db.String(20),
        nullable=False,
        default="logo_only",
        server_default="logo_only",
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self):
        return f"<AppSetting {self.app_name}>"

# ============================================================
# SCRAP (PENDATAAN BESI SISA MODIFIKASI KONTAINER)
# ============================================================

SCRAP_TYPE_BESI_BIASA = "besi_biasa"
SCRAP_TYPE_BESI_LGS = "besi_lgs"

SCRAP_TYPE_CHOICES = [
    (SCRAP_TYPE_BESI_BIASA, "Besi Biasa"),
    (SCRAP_TYPE_BESI_LGS, "Besi Baja Ringan / LGS"),
]

SCRAP_UNIT_CHOICES = ["kg", "ton"]


class ScrapRecord(db.Model):

    __tablename__ = "scrap_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    scrap_type = db.Column(
        db.String(20),
        nullable=False,
    )

    quantity = db.Column(
        db.Float,
        nullable=False,
    )

    unit = db.Column(
        db.String(10),
        nullable=False,
        default="kg",
    )

    recorded_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    def scrap_type_label(self):

        for key, label in SCRAP_TYPE_CHOICES:
            if key == self.scrap_type:
                return label

        return self.scrap_type

    def __repr__(self):
        return f"<ScrapRecord {self.scrap_type} {self.quantity}{self.unit}>"

# ============================================================
# STOK OPNAME (PENCATATAN STOK BULANAN ATK)
# ============================================================


class StockOpnameRecord(db.Model):
    """
    Satu baris = hasil stok opname 1 item ATK untuk 1 bulan (period).
    Sadam cuma input stok_keluar - stok_awal diambil otomatis dari
    stok_akhir bulan sebelumnya (atau Asset.stock_quantity kalau ini
    opname pertama untuk item tsb), stok_akhir dihitung otomatis
    (stok_awal - stok_keluar). Lihat blueprints/stock_opname.py.
    """

    __tablename__ = "stock_opname_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    # Awal bulan periode opname (selalu tanggal 1) - dipakai untuk
    # mengelompokkan & mengurutkan riwayat per bulan.
    period = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    stok_awal = db.Column(
        db.Integer,
        nullable=False,
    )

    stok_keluar = db.Column(
        db.Integer,
        nullable=False,
    )

    stok_akhir = db.Column(
        db.Integer,
        nullable=False,
    )

    # Rencana jumlah yang mau dibeli bulan ini - cuma dipakai untuk
    # kategori yang punya "pengajuan belanja bulanan" dengan batas
    # anggaran (saat ini: Showcase, lihat STOCK_OPNAME_BUDGET di
    # blueprints/stock_opname.py). Null/0 untuk kategori lain.
    qty_beli = db.Column(
        db.Integer,
        nullable=True,
    )

    recorded_by = db.Column(
        db.String(50),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=datetime.utcnow,
    )

    asset = db.relationship("Asset")

    __table_args__ = (
        db.UniqueConstraint(
            "asset_id",
            "period",
            name="uq_stock_opname_asset_period",
        ),
    )

    def __repr__(self):
        return f"<StockOpnameRecord asset={self.asset_id} period={self.period}>"


class VehicleServiceRecord(db.Model):
    """
    Satu baris = satu catatan servis/perawatan untuk 1 kendaraan pada
    satu tanggal - khusus Asset dengan field_template "kendaraan".
    Dipakai bebas (tidak dikelompokkan per bulan seperti sheet
    Excel asalnya) supaya bisa berapa pun catatan per kendaraan per
    bulan tanpa kolom tetap.
    """

    __tablename__ = "vehicle_service_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    service_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=False,
    )

    cost = db.Column(
        db.Float,
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    recorded_by = db.Column(
        db.String(50),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    asset = db.relationship("Asset")

    def __repr__(self):
        return f"<VehicleServiceRecord asset={self.asset_id} date={self.service_date}>"


class StickyNote(db.Model):
    """Catatan pribadi (sticky notes) per user, dibuka dari ikon di navbar."""

    __tablename__ = "sticky_notes"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    content = db.Column(
        db.Text,
        nullable=False,
        default="",
    )

    color = db.Column(
        db.String(10),
        nullable=False,
        default="yellow",
    )

    pinned = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=datetime.utcnow,
    )

    def as_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "color": self.color,
            "pinned": self.pinned,
            "updated_at": self.updated_at.strftime("%d-%m-%Y %H:%M"),
        }


class AtkPickup(db.Model):
    """
    Satu transaksi pengambilan ATK oleh satu pegawai (bisa beberapa
    item sekaligus, lihat AtkPickupItem) - dicatat oleh Office Boy
    (Sadam/Taufik/Roni) lewat scan QR rak, bukan oleh pegawai itu
    sendiri. Nama pegawai wajib diisi, tanda tangan opsional
    (cukup salah satu sebagai bukti pengambilan).
    """

    __tablename__ = "atk_pickups"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_name = db.Column(
        db.String(100),
        nullable=False,
    )

    # Data URL PNG dari canvas tanda tangan - opsional, nama pegawai
    # saja sudah cukup jadi bukti kalau tidak diisi.
    signature = db.Column(
        db.Text,
        nullable=True,
    )

    recorded_by = db.Column(
        db.String(50),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    items = db.relationship(
        "AtkPickupItem",
        backref="pickup",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<AtkPickup {self.employee_name} at {self.created_at}>"


class AtkPickupItem(db.Model):
    """
    Satu baris item dalam satu transaksi AtkPickup. Nama/kategori/
    satuan disalin (snapshot) dari Asset saat transaksi dibuat, supaya
    laporan lama tetap benar meskipun data Asset-nya berubah/dihapus
    belakangan.
    """

    __tablename__ = "atk_pickup_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    pickup_id = db.Column(
        db.Integer,
        db.ForeignKey("atk_pickups.id"),
        nullable=False,
        index=True,
    )

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id"),
        nullable=True,
        index=True,
    )

    asset_name = db.Column(
        db.String(100),
        nullable=False,
    )

    category = db.Column(
        db.String(50),
        nullable=True,
    )

    unit = db.Column(
        db.String(20),
        nullable=True,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
    )

    asset = db.relationship("Asset")

    def __repr__(self):
        return f"<AtkPickupItem {self.asset_name} x{self.quantity}>"
