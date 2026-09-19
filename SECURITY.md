# Security policy

Use this software only for local simulation. It does not control real vehicles.
The replay consumes recorded data; it must never expose a simulator control endpoint.

Keep raw logs, environment files, checkpoints, local tool state and host reports out
of source commits. Publish only validated allowlisted evidence. Do not include
credentials, user home paths, personal contact details or private source URLs.
Use a GitHub no-reply email for public commits. Review `git diff --cached` before pushing.

Report vulnerabilities through this repository's private GitHub vulnerability reporting
feature when enabled. Otherwise request a private reporting channel without including
exploit details or sensitive data in an issue.

CI uses read-only permissions, pinned actions and hosted runners. Do not run untrusted
pull requests on a GPU workstation containing credentials. Isaac jobs are explicit local runs.
