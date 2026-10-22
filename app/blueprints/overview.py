"""
Halaman ringkasan: landing page asset (index) dan dashboard analitik.
"""

from datetime import date, timedelta

from flask import render_template

from .. import db
from ..models import Asset, Category, Location, Department, Vendor, AssetMovement

from . import main
from .helpers import apply_asset_category_restriction

@main.route("/")
def index():

    # ========================================================
    # TOTAL ASSET
    # ========================================================

    total_assets = apply_asset_category_restriction(Asset.query).count()

    # ========================================================
    # STATUS ASSET
    # ========================================================

    status_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.status,
                db.func.count(Asset.id)
            )
        )
        .group_by(Asset.status)
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    status_summary = []

    for status, count in status_rows:

        status_summary.append({
            "status": status or "Tidak Ada Status",
            "count": count
        })

    # ========================================================
    # STATUS SUMMARY (dari status_rows di atas - tidak perlu
    # query .count() terpisah lagi per status)
    # ========================================================

    status_counts = dict(status_rows)

    active_assets = status_counts.get("Active", 0)
    maintenance_assets = status_counts.get("Maintenance", 0)
    inactive_assets = status_counts.get("Inactive", 0)
    lost_assets = status_counts.get("Lost", 0)
    retired_assets = status_counts.get("Retired", 0)

    # ========================================================
    # TOTAL NILAI ASSET
    # ========================================================

    total_value = (
        apply_asset_category_restriction(
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        Asset.purchase_price
                    ),
                    0
                )
            )
        )
        .scalar()
        or 0
    )

    # ========================================================
    # CATEGORY
    # ========================================================

    category_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.category,
                db.func.count(Asset.id)
            )
        )
        .group_by(Asset.category)
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    category_summary = []

    for category, count in category_rows:

        category_summary.append({
            "category": category or "Tanpa Kategori",
            "count": count
        })

    # ========================================================
    # LOCATION
    # ========================================================

    location_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.location,
                db.func.count(Asset.id)
            )
        )
        .group_by(Asset.location)
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    location_summary = []

    for location, count in location_rows:

        location_summary.append({
            "location": location or "Tanpa Lokasi",
            "count": count
        })

    # ========================================================
    # DEPARTMENT
    # ========================================================

    department_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.department,
                db.func.count(Asset.id)
            )
        )
        .group_by(Asset.department)
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    department_summary = []

    for department, count in department_rows:

        department_summary.append({
            "department": (
                department
                or "Tanpa Department"
            ),
            "count": count
        })

    # ========================================================
    # DATA CHART
    # ========================================================

    category_labels = [
        item["category"]
        for item in category_summary
    ]

    category_values = [
        item["count"]
        for item in category_summary
    ]

    department_labels = [
        item["department"]
        for item in department_summary
    ]

    department_values = [
        item["count"]
        for item in department_summary
    ]

    location_labels = [
        item["location"]
        for item in location_summary
    ]

    location_values = [
        item["count"]
        for item in location_summary
    ]

    # ========================================================
    # MASTER DATA
    # ========================================================

    total_categories = (
        Category.query.count()
    )

    total_locations = (
        Location.query.count()
    )

    total_departments = (
        Department.query.count()
    )

    total_vendors = (
        Vendor.query.count()
    )

    # ========================================================
    # ASSET TERBARU
    # ========================================================

    recent_assets = (
        apply_asset_category_restriction(Asset.query)
        .order_by(
            Asset.created_at.desc(),
            Asset.id.desc()
        )
        .limit(10)
        .all()
    )

    # ========================================================
    # RENDER DASHBOARD
    # ========================================================

    return render_template(

        "index.html",

        # ----------------------------------------------------
        # ASSET
        # ----------------------------------------------------

        total_assets=total_assets,

        total_value=total_value,


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        active_assets=active_assets,

        maintenance_assets=maintenance_assets,

        inactive_assets=inactive_assets,

        lost_assets=lost_assets,

        retired_assets=retired_assets,


        # ----------------------------------------------------
        # MASTER DATA
        # ----------------------------------------------------

        total_categories=total_categories,

        total_locations=total_locations,

        total_departments=total_departments,

        total_vendors=total_vendors,


        # ----------------------------------------------------
        # CHART DATA
        # ----------------------------------------------------

        status_summary=status_summary,

        category_summary=category_summary,

        location_summary=location_summary,

        department_summary=department_summary,


        # ----------------------------------------------------
        # RECENT ASSET
        # ----------------------------------------------------

        recent_assets=recent_assets,

    )

@main.route("/dashboard")
def dashboard():

    # ========================================================
    # TOTAL ASSET
    # ========================================================

    total_assets = (
        apply_asset_category_restriction(Asset.query).count()
    )

    # ========================================================
    # TOTAL NILAI ASSET
    # ========================================================

    total_value = (
        apply_asset_category_restriction(
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        Asset.purchase_price
                    ),
                    0
                )
            )
        )
        .scalar()
        or 0
    )

    # ========================================================
    # STATUS ASSET
    # ========================================================

    status_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.status,
                db.func.count(Asset.id)
            )
        )
        .group_by(
            Asset.status
        )
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    status_summary = []

    for status, count in status_rows:

        status_summary.append({
            "status": (
                status
                or "Tidak Ada Status"
            ),
            "count": count
        })

    # ========================================================
    # CATEGORY
    # ========================================================

    category_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.category,
                db.func.count(Asset.id)
            )
        )
        .group_by(
            Asset.category
        )
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    category_summary = []

    for category, count in category_rows:

        category_summary.append({
            "category": (
                category
                or "Tanpa Kategori"
            ),
            "count": count
        })

    # ========================================================
    # LOCATION
    # ========================================================

    location_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.location,
                db.func.count(Asset.id)
            )
        )
        .group_by(
            Asset.location
        )
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    location_summary = []

    for location, count in location_rows:

        location_summary.append({
            "location": (
                location
                or "Tanpa Lokasi"
            ),
            "count": count
        })

    # ========================================================
    # DEPARTMENT
    # ========================================================

    department_rows = (
        apply_asset_category_restriction(
            db.session.query(
                Asset.department,
                db.func.count(Asset.id)
            )
        )
        .group_by(
            Asset.department
        )
        .order_by(
            db.func.count(Asset.id).desc()
        )
        .all()
    )

    department_summary = []

    for department, count in department_rows:

        department_summary.append({
            "department": (
                department
                or "Tanpa Department"
            ),
            "count": count
        })

    # ========================================================
    # ASSET TERBARU
    # ========================================================

    recent_assets = (
        apply_asset_category_restriction(Asset.query)
        .order_by(
            Asset.created_at.desc(),
            Asset.id.desc()
        )
        .limit(10)
        .all()
    )

    # ========================================================
    # MOVEMENT TERBARU
    # ========================================================

    recent_movements = (
        AssetMovement.query
        .order_by(
            AssetMovement.movement_date.desc(),
            AssetMovement.id.desc()
        )
        .limit(10)
        .all()
    )

    # ========================================================
    # MOVEMENT 12 BULAN TERAKHIR
    # ========================================================

    today = date.today()

    current_year = today.year

    current_month = today.month

    # --------------------------------------------------------
    # BATAS RENTANG 12 BULAN (bulan ini + 11 bulan sebelumnya) -
    # dipakai untuk SATU query GROUP BY per bulan di bawah, bukan
    # 12 query .count() terpisah di dalam loop seperti sebelumnya.
    # --------------------------------------------------------

    earliest_month_index = (
        current_year * 12
        + current_month
        - 1
        - 11
    )

    earliest_year = earliest_month_index // 12
    earliest_month = earliest_month_index % 12 + 1

    range_start = date(earliest_year, earliest_month, 1)

    if current_month == 12:
        range_end = date(current_year + 1, 1, 1)
    else:
        range_end = date(current_year, current_month + 1, 1)

    month_key = db.func.strftime(
        "%Y-%m",
        AssetMovement.movement_date,
    )

    monthly_counts = dict(
        db.session.query(
            month_key,
            db.func.count(AssetMovement.id),
        )
        .filter(
            AssetMovement.movement_date >= range_start,
            AssetMovement.movement_date < range_end,
        )
        .group_by(month_key)
        .all()
    )

    monthly_movement_summary = []

    for offset in range(
        11,
        -1,
        -1
    ):

        # ----------------------------------------------------
        # HITUNG INDEX BULAN
        # ----------------------------------------------------

        month_index = (
            current_year * 12
            + current_month
            - 1
            - offset
        )

        # ----------------------------------------------------
        # TAHUN DAN BULAN
        # ----------------------------------------------------

        year = (
            month_index // 12
        )

        month = (
            month_index % 12
            + 1
        )

        # ----------------------------------------------------
        # SIMPAN SUMMARY
        # ----------------------------------------------------

        monthly_movement_summary.append({
            "month": (
                f"{month:02d}-{year}"
            ),
            "count": monthly_counts.get(
                f"{year:04d}-{month:02d}",
                0,
            )
        })

    # ========================================================
    # TOTAL MOVEMENT
    # ========================================================

    total_movements = (
        AssetMovement.query.count()
    )

    # ========================================================
    # MOVEMENT BULAN INI
    # ========================================================

    current_month_start = date(
        today.year,
        today.month,
        1
    )

    if today.month == 12:

        next_month_start = date(
            today.year + 1,
            1,
            1
        )

    else:

        next_month_start = date(
            today.year,
            today.month + 1,
            1
        )

    monthly_movements = (
        AssetMovement.query
        .filter(
            AssetMovement.movement_date
            >= current_month_start,

            AssetMovement.movement_date
            < next_month_start
        )
        .count()
    )

    # ========================================================
    # ASSET DENGAN MOVEMENT TERBANYAK
    # ========================================================

    movement_by_asset = (
        db.session.query(
            AssetMovement.asset_id,
            db.func.count(
                AssetMovement.id
            ).label(
                "movement_count"
            )
        )
        .group_by(
            AssetMovement.asset_id
        )
        .order_by(
            db.func.count(
                AssetMovement.id
            ).desc()
        )
        .limit(10)
        .all()
    )

    top_moved_assets_by_id = {
        asset.id: asset
        for asset in apply_asset_category_restriction(
            Asset.query
        ).filter(
            Asset.id.in_(
                [row.asset_id for row in movement_by_asset]
            )
        ).all()
    }

    movement_asset_summary = [
        {
            "asset": top_moved_assets_by_id[row.asset_id],
            "count": row.movement_count,
        }
        for row in movement_by_asset
        if row.asset_id in top_moved_assets_by_id
    ]

    # ========================================================
    # ASURANSI KENDARAAN AKAN HABIS (<= 30 HARI, TERMASUK YANG
    # SUDAH LEWAT) - lihat Asset.masa_asuransi, khusus field_template
    # "kendaraan".
    # ========================================================

    insurance_cutoff = date.today() + timedelta(days=30)

    expiring_insurance_assets = (
        apply_asset_category_restriction(Asset.query)
        .filter(
            Asset.masa_asuransi.isnot(None),
            Asset.masa_asuransi <= insurance_cutoff,
        )
        .order_by(Asset.masa_asuransi.asc())
        .all()
    )

    # ========================================================
    # STOK ATK PERLU DIBELI (stock_quantity <= batas minimum
    # kategorinya) - hasil stok opname bulanan, dasar pengajuan
    # pembelian ulang (purchase requisition).
    # ========================================================

    atk_categories_with_threshold = (
        Category.query
        .filter(
            Category.field_template == "atk",
            Category.low_stock_threshold.isnot(None),
        )
        .all()
    )

    threshold_by_category_name = {
        c.name: c.low_stock_threshold
        for c in atk_categories_with_threshold
    }

    low_stock_atk_assets = []

    if threshold_by_category_name:

        candidates = (
            apply_asset_category_restriction(Asset.query)
            .filter(
                Asset.category.in_(threshold_by_category_name.keys()),
                Asset.stock_quantity.isnot(None),
            )
            .order_by(Asset.stock_quantity.asc())
            .all()
        )

        for a in candidates:
            threshold = threshold_by_category_name.get(a.category)
            if threshold is not None and a.stock_quantity <= threshold:
                low_stock_atk_assets.append(a)

    # ========================================================
    # RENDER DASHBOARD
    # ========================================================

    return render_template(
        "dashboard.html",

        today=date.today(),

        expiring_insurance_assets=expiring_insurance_assets,

        low_stock_atk_assets=low_stock_atk_assets,

        threshold_by_category_name=threshold_by_category_name,

        # ----------------------------------------------------
        # ASSET
        # ----------------------------------------------------

        total_assets=total_assets,

        total_value=total_value,


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status_summary=status_summary,


        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category_summary=category_summary,


        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        location_summary=location_summary,


        # ----------------------------------------------------
        # DEPARTMENT
        # ----------------------------------------------------

        department_summary=department_summary,


        # ----------------------------------------------------
        # RECENT ASSET
        # ----------------------------------------------------

        recent_assets=recent_assets,


        # ----------------------------------------------------
        # RECENT MOVEMENT
        # ----------------------------------------------------

        recent_movements=recent_movements,


        # ----------------------------------------------------
        # MOVEMENT 12 BULAN
        # ----------------------------------------------------

        monthly_movement_summary=(
            monthly_movement_summary
        ),


        # ----------------------------------------------------
        # MOVEMENT ANALYTICS
        # ----------------------------------------------------

        total_movements=total_movements,

        monthly_movements=monthly_movements,

        movement_asset_summary=(
            movement_asset_summary
        ),
    )

# ============================================================
# ADD ASSET MOVEMENT
# ============================================================


