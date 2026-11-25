import argparse
import tempfile
import unittest
from pathlib import Path

import youtube_upload


class FakeRequest:
    def __init__(self):
        self.response = {"id": "abc123"}

    def execute(self):
        return self.response


class FakeVideos:
    def __init__(self):
        self.kwargs = None
        self.request = FakeRequest()

    def insert(self, **kwargs):
        self.kwargs = kwargs
        return self.request


class FakeService:
    def __init__(self):
        self.fake_videos = FakeVideos()

    def videos(self):
        return self.fake_videos


class YoutubeUploadTest(unittest.TestCase):
    def test_loads_yaml_with_injected_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "upload.yaml"
            config.write_text("ignored")

            loaded = youtube_upload.load_config(
                str(config), yaml_loader=lambda text: {"file": "a.mp4", "title": "A"}
            )

        self.assertEqual(loaded, {"file": "a.mp4", "title": "A"})

    def test_missing_default_config_is_ok(self):
        args = youtube_upload.parser().parse_args(["--file", "video.mp4", "--title", "Title"])

        self.assertEqual(args.config, "youtube_upload.yaml")
        self.assertEqual(youtube_upload.load_config(args.config), {})

    def test_cli_overrides_config(self):
        args = argparse.Namespace(
            config="upload.yaml",
            file=None,
            title="CLI title",
            description=None,
            audience=None,
            privacy_status=None,
            category_id=None,
            tags="one, two",
            publish_at=None,
            client_secrets=None,
            token_file=None,
            notify_subscribers=None,
        )

        options = youtube_upload.merge_options(
            {"file": "video.mp4", "title": "YAML title", "tags": ["old"]}, args
        )

        self.assertEqual(options["title"], "CLI title")
        self.assertEqual(options["tags"], ["one", "two"])
        self.assertTrue(options["notify_subscribers"])
        self.assertEqual(options["privacy_status"], "public")
        self.assertEqual(options["audience"], "not_made_for_kids")
        self.assertEqual(options["token_file"], ".youtube-upload-token.json")
        self.assertNotIn("publish_at", options)

    def test_publish_at_requires_private_video(self):
        args = youtube_upload.parser().parse_args(
            ["--file", "video.mp4", "--title", "Title", "--publish-at", "2026-11-19T18:00:00Z"]
        )

        with self.assertRaisesRegex(ValueError, "requires privacy_status private"):
            youtube_upload.merge_options({}, args)

    def test_upload_builds_youtube_request(self):
        media_calls = []

        def fake_media(*args, **kwargs):
            media_calls.append((args, kwargs))
            return "media"

        service = FakeService()
        response = youtube_upload.upload(
            service,
            {
                "file": "video.mp4",
                "title": "Title",
                "description": "Desc",
                "tags": ["tag"],
                "category_id": "22",
                "privacy_status": "unlisted",
                "audience": "not_made_for_kids",
                "notify_subscribers": True,
            },
            media_cls=fake_media,
        )

        self.assertEqual(response, {"id": "abc123"})
        self.assertEqual(media_calls, [(("video.mp4",), {"chunksize": -1, "resumable": True})])
        self.assertEqual(
            service.fake_videos.kwargs,
            {
                "part": "snippet,status",
                "body": {
                    "snippet": {
                        "title": "Title",
                        "description": "Desc",
                        "categoryId": "22",
                        "tags": ["tag"],
                    },
                    "status": {
                        "privacyStatus": "unlisted",
                        "selfDeclaredMadeForKids": False,
                    },
                },
                "media_body": "media",
                "notifySubscribers": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
