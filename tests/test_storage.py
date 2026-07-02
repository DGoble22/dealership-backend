import io
import unittest
from unittest import mock

from routes import utils


class StorageHelpersTests(unittest.TestCase):
    def test_resolve_image_url_keeps_external_urls(self):
        self.assertEqual(
            utils.resolve_image_url("https://imgbb.com/test.jpg"),
            "https://imgbb.com/test.jpg",
        )

    def test_resolve_image_url_uses_local_path_for_development(self):
        with mock.patch.dict("os.environ", {"IMAGE_STORAGE_BACKEND": "local"}, clear=False):
            self.assertEqual(utils.resolve_image_url("car_1_2.jpg"), "http://localhost:5001/uploads/car_1_2.jpg")

    def test_upload_image_uses_local_storage_when_not_imgbb(self):
        image_file = io.BytesIO(b"fake-image-bytes")
        image_file.filename = "test.jpg"
        image_file.mimetype = "image/jpeg"

        with mock.patch.dict("os.environ", {"IMAGE_STORAGE_BACKEND": "local"}, clear=False):
            with mock.patch("routes.utils.uploads_dir", return_value="/tmp"):
                result = utils.upload_image(image_file)

                self.assertEqual(result["storage"], "local")
                self.assertEqual(result["filename"], "test.jpg")

    def test_delete_image_returns_false_for_remote_without_delete_url(self):
        with mock.patch.dict("os.environ", {"IMAGE_STORAGE_BACKEND": "imgbb"}, clear=False):
            result = utils.delete_image("https://imgbb.com/test.jpg")
            self.assertEqual(result["storage"], "imgbb")
            self.assertFalse(result["deleted"])

    def test_ensure_picture_delete_url_column_creates_missing_column(self):
        fake_conn = mock.MagicMock()
        fake_cursor = fake_conn.cursor.return_value
        fake_cursor.fetchone.return_value = None

        with mock.patch("routes.utils.db_conn") as db_conn_mock:
            db_conn_mock.return_value.__enter__.return_value = fake_conn
            db_conn_mock.return_value.__exit__.return_value = None

            result = utils.ensure_picture_delete_url_column()

            self.assertTrue(result)
            fake_conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
