# Packet risk invariants

Select only the surfaces changed by the assignment. Link adopted contracts; do not duplicate governance or paste every checklist. Name the invariant, negative test, and proof environment in the packet. Reviewers assess delivered behavior against these invariants, not only passing tests.

| Surface | Invariants to resolve before coding |
|---|---|
| Money | Reservation precedes billable dispatch where required; settlement uses fresh authority; abort, timeout, shutdown and replay cannot leak or double-charge; multi-instance races are tested. |
| Tenancy | Every write binds the validated tenant; missing context denies; composite relationships cannot cross tenants; prove enforcement as a NOBYPASSRLS application role, including raw SQL. |
| Authorization | Enumerate actual host policy registrations and endpoint metadata; missing/default authority denies; actor identity comes from trusted authentication, not request-body assertions. |
| Files | Validate before storing; scope paths and handle symlinks; bound input; clean up every failure path and preserve explicit ownership. |
| State machines | Public/default/reconstructed state cannot bypass validation; mutations cannot silently grant authority or reset allowances; history is immutable; stale versions/generations cannot act. |
| Migrations | Model and snapshot agree; test upgrades against isolated databases with existing rows; declare deployment order and rollback constraints; no shared-runtime migration without its authority. |
| UI | Overlays leave targets/popups usable; navigation and component lifetimes preserve intended state; choose accessibility and real-browser checks for the changed interaction. |

After consumer adoption affecting trust boundaries, run focused checks for missing route policies, unbounded/secret-bearing audit properties, and tenant-unbound writes. Reuse unchanged evidence; a sweep supplements independent review and does not certify general security.
