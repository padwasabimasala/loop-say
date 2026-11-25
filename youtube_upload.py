#!/usr/bin/env python3
"""Upload a YouTube video from YAML metadata plus CLI overrides."""

from __future__ import annotations

import argparse
from pathlib import Path


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DEFAULTS = {
    "category_id": "22",
    "client_secrets": ".youtube-oauth-client.json",
    "description": "",
    "notify_subscribers": True,
    "privacy_status": "public",
    "token_file": ".youtube-upload-token.json",
    "audience": "not_made_for_kids",
}


def load_config(path: str, yaml_loader=None) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}

    if yaml_loader is None:
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("Missing dependency: pip install PyYAML") from exc
        yaml_loader = yaml.safe_load
    return yaml_loader(config_path.read_text()) or {}


def split_tags(value):
    if value is None or isinstance(value, list):
        return value
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def made_for_kids(audience):
    if isinstance(audience, bool):
        return audience

    value = str(audience).lower().replace("-", "_").strip()
    if value in {"kids", "for_kids", "made_for_kids", "true", "yes"}:
        return True
    if value in {"not_kids", "not_for_kids", "not_made_for_kids", "general", "false", "no"}:
        return False
    raise ValueError("audience must be made_for_kids or not_made_for_kids")


def merge_options(config: dict, args: argparse.Namespace) -> dict:
    merged = DEFAULTS | config
    for key, value in vars(args).items():
        if key != "config" and value is not None:
            merged[key] = value

    merged["tags"] = split_tags(merged.get("tags")) or []
    missing = [key for key in ("file", "title") if not merged.get(key)]
    if missing:
        raise ValueError(f"Missing required option(s): {', '.join(missing)}")
    if merged.get("publish_at") and merged["privacy_status"] != "private":
        raise ValueError("publish_at requires privacy_status private")
    return merged


def get_credentials(client_secrets: str, token_file: str):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pip install google-auth google-auth-oauthlib"
        ) from exc

    creds = None
    token_path = Path(token_file)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        creds = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES).run_local_server(port=0)

    token_path.write_text(creds.to_json())
    return creds


def youtube_service(creds):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install google-api-python-client") from exc
    return build("youtube", "v3", credentials=creds)


def upload(service, options: dict, media_cls=None) -> dict:
    if media_cls is None:
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:
            raise SystemExit("Missing dependency: pip install google-api-python-client") from exc
        media_cls = MediaFileUpload

    body = {
        "snippet": {
            "title": options["title"],
            "description": options.get("description", ""),
            "categoryId": str(options["category_id"]),
            "tags": options.get("tags", []),
        },
        "status": {
            "privacyStatus": options["privacy_status"],
            "selfDeclaredMadeForKids": made_for_kids(options["audience"]),
        },
    }
    if options.get("publish_at"):
        body["status"]["publishAt"] = options["publish_at"]

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_cls(options["file"], chunksize=-1, resumable=True),
        notifySubscribers=options["notify_subscribers"],
    )
    return request.execute()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", nargs="?", default="youtube_upload.yaml", help="YAML file with upload metadata")
    p.add_argument("--file", help="video file to upload")
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--audience", choices=["made_for_kids", "not_made_for_kids"])
    p.add_argument("--privacy-status", choices=["private", "unlisted", "public"])
    p.add_argument("--category-id")
    p.add_argument("--tags", help="comma-separated tags")
    p.add_argument("--publish-at", help="RFC3339 future publish time; requires --privacy-status private")
    p.add_argument("--client-secrets", help="OAuth client secrets JSON")
    p.add_argument("--token-file", help="cached OAuth token dotfile")
    p.add_argument("--notify-subscribers", action=argparse.BooleanOptionalAction, default=None)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    options = merge_options(load_config(args.config), args)
    creds = get_credentials(options["client_secrets"], options["token_file"])
    response = upload(youtube_service(creds), options)
    print(f"https://www.youtube.com/watch?v={response['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
