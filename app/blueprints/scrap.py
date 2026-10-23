"""
Pendataan scrap besi sisa modifikasi kontainer (Besi Biasa / Besi
Baja Ringan-LGS) per periode - periode dihitung dari tanggal
masing-masing entri, bukan master data terpisah.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_babel import gettext as _

from .. import db
from ..models import ScrapRecord, ScrapPhoto, SCRAP_TYPE_CHOICES, SCRAP_UNIT_CHOICES
from ..auth import requires_permission

from . import main
from .helpers import parse_date, log_action, save_scrap_photo, delete_scrap_photo


def _parse_scrap_type(value):

    valid_keys = {key for key, _label in SCRAP_TYPE_CHOICES}

    if value in valid_keys:
        return value

    return SCRAP_TYPE_CHOICES[0][0]


def _parse_unit(value):

    if value in SCRAP_UNIT_CHOICES:
        return value

    return SCRAP_UNIT_CHOICES[0]


@main.route("/scrap")
@requires_permission("scrap", "read")
def scrap_list():

    date_from = (
        request.args.get("date_from", "") or ""
    ).strip()

    date_to = (
        request.args.get("date_to", "") or ""
    ).strip()

    query = ScrapRecord.query

    start_date = parse_date(date_from)
    end_date = parse_date(date_to)

    if start_date:
        query = query.filter(
            ScrapRecord.recorded_date >= start_date
        )

    if end_date:
        query = query.filter(
            ScrapRecord.recorded_date <= end_date
        )

    items = (
        query
        .order_by(
            ScrapRecord.recorded_date.desc(),
            ScrapRecord.id.desc(),
        )
        .all()
    )

    # ========================================================
    # TOTAL PER JENIS (untuk rentang tanggal yang sedang difilter)
    # ========================================================

    totals_by_type = {}

    for key, label in SCRAP_TYPE_CHOICES:

        totals_by_type[key] = {
            "label": label,
            "kg": 0.0,
            "ton": 0.0,
        }

    for item in items:

        if item.scrap_type in totals_by_type:
            totals_by_type[item.scrap_type][item.unit] = (
                totals_by_type[item.scrap_type].get(item.unit, 0.0)
                + item.quantity
            )

    return render_template(
        "scrap/list.html",
        items=items,
        date_from=date_from,
        date_to=date_to,
        totals_by_type=totals_by_type,
    )

# ============================================================
# ADD SCRAP RECORD
# ============================================================


@main.route(
    "/scrap/add",
    methods=["GET", "POST"],
)
@requires_permission("scrap", "create")
def add_scrap():

    if request.method == "POST":

        quantity_raw = request.form.get("quantity", "").strip()
        recorded_date = parse_date(request.form.get("recorded_date"))

        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError):
            quantity = None

        if not recorded_date:

            flash(
                _("Date is required."),
                "danger",
            )

            return render_template("scrap/add.html")

        if quantity is None or quantity <= 0:

            flash(
                _("Invalid quantity."),
                "danger",
            )

            return render_template("scrap/add.html")

        record = ScrapRecord(
            scrap_type=_parse_scrap_type(
                request.form.get("scrap_type")
            ),
            quantity=quantity,
            unit=_parse_unit(
                request.form.get("unit")
            ),
            recorded_date=recorded_date,
            notes=(
                request.form.get("notes", "").strip() or None
            ),
        )

        db.session.add(record)
        db.session.commit()

        log_action(
            "create",
            "Scrap",
            entity_label=f"{record.scrap_type_label()} {record.quantity}{record.unit}",
        )

        flash(
            _("Scrap record added successfully."),
            "success",
        )

        return redirect(
            url_for("main.scrap_list")
        )

    return render_template("scrap/add.html")

# ============================================================
# EDIT SCRAP RECORD
# ============================================================


@main.route(
    "/scrap/<int:record_id>/edit",
    methods=["GET", "POST"],
)
@requires_permission("scrap", "edit")
def edit_scrap(record_id):

    record = ScrapRecord.query.get_or_404(record_id)

    if request.method == "POST":

        quantity_raw = request.form.get("quantity", "").strip()
        recorded_date = parse_date(request.form.get("recorded_date"))

        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError):
            quantity = None

        if not recorded_date:

            flash(
                _("Date is required."),
                "danger",
            )

            return render_template(
                "scrap/edit.html",
                record=record,
            )

        if quantity is None or quantity <= 0:

            flash(
                _("Invalid quantity."),
                "danger",
            )

            return render_template(
                "scrap/edit.html",
                record=record,
            )

        record.scrap_type = _parse_scrap_type(
            request.form.get("scrap_type")
        )
        record.quantity = quantity
        record.unit = _parse_unit(
            request.form.get("unit")
        )
        record.recorded_date = recorded_date
        record.notes = (
            request.form.get("notes", "").strip() or None
        )

        db.session.commit()

        log_action(
            "update",
            "Scrap",
            entity_label=f"{record.scrap_type_label()} {record.quantity}{record.unit}",
        )

        flash(
            _("Scrap record updated successfully."),
            "success",
        )

        return redirect(
            url_for("main.scrap_list")
        )

    return render_template(
        "scrap/edit.html",
        record=record,
    )

# ============================================================
# DELETE SCRAP RECORD
# ============================================================


@main.route(
    "/scrap/<int:record_id>/delete",
    methods=["POST"],
)
@requires_permission("scrap", "delete")
def delete_scrap(record_id):

    record = ScrapRecord.query.get_or_404(record_id)

    deleted_label = f"{record.scrap_type_label()} {record.quantity}{record.unit}"

    db.session.delete(record)
    db.session.commit()

    log_action("delete", "Scrap", entity_label=deleted_label)

    flash(
        _("Scrap record deleted successfully."),
        "success",
    )

    return redirect(
        url_for("main.scrap_list")
    )

# ============================================================
# DOKUMENTASI FOTO (before/after/proses timbang, dst)
# ============================================================


@main.route("/scrap/photos")
@requires_permission("scrap", "read")
def scrap_photos():

    photos = (
        ScrapPhoto.query
        .order_by(ScrapPhoto.created_at.desc())
        .all()
    )

    records = (
        ScrapRecord.query
        .order_by(ScrapRecord.recorded_date.desc())
        .all()
    )

    return render_template(
        "scrap/photos.html",
        photos=photos,
        records=records,
    )


@main.route(
    "/scrap/photos/upload",
    methods=["POST"],
)
@requires_permission("scrap", "create")
def scrap_photos_upload():

    photo_files = [
        f for f in request.files.getlist("photos")
        if f and f.filename
    ]

    if not photo_files:

        flash(
            _("No photo file was sent."),
            "danger",
        )

        return redirect(
            url_for("main.scrap_photos")
        )

    label = (
        request.form.get("label", "") or ""
    ).strip() or None

    photo_date = parse_date(
        request.form.get("photo_date")
    )

    scrap_record_id = request.form.get(
        "scrap_record_id",
        type=int,
    )

    if scrap_record_id:
        scrap_record_id = (
            scrap_record_id
            if ScrapRecord.query.get(scrap_record_id)
            else None
        )

    try:

        for photo_file in photo_files:

            filename = save_scrap_photo(photo_file)

            db.session.add(
                ScrapPhoto(
                    scrap_record_id=scrap_record_id,
                    filename=filename,
                    label=label,
                    photo_date=photo_date,
                )
            )

        db.session.commit()

    except ValueError as exc:

        db.session.rollback()

        flash(str(exc), "danger")

        return redirect(
            url_for("main.scrap_photos")
        )

    log_action(
        "create",
        "ScrapPhoto",
        entity_label=label or _("Scrap documentation photo"),
        description=f"{len(photo_files)} {_('photo(s)')}",
    )

    flash(
        _("Photo(s) uploaded successfully."),
        "success",
    )

    return redirect(
        url_for("main.scrap_photos")
    )


@main.route(
    "/scrap/photos/<int:photo_id>/delete",
    methods=["POST"],
)
@requires_permission("scrap", "delete")
def scrap_photos_delete(photo_id):

    photo = ScrapPhoto.query.get_or_404(photo_id)

    delete_scrap_photo(photo.filename)

    db.session.delete(photo)
    db.session.commit()

    log_action("delete", "ScrapPhoto", entity_label=photo.label or "-")

    flash(
        _("Photo deleted successfully."),
        "success",
    )

    return redirect(
        url_for("main.scrap_photos")
    )
