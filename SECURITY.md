# Security Policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository when it is
available. Do not open a public issue for an unpatched vulnerability or include
real credentials, customer data, exploit tokens, or production endpoints in a
report.

Include the affected version or commit, minimal reproduction, impact, and any
known workaround. Maintainers will confirm receipt and coordinate disclosure;
no response-time promise is made.

## Supported versions

Until the first stable release, security fixes are applied to the current
default branch. Historical artifacts and releases may not receive backports.

Eval datasets and evidence packs are untrusted input. Run third-party adapters
with least privilege and isolated credentials. Content hashes detect change but
do not make local files immutable or prove who created them.
