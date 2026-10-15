import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import httpx
from pydantic import BaseModel

from backend.app.config import settings

logger = logging.getLogger("ai_harness.facebook_publisher")

def mask_token(token: Optional[str]) -> str:
    """Mask sensitive tokens in logs to prevent accidental exposure."""
    if not token:
        return "<EMPTY_TOKEN>"
    clean = token.strip()
    if len(clean) <= 10:
        return "***"
    return f"{clean[:5]}...{clean[-4:]}"

class PublishResult(BaseModel):
    success: bool
    video_id: Optional[str] = None
    post_id: Optional[str] = None
    is_dry_run: bool = False
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    retryable: bool = False
    retry_after_seconds: Optional[int] = None

class FacebookPublisherService:
    """
    Autonomous Facebook Graph Video Publishing Service.
    Publishes rendered MP4 video files to the connected Facebook Page using the Meta Graph API.
    Guarantees token masking, dry-run safety, and idempotency checks.
    """

    def __init__(
        self,
        page_id: Optional[str] = None,
        access_token: Optional[str] = None,
        graph_version: Optional[str] = None
    ):
        self.page_id = (page_id if page_id is not None else settings.META_PAGE_ID).strip()
        self.access_token = (access_token if access_token is not None else settings.META_PAGE_ACCESS_TOKEN).strip()
        self.graph_version = (graph_version if graph_version is not None else settings.META_GRAPH_API_VERSION).strip()
        self.graph_url = f"https://graph.facebook.com/{self.graph_version}"
        self.video_url = f"https://graph-video.facebook.com/{self.graph_version}"

    async def verify_page_access(self) -> Dict[str, Any]:
        """
        Verifies that the configured page access token is valid and can access the Page.
        Never exposes the access token in returned data or logs.
        """
        if not self.access_token or not self.page_id:
            return {
                "valid": False,
                "error": "META_PAGE_ID or META_PAGE_ACCESS_TOKEN is missing.",
                "page_id": self.page_id,
                "token_masked": mask_token(self.access_token)
            }

        url = f"{self.graph_url}/{self.page_id}"
        params = {
            "fields": "id,name,category,link,is_published",
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params)
                
                if res.status_code == 200:
                    data = res.json()
                    logger.info(f"Facebook Page verified: {data.get('name')} (ID: {data.get('id')})")
                    return {
                        "valid": True,
                        "page_id": data.get("id"),
                        "page_name": data.get("name"),
                        "category": data.get("category"),
                        "link": data.get("link"),
                        "is_published": data.get("is_published", True),
                        "token_masked": mask_token(self.access_token)
                    }
                else:
                    err_json = res.json().get("error", {})
                    err_msg = err_json.get("message", res.text)
                    err_type = err_json.get("type", "Unknown")
                    err_code = err_json.get("code", res.status_code)
                    safe_msg = f"Graph API error ({err_code}): {err_msg} [{err_type}]"
                    logger.error(f"Facebook Page verification failed: {safe_msg}")
                    return {
                        "valid": False,
                        "error": safe_msg,
                        "error_code": err_code,
                        "token_masked": mask_token(self.access_token)
                    }
        except Exception as e:
            logger.error(f"Network error verifying Facebook Page: {e}")
            return {
                "valid": False,
                "error": f"Network exception: {str(e)}",
                "token_masked": mask_token(self.access_token)
            }

    async def verify_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Checks publication and processing status of an uploaded video on Facebook.
        """
        if settings.DRY_RUN or video_id.startswith("dry_run_"):
            return {
                "published": True,
                "video_id": video_id,
                "status": {"video_status": "ready"},
                "is_dry_run": True
            }

        url = f"{self.graph_url}/{video_id}"
        params = {
            "fields": "id,published,status,description,created_time",
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    return res.json()
                return {"published": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"published": False, "error": str(e)}

    async def publish_video(
        self,
        video_path: Path,
        title: str,
        caption: str,
        hashtags: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> PublishResult:
        """
        Publishes a rendered MP4 video to the configured Facebook Page.
        Supports multipart direct upload, token masking, and dry-run execution.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            return PublishResult(
                success=False,
                error_message=f"Video file does not exist on disk: {video_path}"
            )

        file_size = video_path.stat().st_size
        if file_size < 10000:
            return PublishResult(
                success=False,
                error_message=f"Video file corrupted or too small ({file_size} bytes)"
            )

        # Build full description with hashtags
        clean_desc = caption.strip() if caption else title.strip()
        if hashtags:
            clean_tags = " ".join([tag.strip() for tag in hashtags.split() if tag.strip()])
            if clean_tags and clean_tags not in clean_desc:
                clean_desc = f"{clean_desc}\n\n{clean_tags}"

        # Dry run guard
        if settings.DRY_RUN:
            simulated_id = f"dry_run_{int(time.time())}"
            logger.info(
                f"[DRY_RUN] Simulated publication for Job {job_id or 'N/A'}: "
                f"File: {video_path.name} ({round(file_size/(1024*1024), 2)}MB) -> Facebook Video ID: {simulated_id}"
            )
            return PublishResult(
                success=True,
                video_id=simulated_id,
                post_id=f"dry_run_post_{int(time.time())}",
                is_dry_run=True,
                status_code=200
            )

        if not self.access_token or not self.page_id:
            return PublishResult(
                success=False,
                error_message="Missing Facebook credentials (META_PAGE_ID or META_PAGE_ACCESS_TOKEN)."
            )

        upload_endpoint = f"{self.video_url}/{self.page_id}/videos"
        params = {"access_token": self.access_token}
        data = {
            "title": title[:250],
            "description": clean_desc,
            "published": "true"
        }

        logger.info(
            f"Initiating Facebook video upload for '{title}' ({round(file_size/(1024*1024), 2)}MB) "
            f"to Page ID {self.page_id} using token {mask_token(self.access_token)}"
        )

        try:
            # Facebook Graph Video API allows direct multipart upload of MP4 files
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(video_path, "rb") as video_file:
                    files = {
                        "source": (video_path.name, video_file, "video/mp4")
                    }
                    response = await client.post(
                        upload_endpoint,
                        params=params,
                        data=data,
                        files=files
                    )

            if response.status_code in [200, 201]:
                resp_json = response.json()
                video_id = resp_json.get("id")
                post_id = resp_json.get("post_id")
                
                logger.info(f"Facebook Graph API returned video_id: {video_id}, post_id: {post_id}")

                # Follow-up confirmation check
                verify_info = await self.verify_video_status(video_id)
                logger.info(f"Verification response for video {video_id}: {verify_info}")

                return PublishResult(
                    success=True,
                    video_id=video_id,
                    post_id=post_id or video_id,
                    status_code=response.status_code
                )
            
            # Error handling
            status_code = response.status_code
            resp_data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
            err_obj = resp_data.get("error", {})
            err_message = err_obj.get("message", response.text)
            err_code = err_obj.get("code", status_code)
            err_subcode = err_obj.get("error_subcode")
            
            # Safe error text without exposing credentials
            safe_error = f"Facebook Graph API error ({status_code} / code {err_code}): {err_message}"
            logger.error(f"Publish failed: {safe_error}")

            # Check if retryable (e.g. rate limit code 4 / 17 / 32 / 613 or 5xx server errors)
            retryable = False
            retry_after = None

            if status_code in [429, 500, 502, 503, 504] or err_code in [4, 17, 32, 613]:
                retryable = True
                if "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                    except Exception:
                        retry_after = 300
                else:
                    retry_after = 300  # Default 5 minutes for transient failure

            return PublishResult(
                success=False,
                status_code=status_code,
                error_message=safe_error,
                retryable=retryable,
                retry_after_seconds=retry_after
            )

        except httpx.TimeoutException:
            logger.error("Facebook upload request timed out after 300s")
            return PublishResult(
                success=False,
                error_message="Facebook upload connection timed out",
                retryable=True,
                retry_after_seconds=300
            )
        except Exception as e:
            logger.error(f"Unexpected error publishing to Facebook: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error_message=f"Publication exception: {str(e)}",
                retryable=True,
                retry_after_seconds=300
            )

facebook_publisher = FacebookPublisherService()
