"""Static SQL contracts plus a SQLite relational fixtures for discovery and ARR. No warehouse is touched.

The fixture substitutes equivalent scalar/boolean functions; it does not validate Snowflake syntax or schemas.
"""
import _support
from datetime import date, timedelta
import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_shared" / "scripts"
QUERIES = {
    "adoption_lookup.sql": ROOT / "workflows/signal-user-scan/adoption_lookup.sql",
    "adoption_territory.sql": ROOT / "workflows/signal-prospector/adoption_territory.sql",
    "arr_growth_source.sql": ROOT / "workflows/signal-arr-growth/arr_growth_source.sql",
}


def split(sql):
    header = [l for l in sql.splitlines() if l.startswith("--")]
    body = "\n".join(l.split("--")[0] for l in sql.splitlines() if not l.startswith("--"))
    return "\n".join(header), re.sub(r"'[^']*'", "''", body)   # string literals hold regex ? marks


class SqlContracts(unittest.TestCase):
    def test_header_bindings_match_placeholders(self):
        for name in QUERIES:
            header, body = split(QUERIES[name].read_text())
            declared = {int(n) for n in re.findall(r"\?(\d)", header)}
            self.assertEqual(declared, set(range(1, len(declared) + 1)), name)
            self.assertEqual(body.count("?"), len(declared), name)

    def test_adoption_lookup_lists_never_null(self):
        sql = QUERIES["adoption_lookup.sql"].read_text()
        for col in ("org_service_types", "org_platforms"):
            self.assertRegex(sql, rf"COALESCE\(\(SELECT LISTAGG\(DISTINCT \w+, ','\) FROM org_sub\), ''\)\s+AS {col}")
        self.assertIn("empty string means none", sql.lower())

    def test_adoption_lookup_counts_only_live_orgs(self):
        sql = QUERIES["adoption_lookup.sql"].read_text()
        org_map = sql.split("org_map AS (")[1].split("),")[0]
        self.assertIn("o.is_deleted = FALSE", org_map)

    def test_adoption_territory_lowercases_before_stripping_scheme(self):
        sql = QUERIES["adoption_territory.sql"].read_text()
        self.assertIn("REGEXP_REPLACE(LOWER(TRIM(a.website)), '^https?://', '')", sql)
        self.assertNotRegex(sql, r"LOWER\(REGEXP_REPLACE")
        self.assertIn("signals.md admission", sql)

    def test_arr_growth_header_states_drop_rule(self):
        sql = QUERIES["arr_growth_source.sql"].read_text()
        self.assertIn("Dropped orgs are not reported", sql)
        self.assertIn("Dropped orgs are not reported", (SHARED / "policy.yaml").read_text())

    def test_arr_query_excludes_non_usd_and_incomplete_daily_units(self):
        db = sqlite3.connect(':memory:'); self.addCleanup(db.close)
        db.row_factory = sqlite3.Row
        db.create_function('TO_DATE', 1, lambda value: value)
        db.create_function('TO_CHAR', 2, lambda value, fmt: value)
        db.create_function('DATEADD', 3, lambda unit, days, value: (date.fromisoformat(value) + timedelta(days=days)).isoformat())
        db.executescript("""
          CREATE TABLE account (id TEXT, owner_id TEXT, is_deleted BOOL);
          CREATE TABLE organizations (organization_uuid TEXT, billing_email TEXT, outreach_permitted BOOL, is_deleted BOOL, service_type TEXT);
          CREATE TABLE organization_account_map (organization_uuid TEXT, crm_account_id TEXT, is_unambiguous BOOL);
          CREATE TABLE organization_subscription_daily (organization_uuid TEXT, snapshot_date TEXT, organization_name TEXT, subscription_platform TEXT, annual_recurring_revenue REAL, currency TEXT);
          INSERT INTO account VALUES ('account-123', 'owner-123', FALSE);
          INSERT INTO organizations VALUES ('org-1', 'billing@buyer.example', TRUE, FALSE, 'SELF_SERVE');
          INSERT INTO organization_account_map VALUES ('org-1', 'account-123', TRUE);
          INSERT INTO organization_subscription_daily VALUES
            ('org-1', '2026-09-20', 'Buyer', 'web', 1200, 'USD'),
            ('org-1', '2026-09-21', 'Buyer', 'web', 1800, 'USD'),
            ('org-1', '2026-09-22', 'Buyer', 'web', 2400, 'USD');
        """)
        # Adapt only dialect functions; exercise the shipped query's grouping/filtering.
        sql = QUERIES['arr_growth_source.sql'].read_text().replace('prospect_source.', '')
        sql = sql.replace('BOOLAND_AGG(', 'MIN(').replace('DATEADD(day,', "DATEADD('day',")
        def rows():
            return db.execute(sql, ('2026-09-22', 2, 'owner-123', 20)).fetchall()
        result = rows()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['currency'], 'USD')
        self.assertEqual(result[0]['net_change_usd'], 1200)
        for currency in ('EUR', 'GBP', None, ''):
            with self.subTest(currency=currency):
                db.execute('UPDATE organization_subscription_daily SET currency = ?', (currency,))
                self.assertEqual(rows(), [])
        db.execute("UPDATE organization_subscription_daily SET currency = 'USD'")
        db.execute("UPDATE organization_subscription_daily SET currency = 'EUR' WHERE snapshot_date = '2026-09-21'")
        self.assertEqual(rows(), [])
        db.execute("UPDATE organization_subscription_daily SET currency = 'USD'")
        self.assertEqual(len(rows()), 1)

    def test_discovery_domain_uniqueness_and_deleted_org_behavior(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.create_function("TO_DATE", 1, lambda value: value)
        db.create_function("TO_CHAR", 2, lambda value, fmt: value)
        db.create_function("REGEXP_REPLACE", 3, lambda value, pattern, replacement:
                           re.sub(pattern.replace("\\\\", "\\"), replacement, value))
        db.executescript("""
          CREATE TABLE account (id TEXT, name TEXT, owner_id TEXT, number_of_employees INT, website TEXT, is_deleted BOOL);
          CREATE TABLE user_domains (user_id TEXT, email_domain TEXT);
          CREATE TABLE paid_individual_subscription_daily (user_id TEXT, snapshot_date TEXT, is_paying BOOL);
          CREATE TABLE organizations (organization_uuid TEXT, is_deleted BOOL);
          CREATE TABLE organization_account_map (organization_uuid TEXT, crm_account_id TEXT, is_unambiguous BOOL);
          CREATE TABLE organization_subscription_daily (organization_uuid TEXT, snapshot_date TEXT, is_subscribed BOOL);
          INSERT INTO account VALUES ('001A', 'Acme', 'SELLER', 1000, 'HTTPS://www.Acme.example/path', FALSE);
          INSERT INTO user_domains VALUES ('synthetic-user', 'acme.example');
          INSERT INTO paid_individual_subscription_daily VALUES ('synthetic-user', '2026-09-24', TRUE);
        """)
        sql = QUERIES["adoption_territory.sql"].read_text().replace("prospect_source.", "").replace("prospect_source.", "")
        sql = sql.replace("BOOLOR_AGG(", "MAX(")
        def rows():
            return db.execute(sql, ("2026-09-24", "SELLER", 200, 5000, 20)).fetchall()
        self.assertEqual([row[0] for row in rows()], ["001A"])
        # Another owner's small Account must still make the shared domain ambiguous.
        db.execute("INSERT INTO account VALUES ('001B', 'Other buying entity', 'OTHER', 10, 'https://acme.example', FALSE)")
        self.assertEqual(rows(), [])
        db.execute("UPDATE account SET is_deleted = TRUE WHERE id = '001B'")
        self.assertEqual([row[0] for row in rows()], ["001A"])
        db.execute("INSERT INTO organizations VALUES ('org-1', TRUE)")
        db.execute("INSERT INTO organization_account_map VALUES ('org-1', '001A', TRUE)")
        db.execute("INSERT INTO organization_subscription_daily VALUES ('org-1', '2026-09-24', TRUE)")
        self.assertEqual([row[0] for row in rows()], ["001A"])
        db.execute("UPDATE organizations SET is_deleted = FALSE")
        self.assertEqual(rows(), [])


if __name__ == "__main__":
    unittest.main()
