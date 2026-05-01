"""
publish/instagram.py
Meta Graph API integration – placeholder + full implementation scaffold.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO ENABLE REAL PUBLISHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prerequisites
─────────────
1.  A Facebook App (developers.facebook.com) with these permissions:
      instagram_basic
      instagram_content_publish
      pages_read_engagement

2.  Connect an Instagram Business or Creator account to a Facebook Page.

3.  Generate a long-lived User Access Token (valid ~60 days).
    Use Meta's Token Debugger to inspect and extend it.

4.  Find your Instagram Business Account ID:
      GET https://graph.facebook.com/v18.0/me/accounts
    → find the page, then:
      GET https://graph.facebook.com/v18.0/<page_id>?fields=instagram_business_account

Required .env variables
───────────────────────
META_ACCESS_TOKEN               – long-lived user access token
INSTAGRAM_BUSINESS_ACCOUNT_ID  – numeric IG business account ID
META_APP_ID                     – your Facebook App ID
META_APP_SECRET                 – your Facebook App Secret

Publishing flow (IMAGE)
───────────────────────
Step 1 – Upload media container:
  POST /v18.0/{ig-user-id}/media
    image_url   = <publicly accessible URL of your image>
    caption     = <your caption + hashtags>

Step 2 – Publish the container:
  POST /v18.0/{ig-user-id}/media_publish
    creation_id = <id from step 1>

Publishing flow (REEL)
───────────────────────
Step 1 – Upload video container:
  POST /v18.0/{ig-user-id}/media
    media_type  = REELS
    video_url   = <publicly accessible URL>
    caption     = <caption>

Step 2 – Check upload status (poll until status=FINISHED):
  GET /v18.0/{container-id}?fields=status_code

Step 3 – Publish:
  POST /v18.0/{ig-user-id}/media_publish
    creation_id = <container-id>

Rate limits
───────────
25 API-published posts per 24-hour rolling window per IG account.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v18.0"


class InstagramPublisher:
    """
    Wraps the Meta Graph API for Instagram content publishing.
    Instantiate once and reuse.
    """

    def __init__(self):
        self.access_token = os.environ.get("META_ACCESS_TOKEN", "")
        self.ig_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    def _is_configured(self) -> bool:
        return bool(self.access_token and self.ig_account_id)

    # ── Image publishing ──────────────────────────────────────────────────────

    def publish_image(
        self,
        image_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> dict:
        """
        Publish a single image to Instagram.

        Parameters
        ----------
        image_url : publicly accessible HTTPS URL of the image
        caption   : post caption
        hashtags  : list of hashtag strings (will be appended to caption)
        """
        if not self._is_configured():
            return self._placeholder_response("image")

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(hashtags)

        # Step 1 – Create media container
        container_id = self._create_image_container(image_url, full_caption)

        # Step 2 – Publish
        post_id = self._publish_container(container_id)

        logger.info(f"Image published successfully. Post ID: {post_id}")
        return {"success": True, "post_id": post_id, "type": "image"}

    def _create_image_container(self, image_url: str, caption: str) -> str:
        url = f"{GRAPH_BASE}/{self.ig_account_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        response = httpx.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Container created: {data.get('id')}")
        return data["id"]

    # ── Reel publishing ───────────────────────────────────────────────────────

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
        cover_url: Optional[str] = None,
    ) -> dict:
        """
        Publish a Reel to Instagram.

        Parameters
        ----------
        video_url : publicly accessible HTTPS URL of the video (.mp4)
        caption   : post caption
        hashtags  : list of hashtag strings
        cover_url : optional thumbnail image URL
        """
        if not self._is_configured():
            return self._placeholder_response("reel")

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(hashtags)

        # Step 1 – Upload container
        container_id = self._create_reel_container(video_url, full_caption, cover_url)

        # Step 2 – Poll for FINISHED status
        self._wait_for_upload(container_id)

        # Step 3 – Publish
        post_id = self._publish_container(container_id)

        logger.info(f"Reel published successfully. Post ID: {post_id}")
        return {"success": True, "post_id": post_id, "type": "reel"}

    def _create_reel_container(
        self, video_url: str, caption: str, cover_url: Optional[str]
    ) -> str:
        url = f"{GRAPH_BASE}/{self.ig_account_id}/media"
        params: dict = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        if cover_url:
            params["cover_url"] = cover_url

        response = httpx.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Reel container created: {data.get('id')}")
        return data["id"]

    def _wait_for_upload(self, container_id: str, max_polls: int = 20) -> None:
        """Poll until the container status is FINISHED (or raise on ERROR)."""
        url = f"{GRAPH_BASE}/{container_id}"
        for i in range(max_polls):
            time.sleep(5)
            resp = httpx.get(url, params={
                "fields": "status_code",
                "access_token": self.access_token,
            }, timeout=15)
            resp.raise_for_status()
            status = resp.json().get("status_code", "")
            logger.info(f"Upload status poll {i+1}: {status}")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError("Meta video upload failed with ERROR status.")
        raise TimeoutError("Video upload did not finish in time.")

    # ── Shared ────────────────────────────────────────────────────────────────

    def _publish_container(self, container_id: str) -> str:
        url = f"{GRAPH_BASE}/{self.ig_account_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        response = httpx.post(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()["id"]

    @staticmethod
    def _placeholder_response(media_type: str) -> dict:
        return {
            "success": False,
            "status": "placeholder",
            "message": (
                "Publishing module is ready for Meta Graph API integration. "
                "Set META_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in your "
                ".env file and the publish logic will activate automatically."
            ),
            "media_type": media_type,
        }


# Module-level singleton
publisher = InstagramPublisher()
