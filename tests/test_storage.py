import io
import unittest
from unittest import mock

from routes import utils
from routes import car as car_routes


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

    def test_next_picture_number_starts_at_zero(self):
        self.assertEqual(utils.next_picture_number(None), 0)
        self.assertEqual(utils.next_picture_number(0), 1)

    def test_delete_image_returns_false_for_remote_without_delete_url(self):
        with mock.patch.dict("os.environ", {"IMAGE_STORAGE_BACKEND": "imgbb"}, clear=False):
            result = utils.delete_image("https://imgbb.com/test.jpg")
            self.assertEqual(result["storage"], "imgbb")
            self.assertFalse(result["deleted"])

    def test_delete_image_treats_empty_body_success_as_delete_success(self):
        with mock.patch.dict("os.environ", {"IMAGE_STORAGE_BACKEND": "imgbb"}, clear=False):
            fake_response = mock.MagicMock()
            fake_response.read.return_value = b""
            fake_context = mock.MagicMock()
            fake_context.__enter__.return_value = fake_response
            fake_context.__exit__.return_value = None

            with mock.patch("routes.utils.urllib_request.urlopen", return_value=fake_context):
                result = utils.delete_image("https://imgbb.com/test.jpg", "https://example.com/delete")

            self.assertEqual(result["storage"], "imgbb")
            self.assertTrue(result["deleted"])

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

    def test_delete_image_route_handler_has_distinct_name(self):
        self.assertTrue(hasattr(car_routes, "delete_image_record"))
        self.assertEqual(car_routes.delete_image_record.__name__, "delete_image_record")


if __name__ == "__main__":
    unittest.main()
