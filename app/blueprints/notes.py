"""
Sticky notes pribadi (panel dari ikon di navbar). Hanya pemilik yang
bisa melihat - tidak ada hubungannya dengan data asset, murni catatan
pribadi tiap user.
"""

from flask import jsonify, request, abort
from flask_login import current_user, login_required

from .. import db
from ..models import StickyNote

from . import main

COLORS = ("yellow", "green", "blue", "pink", "purple")
MAX_NOTES = 100
MAX_LENGTH = 5000


def _own(note_id):

    note = db.session.get(StickyNote, note_id)

    if note is None or note.user_id != current_user.id:
        abort(404)

    return note


def _ordered():

    return (
        StickyNote.query
        .filter_by(user_id=current_user.id)
        .order_by(StickyNote.pinned.desc(), StickyNote.updated_at.desc())
        .all()
    )


@main.route("/notes")
@login_required
def notes_index():

    return jsonify([n.as_dict() for n in _ordered()])


@main.route("/notes", methods=["POST"])
@login_required
def notes_create():

    if StickyNote.query.filter_by(user_id=current_user.id).count() >= MAX_NOTES:
        return jsonify(error="Maksimal 100 catatan."), 400

    data = request.get_json(silent=True) or {}
    color = data.get("color")

    note = StickyNote(
        user_id=current_user.id,
        content="",
        color=color if color in COLORS else "yellow",
    )

    db.session.add(note)
    db.session.commit()

    return jsonify(note.as_dict()), 201


@main.route("/notes/<int:note_id>", methods=["POST"])
@login_required
def notes_update(note_id):

    note = _own(note_id)
    data = request.get_json(silent=True) or {}

    if "content" in data:
        note.content = str(data["content"])[:MAX_LENGTH]

    if data.get("color") in COLORS:
        note.color = data["color"]

    if "pinned" in data:
        note.pinned = bool(data["pinned"])

    db.session.commit()

    return jsonify(note.as_dict())


@main.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def notes_delete(note_id):

    note = _own(note_id)

    db.session.delete(note)
    db.session.commit()

    return jsonify(ok=True)
