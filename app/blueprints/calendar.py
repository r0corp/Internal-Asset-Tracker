"""
Kalender mini di navbar - isinya agenda jatuh tempo kendaraan
(Pajak STNK, Asuransi, KIR) dalam rentang tanggal yang diminta,
sumbernya sama dengan tiga widget "akan habis" di Dashboard
(lihat overview.py). Belum ada jenis agenda lain.
"""

from flask import jsonify, request
from flask_login import login_required

from ..models import Asset

from . import main
from .helpers import apply_asset_category_restriction


def _parse_date(value):

    from datetime import datetime

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@main.route("/calendar/events")
@login_required
def calendar_events():

    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    events = []

    def _add(assets, date_field, color, label):

        for asset in assets:

            due = getattr(asset, date_field)

            if not due:
                continue

            if start and due < start:
                continue

            if end and due >= end:
                continue

            events.append({
                "start": due.isoformat(),
                "title": f"{label}: {asset.asset_name}",
                "color": color,
                "url": f"/assets/{asset.id}",
                "extendedProps": {
                    "detail": asset.plat_nomor or "",
                },
            })

    base_query = apply_asset_category_restriction(
        Asset.query
    )

    _add(
        base_query.filter(Asset.masa_pajak.isnot(None)).all(),
        "masa_pajak",
        "#fd7e14",
        "STNK",
    )

    _add(
        base_query.filter(Asset.masa_asuransi.isnot(None)).all(),
        "masa_asuransi",
        "#0d6efd",
        "Asuransi",
    )

    _add(
        base_query.filter(Asset.masa_kir.isnot(None)).all(),
        "masa_kir",
        "#6f42c1",
        "KIR",
    )

    return jsonify(events)
