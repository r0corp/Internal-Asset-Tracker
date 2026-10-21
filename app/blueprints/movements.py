"""
Mutasi asset: daftar, laporan, export, tambah, koreksi, QR verifikasi.
"""

import io
import os

from datetime import datetime, date

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_file,
)

from flask_babel import gettext as _

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from sqlalchemy.orm import contains_eager

from .. import db
from ..models import (
    Asset,
    Category,
    Location,
    Department,
    Vendor,
    AssetMovement,
    AssetMovementBatch,
    AssetMovementCorrection,
    Company,
)

from ..auth import requires_permission

from . import main, MOVEMENT_LIST_PER_PAGE, SimplePagination
from .helpers import parse_date

@main.route("/assets/movements/export")
@requires_permission("movement", "read")
def export_asset_movements():

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    movements = (
        AssetMovement.query
        .order_by(
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc(),
        )
        .all()
    )

    workbook = Workbook()

    worksheet = workbook.active
    worksheet.title = "Mutasi Asset"

    headers = [
        "No",
        "No. Mutasi",
        "Tanggal Mutasi",
        "Asset Tag",
        "Nama Asset",
        "Dari Lokasi",
        "Ke Lokasi",
        "Dari Department",
        "Ke Department",
        "Dari PIC",
        "Ke PIC",
        "Alasan",
        "Catatan",
        "Nama Penyerah",
        "Jabatan Penyerah",
        "Nama Penerima",
        "Jabatan Penerima",
        "Dibuat",
    ]

    worksheet.append(headers)

    for cell in worksheet[1]:

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for number, movement in enumerate(
        movements,
        start=1,
    ):

        asset = movement.asset

        worksheet.append([
            number,
            movement.movement_no or "",
            (
                movement.movement_date.strftime("%d-%m-%Y")
                if movement.movement_date
                else ""
            ),
            asset.asset_tag if asset else "",
            asset.asset_name if asset else "",
            movement.from_location or "",
            movement.to_location or "",
            movement.from_department or "",
            movement.to_department or "",
            movement.from_pic or "",
            movement.to_pic or "",
            movement.reason or "",
            movement.notes or "",
            movement.from_signer_name or "",
            movement.from_signer_position or "",
            movement.to_signer_name or "",
            movement.to_signer_position or "",
            (
                movement.created_at.strftime("%d-%m-%Y %H:%M")
                if movement.created_at
                else ""
            ),
        ])

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    column_widths = {
        "A": 8,
        "B": 22,
        "C": 18,
        "D": 20,
        "E": 30,
        "F": 25,
        "G": 25,
        "H": 25,
        "I": 25,
        "J": 20,
        "K": 20,
        "L": 35,
        "M": 40,
        "N": 25,
        "O": 25,
        "P": 25,
        "Q": 25,
        "R": 22,
    }

    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    output = io.BytesIO()

    workbook.save(output)
    output.seek(0)

    filename = (
        "mutasi_asset_export_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".xlsx"
    )

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

# ============================================================
# IMPORT ASSET
# ============================================================


@main.route(
    "/assets/<int:asset_id>/movements"
)
@requires_permission("movement", "read")
def asset_movements(asset_id):

    # ========================================================
    # AMBIL ASSET
    # ========================================================

    asset = Asset.query.get_or_404(
        asset_id
    )

    # ========================================================
    # AMBIL SELURUH MOVEMENT ASSET
    #
    # Urutan histori:
    # movement paling lama -> paling baru
    #
    # ID digunakan sebagai secondary ordering apabila
    # terdapat beberapa movement pada tanggal yang sama.
    # ========================================================

    movements = (
        AssetMovement.query
        .filter(
            AssetMovement.asset_id == asset.id
        )
        .order_by(
            AssetMovement.movement_date.asc(),
            AssetMovement.id.asc(),
        )
        .all()
    )

    # ========================================================
    # MOVEMENT TERAKHIR
    #
    # Hanya movement terakhir yang dapat dikoreksi.
    # ========================================================

    last_movement = (
        movements[-1]
        if movements
        else None
    )

    # ========================================================
    # JUMLAH MOVEMENT
    # ========================================================

    movement_count = len(
        movements
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "asset/movements.html",

        asset=asset,

        movements=movements,

        last_movement=last_movement,

        movement_count=movement_count,
    )

# ============================================================
# LAPORAN MUTASI ASSET
# ============================================================


@main.route("/assets/movements/report")
@requires_permission("movement", "read")
def asset_movements_report():

    start_date = parse_date(
        request.args.get("start_date")
    )

    end_date = parse_date(
        request.args.get("end_date")
    )

    query = (
        AssetMovement.query
        .join(
            Asset,
            Asset.id == AssetMovement.asset_id,
        )
    )

    if start_date:

        query = query.filter(
            AssetMovement.movement_date >= start_date
        )

    if end_date:

        query = query.filter(
            AssetMovement.movement_date <= end_date
        )

    movements = (
        query
        .order_by(
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc(),
        )
        .all()
    )

    total_movements = (
        AssetMovement.query.count()
    )

    filtered_movements = len(movements)

    location_rows = (
        db.session.query(
            AssetMovement.to_location,
            db.func.count(AssetMovement.id),
        )
        .filter(
            AssetMovement.to_location.isnot(None)
        )
        .filter(
            AssetMovement.to_location != ""
        )
        .group_by(
            AssetMovement.to_location
        )
        .order_by(
            db.func.count(
                AssetMovement.id
            ).desc()
        )
        .all()
    )

    top_location = "-"

    if location_rows:
        top_location = location_rows[0][0]

    department_rows = (
        db.session.query(
            AssetMovement.to_department,
            db.func.count(AssetMovement.id),
        )
        .filter(
            AssetMovement.to_department.isnot(None)
        )
        .filter(
            AssetMovement.to_department != ""
        )
        .group_by(
            AssetMovement.to_department
        )
        .order_by(
            db.func.count(
                AssetMovement.id
            ).desc()
        )
        .all()
    )

    top_department = "-"

    if department_rows:
        top_department = department_rows[0][0]

    return render_template(
        "asset/movement_report.html",
        movements=movements,
        start_date=start_date,
        end_date=end_date,
        total_movements=total_movements,
        filtered_movements=filtered_movements,
        top_location=top_location,
        top_department=top_department,
    )

# ============================================================
# GLOBAL ASSET MOVEMENTS
# ============================================================


@main.route("/assets/movements")
@requires_permission("movement", "read")
def global_asset_movements():

    # ========================================================
    # FILTER
    # ========================================================

    search = (
        request.args.get(
            "search",
            ""
        )
        or ""
    ).strip()

    status_filter = (
        request.args.get(
            "status",
            ""
        )
        or ""
    ).strip().upper()

    date_from = (
        request.args.get(
            "date_from",
            ""
        )
        or ""
    ).strip()

    date_to = (
        request.args.get(
            "date_to",
            ""
        )
        or ""
    ).strip()

    location = (
        request.args.get(
            "location",
            ""
        )
        or ""
    ).strip()

    department = (
        request.args.get(
            "department",
            ""
        )
        or ""
    ).strip()

    pic = (
        request.args.get(
            "pic",
            ""
        )
        or ""
    ).strip()

    # ========================================================
    # QUERY DASAR
    # ========================================================

    query = (
        AssetMovement.query
        .join(
            Asset,
            AssetMovement.asset_id
            == Asset.id
        )
        .options(
            contains_eager(AssetMovement.asset)
        )
    )

    # ========================================================
    # SEARCH
    # ========================================================

    if search:

        search_pattern = (
            f"%{search}%"
        )

        query = query.filter(
            db.or_(

                AssetMovement.movement_no.ilike(
                    search_pattern
                ),

                Asset.asset_tag.ilike(
                    search_pattern
                ),

                Asset.asset_name.ilike(
                    search_pattern
                ),

                AssetMovement.from_location.ilike(
                    search_pattern
                ),

                AssetMovement.to_location.ilike(
                    search_pattern
                ),

                AssetMovement.from_department.ilike(
                    search_pattern
                ),

                AssetMovement.to_department.ilike(
                    search_pattern
                ),

                AssetMovement.from_pic.ilike(
                    search_pattern
                ),

                AssetMovement.to_pic.ilike(
                    search_pattern
                )
            )
        )

    # ========================================================
    # DATE FROM
    # ========================================================

    if date_from:

        parsed_date_from = parse_date(
            date_from
        )

        if parsed_date_from:

            query = query.filter(
                AssetMovement.movement_date
                >= parsed_date_from
            )

    # ========================================================
    # DATE TO
    # ========================================================

    if date_to:

        parsed_date_to = parse_date(
            date_to
        )

        if parsed_date_to:

            query = query.filter(
                AssetMovement.movement_date
                <= parsed_date_to
            )

    # ========================================================
    # LOCATION
    # ========================================================

    if location:

        location_pattern = (
            f"%{location}%"
        )

        query = query.filter(
            db.or_(

                AssetMovement.from_location.ilike(
                    location_pattern
                ),

                AssetMovement.to_location.ilike(
                    location_pattern
                )
            )
        )

    # ========================================================
    # DEPARTMENT
    # ========================================================

    if department:

        department_pattern = (
            f"%{department}%"
        )

        query = query.filter(
            db.or_(

                AssetMovement.from_department.ilike(
                    department_pattern
                ),

                AssetMovement.to_department.ilike(
                    department_pattern
                )
            )
        )

    # ========================================================
    # PIC
    # ========================================================

    if pic:

        pic_pattern = (
            f"%{pic}%"
        )

        query = query.filter(
            db.or_(

                AssetMovement.from_pic.ilike(
                    pic_pattern
                ),

                AssetMovement.to_pic.ilike(
                    pic_pattern
                )
            )
        )

    # ========================================================
    # AMBIL DATA MOVEMENT
    # ========================================================

    movements = (
        query
        .order_by(
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc()
        )
        .all()
    )

    # ========================================================
    # TENTUKAN MOVEMENT TERAKHIR SETIAP ASSET
    #
    # Dibuat satu kali untuk seluruh asset.
    # Tidak melakukan query berulang di dalam loop.
    # ========================================================

    latest_movement_by_asset = {}

    # Cuma ambil kolom (asset_id, id) - bukan seluruh baris (yang
    # ikut menyeret from_signature/to_signature TEXT besar) - kita
    # cuma butuh id movement terbaru per asset di sini.
    all_asset_movement_ids = (
        db.session.query(
            AssetMovement.asset_id,
            AssetMovement.id,
        )
        .order_by(
            AssetMovement.asset_id.asc(),
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc()
        )
        .all()
    )

    for asset_id, movement_id in all_asset_movement_ids:

        if asset_id not in latest_movement_by_asset:

            latest_movement_by_asset[asset_id] = movement_id

    # ========================================================
    # BENTUK DATA UNTUK TEMPLATE
    # ========================================================

    movement_rows = []

    for movement in movements:

        latest_movement_id = (
            latest_movement_by_asset.get(
                movement.asset_id
            )
        )

        is_current = (
            latest_movement_id is not None
            and
            latest_movement_id
            == movement.id
        )

        movement_status = (
            "CURRENT"
            if is_current
            else "HISTORY"
        )

        # ----------------------------------------------------
        # FILTER STATUS
        # ----------------------------------------------------

        if (
            status_filter
            and
            status_filter
            != movement_status
        ):

            continue

        movement_rows.append({

            "movement": movement,

            "asset": movement.asset,

            "status": movement_status,

        })

    # ========================================================
    # MASTER LOCATION
    # ========================================================

    locations = (
        Location.query
        .order_by(
            Location.name.asc()
        )
        .all()
    )

    # ========================================================
    # MASTER DEPARTMENT
    # ========================================================

    departments = (
        Department.query
        .order_by(
            Department.name.asc()
        )
        .all()
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    total_movements = (
        len(movement_rows)
    )

    current_movements = sum(
        1
        for row in movement_rows
        if row["status"] == "CURRENT"
    )

    history_movements = sum(
        1
        for row in movement_rows
        if row["status"] == "HISTORY"
    )

    # ========================================================
    # PAGINATION (untuk tabel, summary tetap pakai movement_rows)
    # ========================================================

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    pagination = SimplePagination(
        movement_rows,
        page,
        MOVEMENT_LIST_PER_PAGE,
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "asset/movements_global.html",

        movements=movement_rows,

        pagination=pagination,

        search=search,

        status_filter=status_filter,

        date_from=date_from,

        date_to=date_to,

        location=location,

        department=department,

        pic=pic,

        locations=locations,

        departments=departments,

        total_movements=total_movements,

        current_movements=current_movements,

        history_movements=history_movements,

    )


# ============================================================
# EXPORT LAPORAN MUTASI ASSET
# ============================================================

# ============================================================
# EXPORT LAPORAN MUTASI ASSET
# ============================================================


@main.route(
    "/assets/movements/report/export"
)
@requires_permission("movement", "read")
def export_asset_movements_report():

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    start_date = parse_date(
        request.args.get("start_date")
    )

    end_date = parse_date(
        request.args.get("end_date")
    )

    query = (
        AssetMovement.query
        .join(
            Asset,
            Asset.id == AssetMovement.asset_id,
        )
    )

    if start_date:

        query = query.filter(
            AssetMovement.movement_date >= start_date
        )

    if end_date:

        query = query.filter(
            AssetMovement.movement_date <= end_date
        )

    movements = (
        query
        .order_by(
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc(),
        )
        .all()
    )

    workbook = Workbook()

    worksheet = workbook.active
    worksheet.title = "Laporan Mutasi"

    headers = [
        "No",
        "No. Mutasi",
        "Tanggal",
        "Asset Tag",
        "Nama Asset",
        "Category",
        "Dari Lokasi",
        "Ke Lokasi",
        "Dari Department",
        "Ke Department",
        "Dari PIC",
        "Ke PIC",
        "Alasan",
        "Catatan",
        "Penyerah",
        "Jabatan Penyerah",
        "Penerima",
        "Jabatan Penerima",
    ]

    worksheet.append(headers)

    for cell in worksheet[1]:

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for number, movement in enumerate(
        movements,
        start=1,
    ):

        asset = movement.asset

        worksheet.append([
            number,
            movement.movement_no or "",
            (
                movement.movement_date.strftime("%d-%m-%Y")
                if movement.movement_date
                else ""
            ),
            asset.asset_tag if asset else "",
            asset.asset_name if asset else "",
            asset.category if asset else "",
            movement.from_location or "",
            movement.to_location or "",
            movement.from_department or "",
            movement.to_department or "",
            movement.from_pic or "",
            movement.to_pic or "",
            movement.reason or "",
            movement.notes or "",
            movement.from_signer_name or "",
            movement.from_signer_position or "",
            movement.to_signer_name or "",
            movement.to_signer_position or "",
        ])

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    column_widths = {
        "A": 8,
        "B": 22,
        "C": 15,
        "D": 18,
        "E": 30,
        "F": 20,
        "G": 25,
        "H": 25,
        "I": 25,
        "J": 25,
        "K": 22,
        "L": 22,
        "M": 30,
        "N": 40,
        "O": 25,
        "P": 25,
        "Q": 25,
        "R": 25,
    }

    for column, width in column_widths.items():

        worksheet.column_dimensions[
            column
        ].width = width

    output = io.BytesIO()

    workbook.save(output)
    output.seek(0)

    if start_date and end_date:

        period = (
            f"{start_date.strftime('%Y%m%d')}_"
            f"{end_date.strftime('%Y%m%d')}"
        )

    elif start_date:

        period = (
            f"from_{start_date.strftime('%Y%m%d')}"
        )

    elif end_date:

        period = (
            f"until_{end_date.strftime('%Y%m%d')}"
        )

    else:

        period = "all"

    filename = (
        "laporan_mutasi_"
        + period
        + "_"
        + datetime.now().strftime("%H%M%S")
        + ".xlsx"
    )

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

# ============================================================
# ASSET MOVEMENT DETAIL / BUKTI MUTASI
# ============================================================


@main.route(
    "/assets/<int:asset_id>/movement/<int:movement_id>"
)
@requires_permission("movement", "read")
def asset_movement_detail(
    asset_id,
    movement_id
):
    """
    Link lama (dari riwayat mutasi per-asset, daftar mutasi global, dst)
    tetap mengarah ke sini - diarahkan ke halaman cetak batch yang
    memuat movement ini, supaya semua link yang sudah ada tidak perlu
    diubah satu-satu.
    """

    movement = (
        AssetMovement.query
        .filter(
            AssetMovement.id == movement_id,
            AssetMovement.asset_id == asset_id,
        )
        .first_or_404()
    )

    return redirect(
        url_for(
            "main.asset_movement_batch_detail",
            batch_id=movement.batch_id,
        )
    )


@main.route(
    "/assets/movements/<int:batch_id>"
)
@requires_permission("movement", "read")
def asset_movement_batch_detail(batch_id):
    """
    Dokumen "Tanda Terima" - satu batch bisa memuat beberapa asset
    sekaligus, dengan satu pasang tanda tangan untuk semuanya.
    """

    batch = AssetMovementBatch.query.get_or_404(batch_id)

    items = (
        AssetMovement.query
        .filter(AssetMovement.batch_id == batch.id)
        .join(Asset, AssetMovement.asset_id == Asset.id)
        .options(contains_eager(AssetMovement.asset))
        .order_by(AssetMovement.id.asc())
        .all()
    )

    company = (
        Company.query
        .order_by(Company.id.asc())
        .first()
    )

    # Dihitung terpisah (bukan item.corrections) supaya tidak lazy-load
    # per baris di template - mengikuti pola yang sama di route lain.
    corrected_movement_ids = {
        row[0]
        for row in (
            db.session.query(AssetMovementCorrection.movement_id)
            .filter(
                AssetMovementCorrection.movement_id.in_(
                    [item.id for item in items]
                )
            )
            .distinct()
            .all()
        )
    }

    return render_template(
        "asset/movement_detail.html",
        batch=batch,
        items=items,
        company=company,
        corrected_movement_ids=corrected_movement_ids,
    )

# ============================================================
# ASSET MOVEMENT CORRECTION HISTORY
# ============================================================


@main.route(
    "/assets/<int:asset_id>/movement/<int:movement_id>/corrections"
)
@requires_permission("movement", "read")
def asset_movement_corrections(
    asset_id,
    movement_id
):

    # ========================================================
    # AMBIL ASSET
    # ========================================================

    asset = Asset.query.get_or_404(
        asset_id
    )

    # ========================================================
    # AMBIL MOVEMENT
    # ========================================================

    movement = (
        AssetMovement.query
        .filter(
            AssetMovement.id == movement_id,
            AssetMovement.asset_id == asset_id
        )
        .first_or_404()
    )

    # ========================================================
    # AMBIL RIWAYAT KOREKSI
    # ========================================================

    corrections = (
        AssetMovementCorrection.query
        .filter(
            AssetMovementCorrection.movement_id
            == movement.id
        )
        .order_by(
            AssetMovementCorrection.corrected_at.desc(),
            AssetMovementCorrection.id.desc()
        )
        .all()
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "asset/movement_corrections.html",

        asset=asset,

        movement=movement,

        corrections=corrections,
    )


# ============================================================
# DASHBOARD ANALYTICS
# ============================================================


@main.route(
    "/assets/<int:asset_id>/movement/add",
    methods=["GET"],
)
@requires_permission("movement", "create")
def add_asset_movement(asset_id):
    """
    Alur lama "Catat Mutasi" dari halaman 1 asset - diarahkan ke form
    serah-terima multi-asset yang baru, dengan asset ini sudah
    ter-centang duluan, supaya tombol yang sudah ada di halaman detail
    asset tetap jalan tanpa perlu ubah link-nya satu-satu.
    """

    Asset.query.get_or_404(asset_id)

    return redirect(
        url_for(
            "main.add_asset_movement_batch",
            asset_id=asset_id,
        )
    )


@main.route(
    "/assets/movements/add",
    methods=["GET", "POST"],
)
@requires_permission("movement", "create")
def add_asset_movement_batch():
    """
    Catat 1 serah-terima yang bisa mencakup BANYAK asset sekaligus
    (mis. laptop + HP diserahkan ke 1 orang di 1 tanggal), meniru form
    fisik "Tanda Terima" - satu tanggal, satu tujuan, satu pasang tanda
    tangan untuk semua barang yang dipilih. Tiap asset yang dipilih
    jadi 1 baris AssetMovement (menyimpan from_* miliknya sendiri),
    semuanya ditandai dengan batch_id yang sama (lihat
    AssetMovementBatch di models.py).
    """

    assets = (
        Asset.query
        .order_by(Asset.asset_tag.asc())
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

    preselected_id = request.args.get(
        "asset_id",
        type=int,
    )

    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    # ========================================================
    # ASSET TERPILIH
    # ========================================================

    selected_ids = []

    for value in request.form.getlist("asset_ids"):

        try:
            selected_ids.append(int(value))
        except (TypeError, ValueError):
            continue

    selected_assets = (
        Asset.query
        .filter(Asset.id.in_(selected_ids))
        .order_by(Asset.asset_tag.asc())
        .all()
    ) if selected_ids else []

    if not selected_assets:

        flash(
            _("Select at least one asset to hand over."),
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    # ========================================================
    # TANGGAL
    # ========================================================

    movement_date = parse_date(
        request.form.get("movement_date")
    )

    if not movement_date:

        flash(
            _("Movement date is required."),
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    # ========================================================
    # TUJUAN (berlaku untuk semua asset terpilih)
    # ========================================================

    to_location = (request.form.get("to_location") or "").strip()
    to_department = (request.form.get("to_department") or "").strip()
    to_pic = (request.form.get("to_pic") or "").strip()

    if not to_location:

        flash(
            _("Destination location is required."),
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    if not to_department:

        flash(
            _("Destination department is required."),
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    if not to_pic:

        flash(
            _("Destination PIC is required."),
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    # ========================================================
    # DATA TAMBAHAN & TANDA TANGAN
    # ========================================================

    reason = (request.form.get("reason") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    from_signer_name = (request.form.get("from_signer_name") or "").strip()
    from_signer_position = (request.form.get("from_signer_position") or "").strip()
    to_signer_name = (request.form.get("to_signer_name") or "").strip()
    to_signer_position = (request.form.get("to_signer_position") or "").strip()

    from_signature = (request.form.get("from_signature") or "").strip()
    to_signature = (request.form.get("to_signature") or "").strip()

    # ========================================================
    # CEK KONSISTENSI PER-ASSET
    #
    # Sama seperti alur lama: kondisi asset harus sinkron dengan
    # movement terakhirnya sebelum dibuatkan movement baru, dan
    # movement tidak dibuat kalau posisi tidak berubah sama sekali.
    # ========================================================

    unchanged_assets = []

    for asset in selected_assets:

        latest_movement = (
            AssetMovement.query
            .filter_by(asset_id=asset.id)
            .order_by(AssetMovement.id.desc())
            .first()
        )

        if latest_movement:

            if (
                (asset.location or "").strip() != (latest_movement.to_location or "").strip()
                or (asset.department or "").strip() != (latest_movement.to_department or "").strip()
                or (asset.pic or "").strip() != (latest_movement.to_pic or "").strip()
            ):

                flash(
                    _(
                        "Asset %(tag)s data is not in sync with its latest "
                        "movement. Please check and correct the asset data "
                        "before creating a new movement."
                    ) % {"tag": asset.asset_tag},
                    "danger",
                )

                return render_template(
                    "asset/movement_batch_add.html",
                    assets=assets,
                    locations=locations,
                    departments=departments,
                    preselected_id=preselected_id,
                )

        if (
            (asset.location or "").strip() == to_location
            and (asset.department or "").strip() == to_department
            and (asset.pic or "").strip() == to_pic
        ):

            unchanged_assets.append(asset.asset_tag)

    if unchanged_assets:

        flash(
            _(
                "These assets have no change in position: %(tags)s"
            ) % {"tags": ", ".join(unchanged_assets)},
            "warning",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    # ========================================================
    # GENERATE NOMOR MUTASI (1 nomor untuk seluruh batch)
    # ========================================================

    last_batch = (
        AssetMovementBatch.query
        .order_by(AssetMovementBatch.id.desc())
        .first()
    )

    next_number = (last_batch.id + 1) if last_batch else 1

    movement_no = (
        "MT-" + movement_date.strftime("%Y%m%d") + "-" + str(next_number).zfill(4)
    )

    # ========================================================
    # SIMPAN BATCH + 1 MOVEMENT PER ASSET
    # ========================================================

    try:

        batch = AssetMovementBatch(
            movement_no=movement_no,
            movement_date=movement_date,
            to_location=to_location,
            to_department=to_department,
            to_pic=to_pic,
            reason=reason,
            notes=notes,
            from_signer_name=from_signer_name,
            from_signer_position=from_signer_position,
            to_signer_name=to_signer_name,
            to_signer_position=to_signer_position,
            from_signature=from_signature,
            to_signature=to_signature,
            created_at=datetime.utcnow(),
        )

        db.session.add(batch)
        db.session.flush()

        for asset in selected_assets:

            movement = AssetMovement(
                batch_id=batch.id,
                movement_no=movement_no,
                asset_id=asset.id,
                movement_date=movement_date,
                from_location=(asset.location or "").strip(),
                from_department=(asset.department or "").strip(),
                from_pic=(asset.pic or "").strip(),
                to_location=to_location,
                to_department=to_department,
                to_pic=to_pic,
                from_signer_name=from_signer_name,
                from_signer_position=from_signer_position,
                to_signer_name=to_signer_name,
                to_signer_position=to_signer_position,
                from_signature=from_signature,
                to_signature=to_signature,
                reason=reason,
                notes=notes,
                created_at=datetime.utcnow(),
            )

            db.session.add(movement)

            asset.location = to_location
            asset.department = to_department
            asset.pic = to_pic

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            "Gagal menyimpan asset movement batch."
        )

        flash(
            _("Failed to save the movement. Detail: %(error)s")
            % {"error": str(e)},
            "danger",
        )

        return render_template(
            "asset/movement_batch_add.html",
            assets=assets,
            locations=locations,
            departments=departments,
            preselected_id=preselected_id,
        )

    flash(
        _("Asset movement saved successfully. Movement number: %(number)s")
        % {"number": movement_no},
        "success",
    )

    return redirect(
        url_for(
            "main.asset_movement_batch_detail",
            batch_id=batch.id,
        )
    )


# ============================================================
# KOREKSI ASSET MOVEMENT
# ============================================================


@main.route(
    "/assets/<int:asset_id>/movement/<int:movement_id>/correct",
    methods=["GET", "POST"],
)
@requires_permission("movement", "edit")
def correct_asset_movement(
    asset_id,
    movement_id
):

    # ========================================================
    # AMBIL ASSET
    # ========================================================

    asset = Asset.query.get_or_404(
        asset_id
    )

    # ========================================================
    # AMBIL MOVEMENT
    # ========================================================

    movement = (
        AssetMovement.query
        .filter_by(
            id=movement_id,
            asset_id=asset.id
        )
        .first_or_404()
    )

    # ========================================================
    # CEK MOVEMENT TERAKHIR
    #
    # HANYA MOVEMENT TERAKHIR YANG BOLEH DIKOREKSI.
    #
    # Hal ini menjaga histori movement tetap konsisten.
    # ========================================================

    latest_movement = (
        AssetMovement.query
        .filter_by(
            asset_id=asset.id
        )
        .order_by(
            AssetMovement.id.desc()
        )
        .first()
    )

    if not latest_movement:

        flash(
            _("Movement not found."),
            "danger"
        )

        return redirect(
            url_for(
                "main.asset_detail",
                asset_id=asset.id
            )
        )

    if latest_movement.id != movement.id:

        flash(
            _(
                "This movement is not the latest movement for this "
                "asset. Only the latest movement can be corrected."
            ),
            "warning"
        )

        return redirect(
            url_for(
                "main.asset_movement_detail",
                asset_id=asset.id,
                movement_id=movement.id
            )
        )

    # ========================================================
    # CARI MOVEMENT SEBELUMNYA
    #
    # FROM movement saat ini harus sama dengan TO
    # movement sebelumnya.
    #
    # Ini adalah bagian penting untuk menjaga histori.
    # ========================================================

    previous_movement = (
        AssetMovement.query
        .filter(
            AssetMovement.asset_id == asset.id,
            AssetMovement.id < movement.id,
        )
        .order_by(
            AssetMovement.id.desc()
        )
        .first()
    )

    # ========================================================
    # TENTUKAN FROM YANG BENAR
    #
    # Jika ada movement sebelumnya:
    #
    # FROM LOCATION    = TO LOCATION sebelumnya
    # FROM DEPARTMENT  = TO DEPARTMENT sebelumnya
    # FROM PIC         = TO PIC sebelumnya
    #
    # Jika ini movement pertama:
    # FROM dipertahankan dari data movement saat ini.
    # ========================================================

    if previous_movement:

        correct_from_location = (
            previous_movement.to_location
            or ""
        ).strip()

        correct_from_department = (
            previous_movement.to_department
            or ""
        ).strip()

        correct_from_pic = (
            previous_movement.to_pic
            or ""
        ).strip()

    else:

        correct_from_location = (
            movement.from_location
            or ""
        ).strip()

        correct_from_department = (
            movement.from_department
            or ""
        ).strip()

        correct_from_pic = (
            movement.from_pic
            or ""
        ).strip()

    # ========================================================
    # MASTER DATA
    # ========================================================

    locations = (
        Location.query
        .order_by(
            Location.name.asc()
        )
        .all()
    )

    departments = (
        Department.query
        .order_by(
            Department.name.asc()
        )
        .all()
    )

    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # POST
    # ========================================================

    movement_date = parse_date(
        request.form.get(
            "movement_date"
        )
    )

    # ========================================================
    # VALIDASI TANGGAL
    # ========================================================

    if not movement_date:

        flash(
            _("Movement date is required."),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # VALIDASI URUTAN TANGGAL
    #
    # Movement terakhir tidak boleh memiliki tanggal
    # sebelum movement sebelumnya.
    # ========================================================

    if (
        previous_movement
        and previous_movement.movement_date
        and movement_date < previous_movement.movement_date
    ):

        flash(
            _(
                "Movement date cannot be earlier than the previous "
                "movement."
            ),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # TO DIAMBIL DARI FORM
    #
    # FROM SENGAJA TIDAK DIAMBIL DARI FORM.
    #
    # FROM ditentukan berdasarkan histori database.
    # ========================================================

    to_location = (
        request.form.get(
            "to_location"
        )
        or ""
    ).strip()

    to_department = (
        request.form.get(
            "to_department"
        )
        or ""
    ).strip()

    to_pic = (
        request.form.get(
            "to_pic"
        )
        or ""
    ).strip()

    # ========================================================
    # DATA TAMBAHAN
    # ========================================================

    reason = (
        request.form.get(
            "reason"
        )
        or ""
    ).strip()

    notes = (
        request.form.get(
            "notes"
        )
        or ""
    ).strip()

    from_signer_name = (
        request.form.get(
            "from_signer_name"
        )
        or ""
    ).strip()

    from_signer_position = (
        request.form.get(
            "from_signer_position"
        )
        or ""
    ).strip()

    to_signer_name = (
        request.form.get(
            "to_signer_name"
        )
        or ""
    ).strip()

    to_signer_position = (
        request.form.get(
            "to_signer_position"
        )
        or ""
    ).strip()

    from_signature = (
        request.form.get(
            "from_signature"
        )
        or ""
    ).strip()

    to_signature = (
        request.form.get(
            "to_signature"
        )
        or ""
    ).strip()

    # ========================================================
    # VALIDASI FROM
    #
    # Validasi dilakukan terhadap hasil database,
    # bukan terhadap input user.
    # ========================================================

    if not correct_from_location:

        flash(
            _(
                "The movement's origin location could not be "
                "determined from the asset history."
            ),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    if not correct_from_department:

        flash(
            _(
                "The movement's origin department could not be "
                "determined from the asset history."
            ),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # VALIDASI TO LOCATION
    # ========================================================

    if not to_location:

        flash(
            _("Destination location is required."),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # VALIDASI TO DEPARTMENT
    # ========================================================

    if not to_department:

        flash(
            _("Destination department is required."),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # VALIDASI TO PIC
    # ========================================================

    if not to_pic:

        flash(
            _("Destination PIC is required."),
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # CEK APAKAH ADA PERUBAHAN
    # ========================================================

    if (
        correct_from_location == to_location
        and
        correct_from_department == to_department
        and
        correct_from_pic == to_pic
    ):

        flash(
            _("Movement has no change in asset position."),
            "warning"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

    # ========================================================
    # UPDATE MOVEMENT
    # ========================================================

    movement.movement_date = movement_date

    # --------------------------------------------------------
    # FROM
    #
    # SELALU BERASAL DARI HISTORI DATABASE.
    # --------------------------------------------------------

    movement.from_location = (
        correct_from_location
    )

    movement.from_department = (
        correct_from_department
    )

    movement.from_pic = (
        correct_from_pic
    )

    # --------------------------------------------------------
    # TO
    # --------------------------------------------------------

    movement.to_location = (
        to_location
    )

    movement.to_department = (
        to_department
    )

    movement.to_pic = (
        to_pic
    )

    # --------------------------------------------------------
    # SIGNER
    # --------------------------------------------------------

    movement.from_signer_name = (
        from_signer_name
    )

    movement.from_signer_position = (
        from_signer_position
    )

    movement.to_signer_name = (
        to_signer_name
    )

    movement.to_signer_position = (
        to_signer_position
    )

    # --------------------------------------------------------
    # SIGNATURE
    # --------------------------------------------------------

    movement.from_signature = (
        from_signature
    )

    movement.to_signature = (
        to_signature
    )

    # --------------------------------------------------------
    # KETERANGAN
    # --------------------------------------------------------

    movement.reason = (
        reason
    )

    movement.notes = (
        notes
    )

    # ========================================================
    # UPDATE ASSET
    #
    # Karena movement yang dikoreksi adalah movement terakhir,
    # kondisi asset harus mengikuti nilai TO terbaru.
    # ========================================================

    asset.location = (
        to_location
    )

    asset.department = (
        to_department
    )

    asset.pic = (
        to_pic
    )

    # ========================================================
    # SIMPAN DATABASE
    # ========================================================

    try:

        db.session.commit()

        # ====================================================
        # HAPUS QR LAMA
        #
        # QR akan dibuat ulang ketika detail movement dibuka.
        # ====================================================

        qr_filename = (
            f"movement_{movement.id}.png"
        )

        qr_path = os.path.join(
            current_app.static_folder,
            "qrcodes",
            qr_filename
        )

        if os.path.exists(
            qr_path
        ):

            try:

                os.remove(
                    qr_path
                )

            except OSError:

                pass

        # ====================================================
        # SUCCESS
        # ====================================================

        flash(
            _("Movement %(number)s corrected successfully.")
            % {"number": movement.movement_no or "-"},
            "success"
        )

        return redirect(
            url_for(
                "main.asset_movement_detail",
                asset_id=asset.id,
                movement_id=movement.id
            )
        )

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            "ERROR KOREKSI MOVEMENT"
        )

        flash(
            _("An error occurred while saving the movement correction. "
              "Detail: %(error)s")
            % {"error": str(e)},
            "danger"
        )

        return render_template(
            "asset/movement_correct.html",
            asset=asset,
            movement=movement,
            locations=locations,
            departments=departments,
            correct_from_location=correct_from_location,
            correct_from_department=correct_from_department,
            correct_from_pic=correct_from_pic,
        )

# ============================================================
# CATEGORY
# ============================================================


