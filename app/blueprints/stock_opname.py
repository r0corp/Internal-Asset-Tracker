"""
Stok opname bulanan - Sadam cuma input Stok Keluar per item tiap
bulan, Stok Awal & Stok Akhir dihitung otomatis (mengikuti alur form
kertas "DATA STOK ALAT TULIS KANTOR"). Setelah disimpan, stok_akhir
ikut disalin ke Asset.stock_quantity supaya Asset List & alert stok
rendah di Dashboard tetap sinkron dengan hasil opname terakhir.

ATK dan Pantry masing-masing punya data & "pengajuan" (kebutuhan
purchase requisition) sendiri-sendiri - TIDAK digabung jadi satu -
jadi URL-nya dibedakan lewat <tipe> ("atk" atau "pantry"), bukan satu
halaman bersama untuk semua kategori stok.
"""

from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash, abort
from flask_babel import gettext as _
from flask_login import current_user

from .. import db
from ..models import (
    Asset,
    Category,
    StockOpnameRecord,
    FIELD_TEMPLATE_ATK,
    FIELD_TEMPLATE_PANTRY,
    FIELD_TEMPLATE_SHOWCASE,
)
from ..auth import requires_permission

from . import main
from .helpers import apply_asset_category_restriction, log_action

# Kategori yang sudah punya halaman Stok Opname sendiri. Tambah di
# sini kalau nanti kategori stok lain (Tools Pantry/Gudang Event)
# juga perlu - jangan dibuat 1 halaman gabungan untuk semua.
STOCK_OPNAME_TEMPLATES = {
    "atk": (FIELD_TEMPLATE_ATK, _("Office Stationery (ATK)")),
    "pantry": (FIELD_TEMPLATE_PANTRY, _("Pantry")),
    "showcase": (FIELD_TEMPLATE_SHOWCASE, _("Showcase")),
}

# Kategori yang pengajuan belanja bulanannya dibatasi anggaran tetap
# (Rp) - Winny mengisi "Qty Dibeli" per item, sistem menghitung Total
# Harga (qty x Asset.purchase_price) dan memperingatkan kalau Grand
# Total melebihi angka ini, supaya item bisa diganti/disesuaikan
# sebelum diajukan. Kategori yang tidak ada di sini tidak menampilkan
# kolom pengajuan belanja ini sama sekali (tetap stok opname biasa).
STOCK_OPNAME_BUDGET = {
    "showcase": 500000,
}


def _resolve_tipe(tipe):

    info = STOCK_OPNAME_TEMPLATES.get(tipe)

    if not info:
        abort(404)

    return info


def _month_start(value):
    """
    "YYYY-MM" (dari <input type="month">) -> date tanggal 1 bulan itu.
    None kalau formatnya tidak valid.
    """

    try:
        parsed = datetime.strptime((value or "").strip(), "%Y-%m")
    except ValueError:
        return None

    return date(parsed.year, parsed.month, 1)


def _stock_assets_query(field_template):

    category_names = [
        c.name
        for c in Category.query.filter_by(
            field_template=field_template
        ).all()
    ]

    query = apply_asset_category_restriction(
        Asset.query.filter(Asset.category.in_(category_names))
    )

    return query.all()


def _sort_key(asset, sequence_map):

    sequence = sequence_map.get(asset.category)

    return (
        sequence if sequence is not None else 999999,
        asset.category or "",
    )


def _existing_record(asset_id, period):

    return StockOpnameRecord.query.filter_by(
        asset_id=asset_id,
        period=period,
    ).first()


def _stok_awal_for(asset_id, period, fallback_quantity):
    """
    Stok Akhir dari opname bulan sebelumnya (period < period ini,
    paling baru) - kalau belum pernah ada opname untuk asset ini,
    pakai Asset.stock_quantity saat ini sebagai titik awal.

    Kalau period ini SENDIRI sudah pernah disimpan sebelumnya (mis.
    Sadam membuka ulang halaman Input untuk mengoreksi bulan yang
    sama), pakai stok_awal yang sudah tersimpan itu apa adanya -
    supaya tidak ikut berubah gara-gara Asset.stock_quantity sudah
    ditimpa oleh penyimpanan period ini sebelumnya.
    """

    current = _existing_record(asset_id, period)

    if current:
        return current.stok_awal

    previous = (
        StockOpnameRecord.query
        .filter(
            StockOpnameRecord.asset_id == asset_id,
            StockOpnameRecord.period < period,
        )
        .order_by(StockOpnameRecord.period.desc())
        .first()
    )

    if previous:
        return previous.stok_akhir

    return fallback_quantity or 0

# ============================================================
# INPUT STOK OPNAME
# ============================================================


@main.route(
    "/stock-opname/<tipe>",
    methods=["GET", "POST"],
)
@requires_permission("stock_opname", "create")
def stock_opname_input(tipe):

    field_template, tipe_label = _resolve_tipe(tipe)
    budget = STOCK_OPNAME_BUDGET.get(tipe)

    categories = Category.query.filter_by(
        field_template=field_template
    ).all()

    sequence_map = {
        c.name: c.stock_sequence
        for c in categories
    }

    assets = _stock_assets_query(field_template)
    assets.sort(key=lambda a: _sort_key(a, sequence_map))

    if request.method == "POST":

        period = _month_start(request.form.get("period"))

        if not period:

            flash(
                _("Invalid period."),
                "danger",
            )

            return redirect(
                url_for("main.stock_opname_input", tipe=tipe)
            )

        rows = []
        errors = []

        for asset in assets:

            raw_keluar = request.form.get(
                f"stok_keluar_{asset.id}",
                ""
            ).strip()

            try:
                stok_keluar = int(raw_keluar) if raw_keluar else 0
            except ValueError:
                stok_keluar = None

            if stok_keluar is None or stok_keluar < 0:

                errors.append(
                    _("%(name)s: invalid value.")
                    % {"name": asset.asset_name}
                )

                continue

            stok_awal = _stok_awal_for(
                asset.id,
                period,
                asset.stock_quantity,
            )

            if stok_keluar > stok_awal:

                errors.append(
                    _(
                        "%(name)s: Stock Out (%(keluar)s) exceeds "
                        "Initial Stock (%(awal)s)."
                    )
                    % {
                        "name": asset.asset_name,
                        "keluar": stok_keluar,
                        "awal": stok_awal,
                    }
                )

                continue

            qty_beli = 0

            if budget:

                raw_qty_beli = request.form.get(
                    f"qty_beli_{asset.id}",
                    ""
                ).strip()

                try:
                    qty_beli = int(raw_qty_beli) if raw_qty_beli else 0
                except ValueError:
                    qty_beli = 0

                if qty_beli < 0:
                    qty_beli = 0

            rows.append(
                (asset, stok_awal, stok_keluar, stok_awal - stok_keluar, qty_beli)
            )

        if errors:

            for message in errors[:10]:
                flash(message, "danger")

            if len(errors) > 10:
                flash(
                    _("...and %(count)s more errors.")
                    % {"count": len(errors) - 10},
                    "danger",
                )

            return redirect(
                url_for("main.stock_opname_input", tipe=tipe)
            )

        for asset, stok_awal, stok_keluar, stok_akhir, qty_beli in rows:

            record = StockOpnameRecord.query.filter_by(
                asset_id=asset.id,
                period=period,
            ).first()

            if not record:

                record = StockOpnameRecord(
                    asset_id=asset.id,
                    period=period,
                )

                db.session.add(record)

            record.stok_awal = stok_awal
            record.stok_keluar = stok_keluar
            record.stok_akhir = stok_akhir
            record.qty_beli = qty_beli
            record.recorded_by = current_user.username

            asset.stock_quantity = stok_akhir

        db.session.commit()

        log_action(
            "create",
            "StockOpname",
            entity_label=f"{tipe_label} {period.strftime('%Y-%m')}",
            description=f"{len(rows)} item",
        )

        flash(
            _("Stock opname for %(period)s saved successfully.")
            % {"period": period.strftime("%Y-%m")},
            "success",
        )

        return redirect(
            url_for(
                "main.stock_opname_history",
                tipe=tipe,
                period=period.strftime("%Y-%m"),
            )
        )

    today = date.today()

    default_period = (
        _month_start(request.args.get("period"))
        or date(today.year, today.month, 1)
    )

    rows = []

    for asset in assets:

        existing = _existing_record(asset.id, default_period)

        stok_awal = (
            existing.stok_awal
            if existing
            else _stok_awal_for(asset.id, default_period, asset.stock_quantity)
        )

        rows.append(
            (
                asset,
                stok_awal,
                existing.stok_keluar if existing else 0,
                (existing.qty_beli if existing and existing.qty_beli else 0),
            )
        )

    return render_template(
        "stock_opname/input.html",
        rows=rows,
        default_period=default_period.strftime("%Y-%m"),
        tipe=tipe,
        tipe_label=tipe_label,
        budget=budget,
    )

# ============================================================
# RIWAYAT STOK OPNAME
# ============================================================


@main.route("/stock-opname/<tipe>/history")
@requires_permission("stock_opname", "read")
def stock_opname_history(tipe):

    field_template, tipe_label = _resolve_tipe(tipe)
    budget = STOCK_OPNAME_BUDGET.get(tipe)

    categories = Category.query.filter_by(
        field_template=field_template
    ).all()

    sequence_map = {
        c.name: c.stock_sequence
        for c in categories
    }

    category_names = list(sequence_map.keys())

    allowed_asset_ids = [
        a.id
        for a in apply_asset_category_restriction(
            Asset.query.filter(Asset.category.in_(category_names))
        ).all()
    ]

    available_periods = [
        row[0]
        for row in (
            db.session.query(StockOpnameRecord.period)
            .filter(StockOpnameRecord.asset_id.in_(allowed_asset_ids))
            .distinct()
            .order_by(StockOpnameRecord.period.desc())
            .all()
        )
    ]

    selected_period = _month_start(request.args.get("period"))

    if not selected_period and available_periods:
        selected_period = available_periods[0]

    records = []

    if selected_period:

        records = (
            StockOpnameRecord.query
            .filter(
                StockOpnameRecord.period == selected_period,
                StockOpnameRecord.asset_id.in_(allowed_asset_ids),
            )
            .join(Asset)
            .all()
        )

        records.sort(
            key=lambda r: _sort_key(r.asset, sequence_map)
        )

    return render_template(
        "stock_opname/history.html",
        available_periods=available_periods,
        selected_period=selected_period,
        records=records,
        tipe=tipe,
        tipe_label=tipe_label,
        budget=budget,
    )
