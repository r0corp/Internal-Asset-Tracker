"""
Catatan servis/perawatan kendaraan (field_template "kendaraan") -
satu baris bebas per tanggal, bukan grid bulanan tetap seperti sheet
Excel asalnya, supaya jumlah catatan per kendaraan per bulan tidak
dibatasi kolom.
"""

from flask import render_template, request, redirect, url_for, flash, abort
from flask_babel import gettext as _

from .. import db
from ..models import Asset, Category, VehicleServiceRecord
from ..auth import requires_permission
from flask_login import current_user

from . import main
from .helpers import parse_date, log_action


def _get_vehicle_or_404(asset_id):

    asset = Asset.query.get_or_404(asset_id)

    category = Category.query.filter_by(name=asset.category).first()

    if not category or category.field_template != "kendaraan":
        abort(404)

    return asset


@main.route(
    "/assets/<int:asset_id>/service",
    methods=["GET", "POST"],
)
@requires_permission("asset", "edit")
def vehicle_service_list(asset_id):

    asset = _get_vehicle_or_404(asset_id)

    if request.method == "POST":

        service_date = parse_date(
            request.form.get("service_date")
        )

        description = (
            request.form.get("description", "").strip()
        )

        cost_raw = (
            request.form.get("cost", "").strip()
        )

        try:
            cost = float(cost_raw) if cost_raw else None
        except ValueError:
            cost = None

        if not service_date:

            flash(
                _("Date is required."),
                "danger",
            )

            return redirect(
                url_for("main.vehicle_service_list", asset_id=asset.id)
            )

        if not description:

            flash(
                _("Service/Maintenance description is required."),
                "danger",
            )

            return redirect(
                url_for("main.vehicle_service_list", asset_id=asset.id)
            )

        record = VehicleServiceRecord(
            asset_id=asset.id,
            service_date=service_date,
            description=description,
            cost=cost,
            notes=(
                request.form.get("notes", "").strip() or None
            ),
            recorded_by=current_user.username,
        )

        db.session.add(record)
        db.session.commit()

        log_action(
            "create",
            "VehicleService",
            entity_label=f"{asset.asset_tag} {service_date.strftime('%Y-%m-%d')}",
        )

        flash(
            _("Service record added successfully."),
            "success",
        )

        return redirect(
            url_for("main.vehicle_service_list", asset_id=asset.id)
        )

    records = (
        VehicleServiceRecord.query
        .filter_by(asset_id=asset.id)
        .order_by(VehicleServiceRecord.service_date.desc())
        .all()
    )

    return render_template(
        "asset/vehicle_service.html",
        asset=asset,
        records=records,
    )


@main.route(
    "/assets/<int:asset_id>/service/<int:record_id>/delete",
    methods=["POST"],
)
@requires_permission("asset", "edit")
def delete_vehicle_service(asset_id, record_id):

    asset = _get_vehicle_or_404(asset_id)

    record = VehicleServiceRecord.query.filter_by(
        id=record_id,
        asset_id=asset.id,
    ).first_or_404()

    deleted_label = f"{asset.asset_tag} {record.service_date.strftime('%Y-%m-%d')}"

    db.session.delete(record)
    db.session.commit()

    log_action("delete", "VehicleService", entity_label=deleted_label)

    flash(
        _("Service record deleted successfully."),
        "success",
    )

    return redirect(
        url_for("main.vehicle_service_list", asset_id=asset.id)
    )
