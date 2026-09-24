# Setup questions

Ask only what the selected workflow needs; preserve answers in their owning files.

1. Which owner, timezone and internal domains define scope? → policy.identity.
2. Which CRM/mail/calendar tools are available, how are fields mapped, and how are writes re-read? → adapters.md.
3. What follow-up timing, suppression and voice apply? → policy.followup_signal, outreach and email_voice.
4. What territory, disqualifiers, signal admission rules, personas and recipient sources apply? → the corresponding policy and ICP/taxonomy owner.
5. Which optional private-data adapters are actually available and approved for this audience? → adapters.md and their policy enabled fields.
6. Which voice anchor and private run retention are approved? → policy.email_voice and adapters.md.
7. Which product claims, evidence sources, claim limits and external proof permissions are approved? → claims.json and policy.refresh.

The example values are synthetic starter defaults. Review the configured values before live use.
