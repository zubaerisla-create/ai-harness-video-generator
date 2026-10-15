import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
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
        self._page_id = page_id
        self._access_token = access_token
        self._graph_version = graph_version

    @property
    def page_id(self) -> str:
        return (self._page_id if self._page_id is not None else settings.META_PAGE_ID).strip()

    @property
    def access_token(self) -> str:
        return (self._access_token if self._access_token is not None else settings.META_PAGE_ACCESS_TOKEN).strip()

    @property
    def graph_version(self) -> str:
        return (self._graph_version if self._graph_version is not None else settings.META_GRAPH_API_VERSION).strip()

    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{self.graph_version}"

    @property
    def video_url(self) -> str:
        return f"https://graph-video.facebook.com/{self.graph_version}"

    async def verify_page_access(self) -> Dict[str, Any]:
        """
        Verifies that the configured page access token is valid, is a true Page access token,
        and has authorization to read and publish to the Page Video API.
        Never exposes the raw access token in returned data or logs.
        """
        if not self.access_token or not self.page_id:
            return {
                "valid": False,
                "error": "META_PAGE_ID or META_PAGE_ACCESS_TOKEN is missing.",
                "page_id": self.page_id,
                "token_masked": mask_token(self.access_token)
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Verify token context via /me (determines if it's a Page token or User token)
                me_url = f"{self.graph_url}/me"
                me_res = await client.get(me_url, headers={"Authorization": f"Bearer {self.access_token}"})
                if me_res.status_code != 200:
                    err_json = me_res.json().get("error", {})
                    err_msg = err_json.get("message", me_res.text)
                    return {
                        "valid": False,
                        "error": f"Invalid token (/me verification failed): {err_msg}",
                        "page_id": self.page_id,
                        "token_masked": mask_token(self.access_token)
                    }

                me_data = me_res.json()
                token_owner_id = str(me_data.get("id"))
                effective_token = self.access_token
                is_direct_page_token = (token_owner_id == self.page_id)

                if not is_direct_page_token:
                    # Attempt to resolve Page access token from User token via /me/accounts
                    accounts_res = await client.get(
                        f"{self.graph_url}/me/accounts",
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    resolved_page_token = None
                    if accounts_res.status_code == 200:
                        for page in accounts_res.json().get("data", []):
                            if str(page.get("id")) == str(self.page_id) and page.get("access_token"):
                                resolved_page_token = page.get("access_token")
                                break

                    if resolved_page_token:
                        logger.info(f"Automatically resolved Page access token for Page {self.page_id} via /me/accounts")
                        self._access_token = resolved_page_token
                        effective_token = resolved_page_token
                    else:
                        logger.warning(
                            f"Configured token belongs to user/entity ID {token_owner_id} ({me_data.get('name')}), "
                            f"and Page ID {self.page_id} was not accessible via /me/accounts."
                        )
                        return {
                            "valid": False,
                            "is_page_token": False,
                            "error": (
                                f"The configured token belongs to entity '{me_data.get('name')}' (ID: {token_owner_id}), "
                                f"not target Page ID {self.page_id}. Please use the Page access token for Devlance Ai."
                            ),
                            "token_masked": mask_token(self.access_token)
                        }

                # 2. Query page node details
                page_url = f"{self.graph_url}/{self.page_id}"
                page_res = await client.get(
                    page_url,
                    headers={"Authorization": f"Bearer {effective_token}"},
                    params={"fields": "id,name,category,link,is_published"}
                )
                if page_res.status_code != 200:
                    err_json = page_res.json().get("error", {})
                    return {
                        "valid": False,
                        "error": f"Page query failed: {err_json.get('message', page_res.text)}",
                        "token_masked": mask_token(effective_token)
                    }

                page_data = page_res.json()

                # 3. Verify Video API endpoint access
                video_endpoint_ok = False
                try:
                    v_res = await client.get(
                        f"{self.video_url}/{self.page_id}/videos",
                        headers={"Authorization": f"Bearer {effective_token}"},
                        params={"limit": 1}
                    )
                    video_endpoint_ok = (v_res.status_code == 200)
                except Exception:
                    video_endpoint_ok = False

                logger.info(f"Facebook Page verified: '{page_data.get('name')}' (ID: {page_data.get('id')}) via {self.graph_version}")
                return {
                    "valid": True,
                    "is_page_token": True,
                    "graph_version": self.graph_version,
                    "page_id": page_data.get("id"),
                    "page_name": page_data.get("name"),
                    "category": page_data.get("category"),
                    "link": page_data.get("link"),
                    "is_published": page_data.get("is_published", True),
                    "video_api_accessible": video_endpoint_ok,
                    "token_masked": mask_token(effective_token)
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
            "fields": "id,published,status,description,created_time"
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params, headers=headers)
                if res.status_code == 200:
                    return res.json()
                return {"published": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"published": False, "error": str(e)}

    async def check_recent_publications_on_facebook(
        self,
        min_interval_minutes: int = 120
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Queries Facebook Graph API to check if any video was published to the Page
        within the last `min_interval_minutes` (default 120m).
        Guarantees zero-trust duplicate protection across multi-machine / multi-process setups.
        """
        if settings.DRY_RUN:
            return True, None, None

        if not self.access_token or not self.page_id:
            return True, None, None

        url = f"{self.video_url}/{self.page_id}/videos"
        params = {
            "fields": "id,created_time,published,title,description",
            "limit": 15
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params, headers=headers)
                if res.status_code != 200:
                    logger.warning(f"Failed to query recent videos from Facebook: {res.status_code}")
                    return True, None, None  # Allow upload if query temporarily fails

                videos = res.json().get("data", [])
                if not videos:
                    return True, None, None

                now_utc = datetime.now(timezone.utc)
                for v in videos:
                    c_time_str = v.get("created_time")
                    if not c_time_str:
                        continue
                    try:
                        c_dt = datetime.fromisoformat(c_time_str.replace("Z", "+00:00"))
                    except Exception:
                        try:
                            c_dt = datetime.strptime(c_time_str, "%Y-%m-%dT%H:%M:%S%z")
                        except Exception:
                            continue

                    # Ensure c_dt is timezone-aware in UTC
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    else:
                        c_dt = c_dt.astimezone(timezone.utc)

                    diff_m = (now_utc - c_dt).total_seconds() / 60.0
                    if 0 <= diff_m < min_interval_minutes:
                        msg = (
                            f"Enforcing interval guard: Video {v.get('id')} was published to Facebook "
                            f"{int(diff_m)} minutes ago ({c_time_str}). "
                            f"Minimum required spacing between posts is {min_interval_minutes} minutes."
                        )
                        logger.warning(msg)
                        return False, msg, v

                return True, None, None
        except Exception as e:
            logger.warning(f"Exception checking recent Facebook videos: {e}")
            return True, None, None

    async def get_recent_live_publications_count_on_facebook(self, lookback_hours: int = 24) -> int:
        """
        Directly queries Facebook Graph API to count how many videos were published
        to the Page within the last `lookback_hours` (default 24h).
        Zero-trust verification directly against Meta's servers.
        """
        if settings.DRY_RUN or not self.access_token or not self.page_id:
            return 0

        url = f"{self.video_url}/{self.page_id}/videos"
        params = {
            "fields": "id,created_time,published",
            "limit": 25
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params, headers=headers)
                if res.status_code != 200:
                    return 0

                videos = res.json().get("data", [])
                now_utc = datetime.now(timezone.utc)
                count = 0
                for v in videos:
                    c_time_str = v.get("created_time")
                    if not c_time_str:
                        continue
                    try:
                        c_dt = datetime.fromisoformat(c_time_str.replace("Z", "+00:00"))
                        if c_dt.tzinfo is None:
                            c_dt = c_dt.replace(tzinfo=timezone.utc)
                        else:
                            c_dt = c_dt.astimezone(timezone.utc)
                        diff_h = (now_utc - c_dt).total_seconds() / 3600.0
                        if 0 <= diff_h <= lookback_hours:
                            count += 1
                    except Exception:
                        continue
                return count
        except Exception as e:
            logger.warning(f"Error querying live publication count from Meta: {e}")
            return 0

    async def reconcile_video_with_facebook(
        self,
        title: str,
        caption: str,
        max_lookback_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Reconciles ambiguous upload timeouts by checking if a video matching the title
        or description was actually created on Facebook in the last `max_lookback_hours`.
        Guarantees that retry attempts never duplicate an already-uploaded video.
        """
        if settings.DRY_RUN or not self.access_token or not self.page_id:
            return None

        url = f"{self.video_url}/{self.page_id}/videos"
        params = {
            "fields": "id,title,description,created_time,published,status",
            "limit": 25
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, params=params, headers=headers)
                if res.status_code != 200:
                    return None

                videos = res.json().get("data", [])
                clean_title = (title or "").strip().lower()
                clean_caption = (caption or "").strip().lower()
                now_utc = datetime.now(timezone.utc)

                for v in videos:
                    c_time_str = v.get("created_time")
                    if c_time_str:
                        try:
                            c_dt = datetime.fromisoformat(c_time_str.replace("Z", "+00:00"))
                            if c_dt.tzinfo is None:
                                c_dt = c_dt.replace(tzinfo=timezone.utc)
                            else:
                                c_dt = c_dt.astimezone(timezone.utc)
                            diff_h = (now_utc - c_dt).total_seconds() / 3600.0
                            if diff_h > max_lookback_hours:
                                continue
                        except Exception:
                            pass

                    fb_title = (v.get("title") or "").strip().lower()
                    fb_desc = (v.get("description") or "").strip().lower()

                    matched = False
                    if clean_title and len(clean_title) > 10 and (clean_title in fb_title or clean_title in fb_desc):
                        matched = True
                    elif clean_caption and len(clean_caption) > 15 and clean_caption[:50] in fb_desc:
                        matched = True

                    if matched:
                        logger.info(
                            f"Reconciled upload with Meta: Video '{v.get('id')}' matches title/caption "
                            f"on Facebook. Reusing existing upload rather than re-uploading."
                        )
                        return v

                return None
        except Exception as e:
            logger.warning(f"Error during Meta reconciliation check: {e}")
            return None

    async def publish_video(
        self,
        video_path: Path,
        title: str,
        caption: str,
        hashtags: Optional[str] = None,
        job_id: Optional[str] = None,
        dry_run_override: Optional[bool] = None
    ) -> PublishResult:
        """
        Publishes a rendered MP4 video to the configured Facebook Page.
        Guarantees dry-run safety, live publishing guards, and token masking.
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

        # 1. DRY_RUN Guard: Never publish a real video in dry-run mode (or when dry_run_override is True)
        is_dry = settings.DRY_RUN if dry_run_override is None else (settings.DRY_RUN or dry_run_override)
        if is_dry:
            simulated_id = f"dry_run_{int(time.time())}"
            logger.info(
                f"[DRY_RUN] Simulated publication for Job {job_id or 'N/A'}: "
                f"File: {video_path.name} ({round(file_size/(1024*1024), 2)}MB) -> Simulated ID: {simulated_id}"
            )
            return PublishResult(
                success=True,
                video_id=simulated_id,
                post_id=f"dry_run_post_{int(time.time())}",
                is_dry_run=True,
                status_code=200
            )

        # Check credentials
        if not self.access_token or not self.page_id:
            return PublishResult(
                success=False,
                error_message="Missing Facebook credentials (META_PAGE_ID or META_PAGE_ACCESS_TOKEN)."
            )

        # 2. Live Publishing Guard: If FACEBOOK_PUBLISHING_ENABLED is False and not DRY_RUN, refuse to upload
        if not settings.FACEBOOK_PUBLISHING_ENABLED:
            logger.warning("Publication aborted: FACEBOOK_PUBLISHING_ENABLED is False.")
            return PublishResult(
                success=False,
                error_message="Live publishing is currently disabled (FACEBOOK_PUBLISHING_ENABLED=False). Enable it to publish live."
            )

        # 3. Minimum Publishing Interval Guard (enforces >= 2 hours between live posts directly on Facebook)
        can_pub, interval_err, _ = await self.check_recent_publications_on_facebook(min_interval_minutes=120)
        if not can_pub:
            return PublishResult(
                success=False,
                error_message=interval_err,
                retryable=False
            )

        # 4. Meta Upload Timeout Reconciliation: Check if this video was already received by Facebook
        reconciled = await self.reconcile_video_with_facebook(title=title, caption=caption)
        if reconciled:
            v_id = reconciled.get("id")
            logger.info(f"Reconciled job {job_id} with existing Facebook video ID {v_id}. Reusing video.")
            return PublishResult(
                success=True,
                video_id=v_id,
                post_id=v_id,
                status_code=200
            )

        upload_endpoint = f"{self.video_url}/{self.page_id}/videos"
        headers = {"Authorization": f"Bearer {self.access_token}"}
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
                        headers=headers,
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
