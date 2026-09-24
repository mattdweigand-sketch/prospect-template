"""Fixed, read-only preflight for the eight workflows. No provider calls or writes.

inputs.json owns paths and associations, never commands. Source entries use
{receipt, page, result, checked_at}; checked_at may instead be in the receipt.
Handoffs use {run_id, workflow, approval_reference, review, selected, artifacts}:
review is a retained source review.json; artifacts maps source-run paths to copies
in this run. Only the explicitly selected export and its evidence are read.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import factory

VERSION = 1
# Process-local comparison only. Never serialized or printed; a new process uses
# the authorized immutable adapter snapshot reference instead.
_ARR_PREIMAGES = {}
KINDS = {
    "signal-scan": set(), "signal-user-scan": set(),
    "signal-prospector": {"account_create", "owner_transfer", "contact_create"},
    "signal-outreach": {"draft"}, "signal-arr-growth": {"draft"},
    "signal-followup": {"task"},
    "prospect-setup": {"configuration"}, "signal-refresh": {"configuration"},
}
FIELDS = {
    "signal-scan": {"sources", "crm", "verdict"},
    "signal-prospector": {"sources", "candidates"},
    "signal-outreach": {"handoff", "packet", "result", "refreshed", "adoption_handoff"},
    "signal-followup": {"handoff", "packet", "result", "mode"},
    "signal-user-scan": {"bundle", "crm", "receipt"},
    "prospect-setup": {"postimages", "source_revision", "setup_result", "diagnostic", "intake"},
    "signal-refresh": {"postimages", "source_revision", "diagnostic"},
    "signal-arr-growth": {"drafts", "receipt"},
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def remember_arr(root, run_id, packet):
    if packet is not None:
        _ARR_PREIMAGES[(str(Path(root).resolve()), run_id)] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).digest()


def substantive(value):
    """Evaluation/staging metadata is not the checked payload or original fetch time."""
    if isinstance(value, dict):
        return {k: substantive(v) for k, v in value.items()
                if k not in ("checked_on", "stage", "stage_status", "configuration")}
    if isinstance(value, list):
        return [substantive(v) for v in value]
    return value


def manifest_shape(manifest, path):
    """Malformed associations are input errors, not recoverable coverage gaps."""
    def ref(value):
        factory.require(factory.nonblank(value), "manifest paths must be nonblank strings")
        factory.relative_path(path, value)

    def source(entry):
        factory.require(isinstance(entry, dict) and {"receipt", "page", "result"} <= set(entry)
                        and set(entry) <= {"receipt", "page", "result", "checked_at"}, "source requires receipt/page/result paths")
        for key in ("receipt", "page", "result"):
            ref(entry[key])
        factory.require("checked_at" not in entry or factory.nonblank(entry["checked_at"]), "source checked_at must be a timestamp string")

    def handoff(entry):
        fields = {"run_id", "workflow", "approval_reference", "review", "selected", "artifacts"}
        factory.require(isinstance(entry, dict) and set(entry) == fields, "handoff requires run/workflow/review/selected/artifacts identity")
        factory.require(all(factory.nonblank(entry[k]) for k in fields - {"artifacts"})
                        and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", entry["run_id"])
                        and entry["workflow"] in KINDS, "invalid handoff identity")
        factory.require(isinstance(entry["artifacts"], dict) and entry["selected"] in entry["artifacts"], "handoff artifacts must include the selected source path")
        ref(entry["review"])
        for original, copied in entry["artifacts"].items():
            ref(original)
            ref(copied)

    for effect in manifest["effects"].values():
        factory.require(set(effect) <= {"kind", "input", "account_effect"}, "unknown effect binding fields")
        ref(effect["input"])
        factory.require("account_effect" not in effect or factory.nonblank(effect["account_effect"]), "account_effect must name one effect ID")
    for key in {"crm", "verdict", "packet", "result", "bundle", "receipt", "postimages", "setup_result", "intake"} & set(manifest):
        ref(manifest[key])
    if "source_revision" in manifest:
        factory.require(isinstance(manifest["source_revision"], str) and re.fullmatch(r"[0-9a-f]{40}", manifest["source_revision"]), "source_revision must be a full commit")
    if "mode" in manifest:
        factory.require(manifest["mode"] in ("standard", "arr_growth"), "invalid follow-up mode")
    if "sources" in manifest:
        factory.require(isinstance(manifest["sources"], list), "sources must be a list")
        for entry in manifest["sources"]:
            source(entry)
        factory.require(len({e["result"] for e in manifest["sources"]}) == len(manifest["sources"]), "source result paths must be unique")
    if "refreshed" in manifest:
        source(manifest["refreshed"])
    for key in ("handoff", "adoption_handoff"):
        if key in manifest:
            handoff(manifest[key])
    if "candidates" in manifest:
        factory.require(isinstance(manifest["candidates"], list), "candidates must be a list")
        for entry in manifest["candidates"]:
            factory.require(isinstance(entry, dict) and {"receipt", "result", "sources"} <= set(entry)
                            and set(entry) <= {"receipt", "result", "sources", "contact", "adoption"}, "candidate needs receipt/result/source associations")
            for key in ("receipt", "result", "contact"):
                if key in entry:
                    ref(entry[key])
            factory.require(isinstance(entry["sources"], list) and bool(entry["sources"]), "candidate sources must be a nonempty path list")
            for value in entry["sources"]:
                ref(value)
            if "adoption" in entry:
                handoff(entry["adoption"])
    if "drafts" in manifest:
        factory.require(isinstance(manifest["drafts"], list), "drafts must be a list")
        for entry in manifest["drafts"]:
            factory.require(isinstance(entry, dict) and set(entry) == {"account_id", "draft"}
                            and factory.nonblank(entry["account_id"]), "draft needs a checked account ID and retained draft path")
            ref(entry["draft"])
    if "diagnostic" in manifest:
        entry = manifest["diagnostic"]
        factory.require(isinstance(entry, dict) and set(entry) == {"shared", "result", "revision"}, "diagnostic needs shared/result/revision")
        ref(entry["shared"])
        ref(entry["result"])
        factory.require(isinstance(entry["revision"], str) and re.fullmatch(r"[0-9a-f]{40}", entry["revision"]), "diagnostic revision must be a full commit")


class Check:
    def __init__(self, root, path, workflow, proposed, source, arr_packet, now, compare_arr):
        self.root, self.path = Path(root).resolve(), Path(path).resolve()
        self.shared = self.root / "_shared"
        self.workflow, self.source, self.arr_packet = workflow, source, arr_packet
        self.compare_arr = compare_arr
        self.now = now or datetime.now(timezone.utc)
        factory.require(self.now.tzinfo is not None, "preflight now must be timezone-aware")
        self.inputs, self.issues, self.checks, self.effects, self.exports = {}, [], {}, {}, {}
        self.manifest = self.read("inputs.json")
        m = self.manifest
        factory.require(set(m) <= FIELDS[workflow] | {"schema_version", "effects", "gaps"}, "unknown fields in inputs.json")
        factory.require(type(m.get("schema_version")) is int and m["schema_version"] == VERSION,
                        "inputs.json needs schema_version 1")
        factory.require(isinstance(m.get("effects"), dict), "inputs.effects must be an object")
        factory.require(isinstance(m.get("gaps"), list) and all(factory.nonblank(g) for g in m["gaps"]),
                        "inputs.gaps must be a list of nonblank explanations")
        factory.require(set(m["effects"]) == set(proposed), "manifest must bind exactly every proposed Effect")
        for eid, effect in m["effects"].items():
            factory.require(isinstance(effect, dict) and effect.get("kind") in KINDS[workflow]
                            and factory.nonblank(effect.get("input")), "invalid effect kind/input: " + eid)
        pairs = [(e["kind"], e["input"]) for e in m["effects"].values()]
        factory.require(len(pairs) == len(set(pairs)), "duplicate effect kind and checked input")
        manifest_shape(m, self.path)
        self.policy = factory.read(self.shared / "policy.json")

    def file(self, ref):
        factory.require(factory.nonblank(ref), "input path must be a nonblank string")
        path = factory.relative_path(self.path, ref)
        factory.require(path.is_file() and path.name not in ("review.json", "02_result.json")
                        or (path.is_file() and path.parent != self.path),
                        "input must be a retained regular file, not this run's approval/result")
        self.inputs[str(path.relative_to(self.root))] = digest(path)
        return path

    def read(self, ref):
        value = json.loads(self.file(ref).read_text())
        factory.require(isinstance(value, dict), "input must contain an object: " + str(ref))
        return value

    def compare(self, ref, actual):
        factory.require(substantive(self.read(ref)) == substantive(actual), "saved result differs from replay: " + ref)

    def attempt(self, label, fn):
        try:
            result = fn()
            self.checks[label] = result
            return result
        except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
            # Financial packets and potentially sensitive rejected values never enter output.
            reason = "ARR inputs or retained receipt failed validation" if self.workflow == "signal-arr-growth" else str(exc)
            self.issues.append(label + ": " + reason)
            self.checks[label] = {"state": "unusable", "reason": reason}
            return None

    def source_entry(self, entry, now=None):
        import evidence_gate
        factory.require(isinstance(entry, dict), "source entry must be an object")
        receipt = self.read(entry["receipt"])
        page = self.file(entry["page"]).read_text()
        code, result = evidence_gate.evaluate(receipt, page, self.shared / "policy.json",
                                              now=now or self.now, checked_at=entry.get("checked_at"))
        self.compare(entry["result"], result)
        return {"code": code, "result": result, "source": entry, "artifacts": [entry[k] for k in ("receipt", "page", "result")]}

    def sources(self):
        entries = self.manifest.get("sources", [])
        results = {}
        for n, entry in enumerate(entries):
            result = self.attempt("source:" + str(n + 1), lambda e=entry: self.source_entry(e))
            if result:
                results[entry["result"]] = result
        if not entries and not self.manifest["gaps"]:
            self.issues.append("No fetched sources: record an explicit coverage gap")
        return results

    def bind(self, ref, kind, payload, eligible=True):
        for eid, effect in self.manifest["effects"].items():
            if effect["input"] == ref and effect["kind"] == kind and eligible:
                self.effects[eid] = {"kind": kind, "input": ref, "payload": payload}

    def handoff(self, workflows, handoff=None):
        h = handoff or self.manifest.get("handoff")
        factory.require(isinstance(h, dict) and h.get("workflow") in workflows, "a named reviewed handoff is required")
        rid = h.get("run_id")
        factory.require(isinstance(rid, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", rid), "invalid source run ID")
        factory.require(rid != self.path.name, "a run cannot hand off to itself")
        review = self.read(h["review"])
        validation = review.get("validation", {})
        factory.require(validation.get("contract_version") == VERSION and validation.get("workflow") == h["workflow"]
                        and validation.get("run_id") == rid, "handoff has no current validation contract")
        factory.require(factory.nonblank(h.get("approval_reference"))
                        and review.get("approval_reference") == h["approval_reference"] and factory.nonblank(review.get("reviewer")),
                        "handoff review reference does not match")
        # A portable copy is sufficient; when the named source run is present its
        # current state must agree. Never search for other source runs.
        original = self.root / "output" / rid
        if original.exists():
            import runs
            factory.require(not original.is_symlink() and digest(original / "review.json") == digest(self.file(h["review"])),
                            "source approval record differs from the retained handoff")
            factory.require(runs.status(self.root, rid)["state"] in ("review_current", "completion_recorded"), "source review is stale or incomplete")
        selected = h["selected"]
        export = validation.get("exports", {}).get(selected)
        factory.require(isinstance(export, dict) and export.get("eligible") is True, "selected handoff is not actionable")
        if export.get("effect_id"):
            factory.require(export["effect_id"] in review.get("approved_effect_ids", []), "selected handoff effect was not approved")
            effect = validation.get("effects", {}).get(export["effect_id"], {})
            factory.require(factory.nonblank(export.get("account_id")) and effect.get("payload", {}).get("account_id") == export["account_id"], "draft handoff lacks its checked account identity")
        copies = h.get("artifacts")
        factory.require(isinstance(copies, dict), "handoff artifacts must map source paths to retained copies")
        for ref in set(export.get("artifacts", [])) | {selected}:
            factory.relative_path(Path("/portable"), ref)
            copied = self.file(copies[ref])
            factory.require(digest(copied) == review.get("snapshot", {}).get(f"output/{rid}/{ref}"),
                            "handoff artifact hash differs: " + ref)
        selected_data = self.read(copies[selected])
        if export["kind"] in ("signal", "adoption"):
            retained = selected_data.get("bundle") if export["kind"] == "signal" else selected_data
            factory.require(retained == export["bundle"], "handoff bundle differs from frozen checked artifact")
            if export["kind"] == "signal":
                crm = self.read(copies[export["crm"]])
                factory.require(factory.nonblank(export.get("account_id")) and crm["account"]["id"] == export["account_id"], "signal handoff account differs from retained CRM identity")
        else:
            retained = {"to": selected_data["recipient"]["email"], **selected_data["draft"],
                        "signal_type": selected_data["bundle"]["signal_type"], "claim_id": selected_data["claim"]["id"]} if h["workflow"] == "signal-outreach" else selected_data
            factory.require(retained == export["payload"], "handoff draft differs from frozen checked artifact")
        return export, copies

    def scan(self):
        import route_candidate
        import scan_verdict
        sources = self.sources()
        outputs = [r["result"] for r in sources.values()]
        verdict = scan_verdict.verdict(outputs)
        self.checks["verdict"] = verdict
        if self.manifest.get("verdict"):
            self.compare(self.manifest["verdict"], verdict)
        route = self.attempt("crm", lambda: route_candidate.scan_route(self.read(self.manifest["crm"]), self.policy, self.now)) if self.manifest.get("crm") else None
        if not route:
            self.issues.append("CRM ownership/activity unavailable; public findings cannot support outreach")
        selected = verdict.get("recommended")
        if selected and route and route.get("handoff_eligible") is True:
            ref, source = list(sources.items())[selected - 1]
            account = self.read(self.manifest["crm"])["account"]
            bundle = source["result"]["bundle"]
            factory.require(factory.domain(bundle["account_domain"]) == factory.domain(account["domain"]), "selected source belongs to another CRM domain")
            names = [bundle["account_name"], *bundle.get("account_aliases", [])]
            factory.require(account["name"].strip().casefold() in {n.strip().casefold() for n in names}, "selected source does not identify the resolved CRM account")
            self.exports[ref] = {"eligible": True, "kind": "signal", "bundle": source["result"]["bundle"],
                                 "account_id": account["id"], "crm": self.manifest["crm"],
                                 "artifacts": source["artifacts"] + [self.manifest["crm"]],
                                 "source": source["source"]}

    def prospector(self):
        import route_candidate
        sources = self.sources()
        candidates = self.manifest.get("candidates", [])
        factory.require(isinstance(candidates, list), "candidates must be a list")
        factory.require(len(candidates) <= self.policy["prospector"]["max_candidates"], "candidate count exceeds configured limit")
        for n, candidate in enumerate(candidates):
            def one(c=candidate):
                receipt = self.read(c["receipt"])
                linked = c["sources"]
                factory.require(isinstance(linked, list) and bool(linked), "candidate needs source associations")
                signals = []
                for ref in linked:
                    bundle = sources[ref]["result"]["bundle"]
                    factory.require(sources[ref]["code"] == 0 and factory.domain(bundle["account_domain"]) == factory.domain(receipt["domain"]), "candidate evidence belongs to another account")
                    signals.append({"signal_type": bundle["signal_type"], "tier": bundle["tier"]})
                if c.get("adoption"):
                    aggregate, _ = self.handoff({"signal-user-scan"}, c["adoption"])
                    b = aggregate["bundle"]
                    factory.require(b["paid_individuals_exist"] is True and b["org_subscribed"] is False
                                    and b["account_id"] == receipt.get("account_id")
                                    and factory.domain(b["account_domain"]) == factory.domain(receipt["domain"]), "adoption-assisted candidate identity/category mismatch")
                    today = self.now.astimezone(ZoneInfo(self.policy["identity"]["timezone"])).date()
                    factory.require(self.policy["adoption"]["enabled"] is True and b["data_through_date"] == (today - timedelta(days=self.policy["adoption"]["data_lag_days"])).isoformat(), "adoption-assisted evidence is disabled or stale")
                    sid = self.policy["prospector"]["adoption_signal_id"]
                    signals.append({"signal_type": sid, "tier": "tier2"})
                factory.require(receipt["signals"] == signals, "candidate signal IDs/tiers differ from qualified evidence")
                result = route_candidate.check(receipt, route_candidate.load_rules(self.shared))
                self.compare(c["result"], result)
                if result["claimable"]:
                    kind = "account_create" if result["route"] == "claim_new" else "owner_transfer"
                    if kind == "account_create":
                        payload = {"name": sources[linked[0]]["result"]["bundle"]["account_name"],
                                   "website": "https://" + factory.domain(receipt["domain"]),
                                   "owner_id": self.policy["identity"]["owner_id"], "employee_count": receipt["headcount"]}
                    else:
                        factory.require(factory.nonblank(receipt.get("account_id")), "owner transfer needs the exact existing account ID")
                        payload = {"account_id": receipt["account_id"], "owner_id": self.policy["identity"]["owner_id"], "previous_owner_id": receipt["owner_id"]}
                    self.bind(c["receipt"], kind, payload)
                    for eid, effect in self.manifest["effects"].items():
                        if effect["kind"] == "contact_create" and effect["input"] == c["receipt"]:
                            contact = self.read(c["contact"])
                            factory.email(contact["email"])
                            factory.require(all(factory.nonblank(contact.get(k)) for k in ("first_name", "last_name", "title", "source_reference")), "contact needs verified identity/source")
                            factory.require(contact.get("source") in self.policy["prospector"]["contact_email_sources"], "contact source is not permitted")
                            if kind == "account_create":
                                parent = effect.get("account_effect")
                                factory.require(contact.get("account_id") is None, "new-account contact cannot name another existing account")
                                factory.require(parent in self.effects and self.effects[parent]["kind"] == "account_create"
                                                and self.effects[parent]["input"] == c["receipt"], "new contact needs its account effect")
                                association = {"account_effect": parent}
                            else:
                                factory.require(contact.get("account_id") == receipt["account_id"], "contact belongs to another account")
                                association = {"account_id": receipt["account_id"]}
                            self.effects[eid] = {"kind": "contact_create", "input": c["receipt"], "payload": {
                                **association, **{k: contact[k] for k in ("first_name", "last_name", "title", "email")}}}
                return result
            self.attempt("candidate:" + str(n + 1), one)
        if not candidates and not self.manifest["gaps"]:
            self.issues.append("No candidates: record an explicit discovery gap or no-result finding")

    def outreach(self):
        import outreach_gate
        export, copies = self.handoff({"signal-scan"})
        original = dict(export["source"])
        for key in ("receipt", "page", "result"):
            original[key] = copies[original[key]]
        historical_time = datetime.fromisoformat(export["bundle"]["checked_at"].replace("Z", "+00:00"))
        original_result = self.source_entry(original, historical_time)
        factory.require(original_result["code"] == 0 and substantive(original_result["result"]["bundle"]) == substantive(export["bundle"]), "original handoff evidence no longer reproduces")
        selected = self.source_entry(self.manifest["refreshed"]) if self.manifest.get("refreshed") else self.source_entry(original)
        factory.require(selected["code"] == 0, "public evidence does not qualify")
        fresh = selected["result"]["bundle"]
        facts = lambda b: {k: v for k, v in substantive(b).items() if k != "checked_at"}
        factory.require(facts(fresh) == facts(export["bundle"]), "refetch changed substantive facts; review the revised research finding")
        packet = self.read(self.manifest["packet"])
        factory.require(all(packet["bundle"].get(k) == v for k, v in fresh.items() if k != "checked_on"), "packet evidence fields differ from the qualified source")
        if packet.get("adoption_sentence"):
            h = self.manifest.get("adoption_handoff")
            factory.require(isinstance(h, dict), "adoption sentence needs its exact reviewed aggregate handoff")
            aggregate, _ = self.handoff({"signal-user-scan"}, h)
            factory.require(packet.get("adoption_bundle") == aggregate["bundle"]
                            and packet.get("adoption_review_reference") == h["approval_reference"]
                            and packet.get("adoption_checked_at") == aggregate["checked_at"], "adoption packet differs from reviewed aggregate evidence")
        reasons = outreach_gate.check(packet, self.policy["outreach"], self.shared, self.now)
        flags = outreach_gate.fit_flags(packet, self.policy["outreach"], self.shared)
        result = {"verdict": "block", "reasons": reasons, "flags": flags} if reasons else {
            "verdict": "allow", "recipient": packet["recipient"]["email"], "signal_type": packet["bundle"]["signal_type"], "claim_id": packet["claim"]["id"], "flags": flags}
        self.compare(self.manifest["result"], result)
        self.checks["outreach"] = result
        if not reasons:
            payload = {"to": packet["recipient"]["email"], **packet["draft"], "signal_type": packet["bundle"]["signal_type"], "claim_id": packet["claim"]["id"]}
            self.bind(self.manifest["packet"], "draft", {"account_id": export["account_id"], **payload})
            for eid in self.effects:
                self.exports[self.manifest["packet"]] = {"eligible": True, "kind": "draft", "effect_id": eid, "account_id": export["account_id"], "payload": payload, "artifacts": [self.manifest["packet"], self.manifest["result"]]}

    def followup(self):
        import followup_gate
        mode = self.manifest.get("mode", "standard")
        factory.require(mode in ("standard", "arr_growth"), "invalid follow-up mode")
        export, _ = self.handoff({"signal-arr-growth"} if mode == "arr_growth" else {"signal-outreach"})
        packet = self.read(self.manifest["packet"])
        payload = export["payload"]
        factory.require(isinstance(packet.get("account"), dict) and packet["account"].get("id") == export["account_id"], "follow-up account differs from the reviewed draft account")
        factory.require(isinstance(packet.get("contacts"), list) and all(isinstance(c, dict) and c.get("account_id") == export["account_id"] for c in packet["contacts"]), "follow-up contact belongs to another draft account")
        if len(packet.get("sent", [])) == 1:
            sent = packet["sent"][0]
            factory.require(sent["to"] == payload["to"] and sent["subject"] == payload["subject"], "sent attribution differs from the reviewed draft")
        expected = {"signal_type": "arr_growth", "claim_id": "arr_growth"} if mode == "arr_growth" else {k: payload[k] for k in ("signal_type", "claim_id")}
        factory.require(packet["signal"] == expected, "follow-up attribution differs from the reviewed handoff")
        result = followup_gate.check(packet, mode, self.policy, self.now, self.shared)
        self.compare(self.manifest["result"], result)
        self.checks["followup"] = result
        self.bind(self.manifest["packet"], "task", result.get("task"), result["verdict"] == "allow")

    def adoption(self):
        import privacy_check
        factory.validate_policy(self.policy, ("identity", "adoption"))
        bundle = self.read(self.manifest["bundle"])
        issues = privacy_check.check(bundle, self.policy["adoption"]["bundle_keys"])
        factory.require(not issues, "aggregate privacy check failed: " + "; ".join(issues))
        crm = self.read(self.manifest["crm"])
        receipt = self.read(self.manifest["receipt"])
        today = self.now.astimezone(ZoneInfo(self.policy["identity"]["timezone"])).date()
        account = crm.get("account")
        factory.require(self.policy["adoption"]["enabled"] is True and crm.get("crm_complete") is True
                        and factory.nonblank(crm.get("read_reference")) and isinstance(account, dict)
                        and factory.nonblank(account.get("id")) and account.get("owner_id") == self.policy["identity"]["owner_id"]
                        and account.get("owner_is_active") is True
                        and account.get("open_opportunity_ids") == [], "adoption disabled or owned/no-open-deal CRM prerequisites incomplete")
        factory.require(receipt.get("success") is True and receipt.get("mapping_complete") is True
                        and factory.nonblank(receipt.get("reference")), "completed aggregate adapter receipt required")
        factory.require(bundle["source_reference"] == receipt["reference"], "aggregate bundle and adapter receipt references differ")
        read_at = datetime.fromisoformat(receipt["checked_at"].replace("Z", "+00:00"))
        factory.require(read_at.tzinfo is not None and read_at <= self.now, "aggregate receipt needs an actual aware nonfuture read time")
        factory.require(bundle["account_id"] == account["id"] and factory.domain(bundle["account_domain"]) == factory.domain(account["domain"]), "adoption identity mismatch")
        domain = factory.domain(account["domain"])
        internal = [factory.domain(d) for d in self.policy["identity"]["internal_domains"]]
        factory.require(not any(domain == d or domain.endswith("." + d) for d in internal), "internal account domains cannot support adoption handoffs")
        factory.require(bundle["data_through_date"] == (today - timedelta(days=self.policy["adoption"]["data_lag_days"])).isoformat(), "adoption data date is not current")
        self.checks["adoption"] = {"category": bundle["adoption"], "privacy": "clean"}
        if bundle["adoption"] in ("org_adopted", "individuals_only"):
            self.exports[self.manifest["bundle"]] = {"eligible": True, "kind": "adoption", "bundle": bundle, "checked_at": receipt["checked_at"], "artifacts": [self.manifest[k] for k in ("bundle", "crm", "receipt")]}

    def configuration(self):
        import build_pairings
        import refresh_tracks
        import validate_setup
        m = self.manifest
        factory.require(self.source is not None, "pass --source for pinned evidence verification")
        revision = m["source_revision"]
        factory.require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision), "source_revision must be a full commit")
        def shared_dir(ref):
            path = factory.relative_path(self.path, ref)
            factory.require(path.is_dir(), "retained factory directory required")
            for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md"):
                self.file(str(Path(ref) / name))
            if (path / "adapters.md").exists():
                self.file(str(Path(ref) / "adapters.md"))
            return path
        factory.require(self.workflow != "signal-refresh" or m.get("diagnostic"), "refresh needs a saved diagnostic report and its retained factory baseline")
        if m.get("diagnostic"):
            d = m["diagnostic"]
            baseline = shared_dir(d["shared"])
            self.compare(d["result"], refresh_tracks.report(Path(self.source), baseline, d["revision"]))
        if not m.get("postimages"):
            factory.require(not m["effects"] and m.get("diagnostic"), "configuration effects need postimages")
            return
        post = shared_dir(m["postimages"])
        if m.get("intake"):
            self.read(m["intake"])
        factory.require(factory.claim_document(post)["source_revision"] == revision, "postimages source revision differs")
        report = validate_setup.validate(post, Path(self.source))
        if self.workflow == "prospect-setup":
            self.compare(m["setup_result"], report)
        _, bindings = build_pairings.build(post)
        factory.require(report["messaging"]["state"] == "checks_passed" and not bindings, "proposed messaging configuration is incomplete")
        self.checks["configuration"] = report["messaging"]
        import runs
        expected = runs.review_metadata(self.path).get("expected_after", {})
        covered = {ref for changes in expected.values() for ref in changes}
        changed = {"_shared/" + name for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md", "adapters.md")
                   if (post / name).is_file() and (not (self.shared / name).is_file() or digest(post / name) != digest(self.shared / name))}
        factory.require(not m["effects"] or changed <= covered, "expected_after omits changed companion factory files: " + ", ".join(sorted(changed - covered)))
        for eid, effect in m["effects"].items():
            factory.require(effect["input"] == m["postimages"] and isinstance(expected.get(eid), dict) and expected[eid], "configuration effect needs exact expected_after postimages")
            hashes = {}
            for ref, sha in expected[eid].items():
                factory.require(ref in {"_shared/" + n for n in ("policy.json", "claims.json", "taxonomy.json", "icp.md", "adapters.md")}, "configuration target must be a canonical factory file")
                staged = self.file(str(Path(m["postimages"]) / Path(ref).name))
                factory.require(digest(staged) == sha, "postimage hash differs: " + ref)
                hashes[ref] = sha
            self.effects[eid] = {"kind": "configuration", "input": m["postimages"], "payload": hashes}

    def arr(self):
        import arr_growth_gate
        factory.require(self.arr_packet is not None, "ARR preflight requires transient stdin input")
        receipt = self.read(self.manifest["receipt"])
        factory.require(receipt.get("retention_authorized") is True and receipt.get("success") is True
                        and receipt.get("input_reference_kind") == "immutable_snapshot"
                        and factory.nonblank(receipt.get("reference")) and factory.nonblank(receipt.get("immutable_input_reference")),
                        "authorized immutable adapter input receipt required")
        factory.require(self.arr_packet.get("immutable_input_reference") == receipt["immutable_input_reference"], "financial preimage changed; fresh review required")
        previous = _ARR_PREIMAGES.get((str(self.root), self.path.name))
        current = hashlib.sha256(json.dumps(self.arr_packet, sort_keys=True).encode()).digest()
        factory.require(not self.compare_arr or previous is None or previous == current, "in-memory financial preimage changed; fresh review required")
        today = self.now.astimezone(ZoneInfo(self.policy["identity"]["timezone"])).date()
        result = arr_growth_gate.check(self.arr_packet, self.policy, today, self.shared)
        safe = {"verdict": result["verdict"], "data_through_date": result.get("data_through_date"),
                "receipt": receipt["reference"], "immutable_input_reference": receipt["immutable_input_reference"],
                "financial_inputs": "transient_not_replayable", "query_count": len(self.arr_packet.get("rows", [])),
                "selected": [{k: r[k] for k in ("account_id", "draft")} for r in result.get("selected", [])],
                "held": [{k: r[k] for k in ("account_id", "hold")} for r in result.get("held", [])], "shortfall": result.get("shortfall")}
        drafts = self.manifest.get("drafts", [])
        factory.require(isinstance(drafts, list), "drafts must be a list")
        selected = {r["account_id"]: r["draft"] for r in safe["selected"]}
        factory.require(len(drafts) == len(selected), "proposed accounts differ from selected accounts")
        seen = set()
        for row in drafts:
            account, ref = row["account_id"], row["draft"]
            factory.require(account in selected and account not in seen and self.read(ref) == selected[account], "selected draft/account differs from proposed draft")
            seen.add(account)
            self.bind(ref, "draft", {"account_id": account, **selected[account]})
            for eid, effect in self.effects.items():
                if effect["input"] == ref:
                    self.exports[ref] = {"eligible": True, "kind": "draft", "effect_id": eid, "account_id": account, "payload": selected[account], "artifacts": [ref, self.manifest["receipt"]]}
        self.checks["arr"] = safe

    def run(self):
        method = {"signal-scan": self.scan, "signal-prospector": self.prospector,
                  "signal-outreach": self.outreach, "signal-followup": self.followup,
                  "signal-user-scan": self.adoption, "prospect-setup": self.configuration,
                  "signal-refresh": self.configuration, "signal-arr-growth": self.arr}[self.workflow]
        self.attempt(self.workflow, method)
        missing = sorted(set(self.manifest["effects"]) - set(self.effects))
        if missing:
            self.issues.append("Effects lack passing prerequisites: " + ", ".join(missing))
        if not self.manifest["effects"] and self.issues and not self.manifest["gaps"]:
            self.issues.append("A partial report requires explicit inputs.gaps")
        allowed = not missing and (bool(self.manifest["effects"]) or not self.issues or bool(self.manifest["gaps"]))
        return {"contract_version": VERSION, "checked_at": self.now.isoformat(), "workflow": self.workflow,
                "run_id": self.path.name, "reviewable": allowed, "issues": self.issues, "checks": self.checks,
                "effects": self.effects, "exports": self.exports, "handoff_eligible": bool(self.exports), "inputs": self.inputs}


def preflight(root, path, workflow, proposed, source=None, arr_packet=None, now=None, compare_arr=True):
    if arr_packet is not None and workflow != "signal-arr-growth":
        raise ValueError("--arr-packet is only supported for signal-arr-growth")
    return Check(root, path, workflow, proposed, source, arr_packet, now, compare_arr).run()
