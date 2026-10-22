import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

from flask import Flask, flash, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_babel import Babel, gettext as _, lazy_gettext as _l
from flask_compress import Compress
from sqlalchemy.orm import joinedload


db = SQLAlchemy()

migrate = Migrate()

login_manager = LoginManager()

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)

babel = Babel()

compress = Compress()


def get_locale():
    """
    Urutan penentuan bahasa: pilihan manual user (tersimpan di
    session lewat /language/<kode>) -> bahasa browser yang cocok
    -> default aplikasi (Inggris).
    """

    from flask import current_app

    languages = current_app.config["LANGUAGES"]

    chosen = session.get("language")

    if chosen in languages:
        return chosen

    return (
        request.accept_languages.best_match(languages.keys())
        or current_app.config["BABEL_DEFAULT_LOCALE"]
    )


def create_app():

    app = Flask(__name__)

    app.config.from_object("config.Config")

    db.init_app(app)

    migrate.init_app(app, db)

    login_manager.init_app(app)

    login_manager.login_view = "main.login"

    login_manager.login_message = _l(
        "Please log in to access this page."
    )

    login_manager.login_message_category = "warning"

    csrf.init_app(app)

    limiter.init_app(app)

    babel.init_app(app, locale_selector=get_locale)

    compress.init_app(app)

    from .blueprints import main

    app.register_blueprint(main)

    from . import models

    @app.errorhandler(413)
    def handle_file_too_large(error):

        flash(
            _("The uploaded file is too large (maximum 5 MB)."),
            "danger",
        )

        return redirect(
            request.referrer
            or url_for("main.dashboard")
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """
        Tanpa handler ini, token CSRF yang hilang/kedaluwarsa (mis.
        user mengisi form lama tanpa aktivitas lain di sesi itu)
        akan menampilkan halaman error mentah Flask ("Bad Request").
        Tangkap di sini supaya user diarahkan balik dengan pesan
        yang jelas - kalau sesinya memang sudah tidak valid lagi,
        require_login/enforce_session_security akan otomatis
        mengarahkan ke halaman login setelah redirect ini.
        """

        flash(
            _("Your session has expired. Please try again."),
            "warning",
        )

        return redirect(
            request.referrer
            or url_for("main.dashboard")
        )

    @login_manager.user_loader
    def load_user(user_id):

        return models.User.query.get(
            int(user_id)
        )

    @app.context_processor
    def inject_nav_menu():

        if not current_user.is_authenticated:
            return {"nav_menu": []}

        role = current_user.role

        top_items = (
            models.MenuItem.query
            .filter_by(
                parent_id=None,
                is_active=True,
            )
            .options(
                joinedload(models.MenuItem.children)
            )
            .order_by(
                models.MenuItem.order,
                models.MenuItem.id,
            )
            .all()
        )

        # Kalau role-nya dibatasi kategorinya, menu "Asset" (url "/")
        # dipecah jadi satu menu terpisah per kategori yang diizinkan
        # (misalnya ATK, Pantry, dst), masing-masing langsung menuju
        # Asset List yang sudah terfilter - bukan satu menu "Asset"
        # gabungan seperti role yang tidak dibatasi.
        role_obj = models.Role.query.filter_by(name=role).first()

        allowed_tipe_keys = (
            role_obj.allowed_category_templates()
            if role_obj and role_obj.restricts_categories()
            else None
        )

        nav_menu = []

        for item in top_items:

            if not item.is_visible_to(role):
                continue

            if allowed_tipe_keys is not None and item.url == "/":

                # Tidak dikelompokkan jadi dropdown "Asset" lagi - tiap
                # kategori yang diizinkan dapat header (judul) + garis
                # pemisah sendiri, lalu menu link kategori itu (dan
                # untuk ATK/Pantry, link Stok Opname menyusul di
                # bawahnya kalau role ini punya izin stock_opname).
                stock_opname_perm = (
                    role_obj.permission_for("stock_opname")
                    if role_obj else None
                )
                can_see_stock_opname = bool(
                    stock_opname_perm and stock_opname_perm.can_read
                )

                for key, label, icon in models.ASSET_TYPE_TAB_CHOICES:

                    if key not in allowed_tipe_keys:
                        continue

                    nav_menu.append({
                        "item": SimpleNamespace(
                            is_divider=False,
                            is_header=True,
                            label=label,
                            icon=None,
                            url=None,
                        ),
                        "children": [],
                    })

                    nav_menu.append({
                        "item": SimpleNamespace(
                            is_divider=True,
                            is_header=False,
                            label=None,
                            icon=None,
                            url=None,
                        ),
                        "children": [],
                    })

                    nav_menu.append({
                        "item": SimpleNamespace(
                            is_divider=False,
                            is_header=False,
                            label=label,
                            icon=icon,
                            url=f"/assets?tipe={key}",
                        ),
                        "children": [],
                    })

                    if key in ("atk", "pantry") and can_see_stock_opname:
                        nav_menu.append({
                            "item": SimpleNamespace(
                                is_divider=False,
                                is_header=False,
                                label=_("Stock Opname"),
                                icon="bi-clipboard-check",
                                url=f"/stock-opname/{key}",
                            ),
                            "children": [],
                        })

                continue

            children = [
                child
                for child in item.children
                if child.is_active
                and child.is_visible_to(role)
            ]

            nav_menu.append({
                "item": item,
                "children": children,
            })

        return {"nav_menu": nav_menu}

    @app.context_processor
    def inject_online_users():

        if (
            not current_user.is_authenticated
            or current_user.role != models.ROLE_ADMINISTRATOR
        ):
            return {"online_users": []}

        online_users = sorted(
            (
                user
                for user in models.User.query.all()
                if user.id != current_user.id
                and user.is_online
            ),
            key=lambda user: user.full_name,
        )

        return {"online_users": online_users}

    @app.context_processor
    def inject_app_setting():

        from .blueprints.app_settings import get_app_setting

        return {"app_setting": get_app_setting()}

    @app.context_processor
    def inject_now():

        return {"now": datetime.utcnow}

    @app.context_processor
    def inject_language():

        return {
            "current_language": get_locale(),
            "available_languages": app.config["LANGUAGES"],
        }

    # ========================================================
    # LOG KE FILE
    # ========================================================
    # Dev server biasa cuma nulis ke console, yang hilang begitu
    # proses di-restart - jadi kalau ada error di production dan
    # tidak ada yang mantengin layar saat itu terjadi, tidak ada
    # jejaknya sama sekali. Di-skip saat testing supaya suite test
    # tidak ikut menulis file log (app.testing belum kepasang di
    # titik ini, lihat catatan di tests/conftest.py).
    if os.environ.get("TESTING") != "True":

        log_dir = os.path.join(app.instance_path, "logs")

        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=1 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )

        file_handler.setLevel(logging.WARNING)

        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s"
            )
        )

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.WARNING)

    return app