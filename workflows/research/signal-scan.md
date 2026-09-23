---
type: workflow
command: signal-scan
mode: read
---
# signal-scan

Find and qualify public buying signals for one named account.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, web.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Resolve the Account by name and domain, its owner and open Opportunities. Apply policy.routing. An active deal routes to the sales repository; live engagement owned by another rep is a collision to report. Do not infer ownership from the company name alone.
2. Declare account-owned aliases from sourced evidence, including any subsidiary or executive used in attribution. Ask the user to resolve uncertain attribution before handoff.
3. Read only the relevant _shared/taxonomy.json signal types and the account scope. List the search queries for coverage. Prefer first-party statements or documented company actions; distinguish internal adoption from a vendor selling its own AI product.
4. Fetch selected pages in full. Record the URL, verbatim quote, speaker, evidence subject, published or explicit event date, timezone-aware checked_at, account domain and signal_type in output/{run-id}/bundle.json. A snippet or inferred publication date is insufficient.
5. Run scripts/check_signal.py against the bundle, saved page text and configured taxonomy. That check verifies quote presence, declared attribution and freshness, not semantic fit or page authenticity. Review those separately. An undated evergreen page without a dated event remains unqualified.
6. Report sources examined, qualified and rejected signals, reasons, account routing, and the next dated trigger if supported. No usable signal is not proof of no initiative. Include the bundle only when it is both qualified and recommended.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested read-only deliverable, source coverage, evidence and unresolved items.
- For a recommended qualified signal, declare bundle.json and the fetched source text in the review's artifacts list. For an unqualified result, state why no bundle is handed off.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Its effects list is empty.

## Human check
Read the source quote in context, confirm attribution and the signal's actual fit. A qualified bundle does not authorize an email draft or contact creation.
