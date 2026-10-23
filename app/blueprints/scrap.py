"""
Pendataan scrap besi sisa modifikasi kontainer (Besi Biasa / Besi
Baja Ringan-LGS) per periode - periode dihitung dari tanggal
masing-masing entri, bukan master data terpisah.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_babel import gettext as _

from .. import db
from ..models import (
    ScrapRecord,
    ScrapPhoto,
    SCRAP_TYPE_CHOICES,
    SCRAP_UNIT_CHOICES,
    SCRAP_PHOTO_CATEGORY_CHOICES,
    SCRAP_PHOTO_CATEGORY_LAINNYA,
    SCRAP_PHOTO_CATEGORY_BEFORE,
    SCRAP_PHOTO_CATEGORY_AFTER,
    SCRAP_PHOTO_CATEGORY_TIMBANG,
)
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


def _photo_files(field_name):

    return [
        f for f in request.files.getlist(field_name)
        if f and f.filename
    ]


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

        photo_groups = (
            (SCRAP_PHOTO_CATEGORY_BEFORE, _photo_files("photos_before")),
            (SCRAP_PHOTO_CATEGORY_TIMBANG, _photo_files("photos_timbang")),
            (SCRAP_PHOTO_CATEGORY_AFTER, _photo_files("photos_after")),
        )

        if any(not files for _category, files in photo_groups):

            flash(
                _("Before, Weighing Process, and After photos are all required."),
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
        db.session.flush()

        try:

            for category, files in photo_groups:
                for photo_file in files:

                    filename = save_scrap_photo(photo_file)

                    db.session.add(
                        ScrapPhoto(
                            scrap_record_id=record.id,
                            filename=filename,
                            category=category,
                            photo_date=recorded_date,
                        )
                    )

        except ValueError as exc:

            db.session.rollback()

            flash(str(exc), "danger")

            return render_template("scrap/add.html")

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
# DOKUMENTASI FOTO (before/after/proses timbang, dst) - tampilannya
# dikelompokkan jadi "folder" per tanggal/periode (bukan per
# kategori), supaya mudah ditelusuri berdasarkan kapan foto itu
# diambil.
# ============================================================


def _photo_effective_date(photo):
    """
    Tanggal "folder" untuk satu foto - pakai photo_date kalau diisi,
    kalau tidak ikut tanggal ScrapRecord yang terkait (kalau ada),
    kalau keduanya kosong masuk folder "Tanpa Tanggal" (None).
    """

    if photo.photo_date:
        return photo.photo_date

    if photo.scrap_record:
        return photo.scrap_record.recorded_date

    return None


def _group_photos_by_date(photos):

    groups = {}

    for photo in photos:

        key = _photo_effective_date(photo)
        groups.setdefault(key, []).append(photo)

    # Folder dengan tanggal diurutkan terbaru dulu; "Tanpa Tanggal"
    # (key None) selalu ditaruh paling akhir.
    dated = sorted(
        (item for item in groups.items() if item[0] is not None),
        key=lambda item: item[0],
        reverse=True,
    )

    undated = [
        item for item in groups.items() if item[0] is None
    ]

    return dated + undated


@main.route("/scrap/photos")
@requires_permission("scrap", "read")
def scrap_photos():

    selected_date_raw = request.args.get("date")

    all_photos = ScrapPhoto.query.all()

    records = (
        ScrapRecord.query
        .order_by(ScrapRecord.recorded_date.desc())
        .all()
    )

    if selected_date_raw is not None:

        selected_date = (
            parse_date(selected_date_raw)
            if selected_date_raw != "none"
            else None
        )

        photos = sorted(
            [
                p for p in all_photos
                if _photo_effective_date(p) == selected_date
            ],
            key=lambda p: p.created_at,
            reverse=True,
        )

        return render_template(
            "scrap/photos.html",
            view="folder",
            selected_date=selected_date,
            selected_date_raw=selected_date_raw,
            photos=photos,
            records=records,
            category_choices=SCRAP_PHOTO_CATEGORY_CHOICES,
        )

    folders = []

    for photo_date, photos_in_date in _group_photos_by_date(all_photos):

        folders.append({
            "date": photo_date,
            "date_raw": (
                photo_date.strftime("%Y-%m-%d")
                if photo_date else "none"
            ),
            "count": len(photos_in_date),
            "cover": photos_in_date[0] if photos_in_date else None,
        })

    return render_template(
        "scrap/photos.html",
        view="folders",
        folders=folders,
        records=records,
        category_choices=SCRAP_PHOTO_CATEGORY_CHOICES,
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

    category = request.form.get("category")
    valid_categories = {key for key, _label in SCRAP_PHOTO_CATEGORY_CHOICES}

    if category not in valid_categories:
        category = SCRAP_PHOTO_CATEGORY_LAINNYA

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
                    category=category,
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

    if photo_date:
        return redirect(
            url_for("main.scrap_photos", date=photo_date.strftime("%Y-%m-%d"))
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

    effective_date = _photo_effective_date(photo)

    db.session.delete(photo)
    db.session.commit()

    log_action("delete", "ScrapPhoto", entity_label=photo.label or "-")

    flash(
        _("Photo deleted successfully."),
        "success",
    )

    return redirect(
        url_for(
            "main.scrap_photos",
            date=(
                effective_date.strftime("%Y-%m-%d")
                if effective_date else "none"
            ),
        )
    )
