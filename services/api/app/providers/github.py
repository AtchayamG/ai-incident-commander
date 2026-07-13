import json
import urllib.error
import urllib.request

from app.domain.contracts import Incident
from app.providers.base import PullRequestReceipt


class GitHubPullRequestProvider:
    """Live GitHub PR provider.

    Creates a draft pull request only when explicitly configured and approved,
    fails closed, redacts tokens, and does not merge, push, or publish.
    """

    def __init__(self, token: str, repository: str, head_ref: str = "", base_ref: str = "") -> None:
        self.token = token
        self.repository = repository
        self.head_ref = head_ref
        self.base_ref = base_ref

    def create_draft_pr(
        self, incident: Incident, diff: str, idempotency_key: str
    ) -> PullRequestReceipt:
        if not self.token or not self.repository or not self.head_ref or not self.base_ref:
            raise RuntimeError(
                "GitHub provider is not fully configured "
                "(token, repository, head_ref, base_ref are required)"
            )

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Incident-Commander-AI",
            "Content-Type": "application/json",
        }

        # Use pre-existing configured refs
        head_branch = self.head_ref
        base_branch = self.base_ref

        # The pre-existing head ref contains the reviewed patch. Never copy the
        # diff into an external request body: it may contain sensitive text.
        body_text = (
            f"Proposed remediation for incident: {incident.title}\n\n"
            f"Incident ID: {incident.id}\n"
            f"Idempotency Key: {idempotency_key}\n"
        )

        data = {
            "title": f"fix({incident.service}): resolve incident {incident.id}",
            "head": head_branch,
            "base": base_branch,
            "body": body_text,
            "draft": True,
        }

        url = f"https://api.github.com/repos/{self.repository}/pulls"
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                pr_url = res_body.get("html_url", f"https://github.com/{self.repository}/pull/{res_body.get('number')}")
                return PullRequestReceipt(
                    provider="github",
                    url=pr_url,
                    simulated=False,
                    idempotency_key=idempotency_key,
                )
        except Exception as e:
            # Ensure the token is redacted from error details
            err_str = str(e)
            if self.token:
                err_str = err_str.replace(self.token, "REDACTED")
            raise RuntimeError(f"GitHub API action failed: {err_str}") from e
