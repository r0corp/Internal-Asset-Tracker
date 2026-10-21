from tests.conftest import get_csrf_token


def test_add_asset(admin_client, app):

    token = get_csrf_token(admin_client, "/assets/add")

    response = admin_client.post(
        "/assets/add",
        data={
            "asset_tag": "QA-TEST-001",
            "asset_name": "Laptop QA Test",
            "status": "Active",
            "purchase_price": "1234.56",
            "csrf_token": token,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        from app.models import Asset

        asset = Asset.query.filter_by(asset_tag="QA-TEST-001").first()

        assert asset is not None
        assert asset.purchase_price == 1234.56


def test_edit_asset_price_parses_decimal_correctly(admin_client, app):

    with app.app_context():

        from app.models import Asset

        asset = Asset.query.filter_by(asset_tag="QA-TEST-001").first()
        asset_id = asset.id
        asset_tag = asset.asset_tag
        asset_name = asset.asset_name

    token = get_csrf_token(
        admin_client,
        f"/assets/edit/{asset_id}",
    )

    admin_client.post(
        f"/assets/edit/{asset_id}",
        data={
            "asset_tag": asset_tag,
            "asset_name": asset_name,
            "status": "Active",
            "purchase_price": "9999.99",
            "csrf_token": token,
        },
        follow_redirects=True,
    )

    with app.app_context():

        from app.models import Asset

        asset = Asset.query.get(asset_id)

        assert asset.purchase_price == 9999.99


def test_asset_list_pagination_stays_within_bounds(admin_client):

    response = admin_client.get("/assets?page=999")

    assert response.status_code == 200


def test_delete_asset_requires_csrf(admin_client, app):

    with app.app_context():

        from app.models import Asset

        asset = Asset.query.filter_by(asset_tag="QA-TEST-001").first()
        asset_id = asset.id

    response = admin_client.post(f"/assets/{asset_id}/delete")

    assert response.status_code == 400


def test_delete_asset_removes_photo_files(admin_client, app, monkeypatch, tmp_path):

    import app.blueprints.helpers as helpers_module
    from app.models import Asset, AssetPhoto, db

    # Foto asset disimpan di folder static yang sesungguhnya secara
    # default (lihat get_asset_photo_folder) - dialihkan ke tmp_path
    # di sini supaya test ini tidak pernah menulis/menghapus file di
    # folder static asli milik checkout ini.
    monkeypatch.setattr(
        helpers_module,
        "get_asset_photo_folder",
        lambda: str(tmp_path),
    )

    photo_filename = "test-delete-asset-photo.jpg"

    (tmp_path / photo_filename).write_bytes(b"fake-image-data")

    with app.app_context():

        asset = Asset(
            asset_tag="QA-TEST-PHOTO-DEL",
            asset_name="Test Asset With Photo",
        )

        db.session.add(asset)
        db.session.commit()

        db.session.add(
            AssetPhoto(
                asset_id=asset.id,
                filename=photo_filename,
                is_cover=True,
            )
        )
        db.session.commit()

        asset_id = asset.id

    assert (tmp_path / photo_filename).exists()

    token = get_csrf_token(admin_client, f"/assets/edit/{asset_id}")

    response = admin_client.post(
        f"/assets/{asset_id}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert not (tmp_path / photo_filename).exists()

    with app.app_context():

        assert Asset.query.get(asset_id) is None
        assert AssetPhoto.query.filter_by(asset_id=asset_id).count() == 0
