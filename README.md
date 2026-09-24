# Prospect Workflow Template

A workspace for using an AI agent to research potential business customers and
prepare relevant outreach. It works for teams selling products or services to
other businesses.

You supply information about your business and connect the tools you use. The
repo provides instructions, templates and Python checks to help the agent:

- Define your ideal customers and the claims you can support with evidence.
- Find potential customers and public events that give you a reason to reach out.
- Prepare an email based on those sources and your approved messaging.
- Create follow-up tasks after an email is actually sent.
- Keep your messaging current as its supporting sources change.

You review the findings and approve each proposed draft or CRM change. Emails
are created as **unsent drafts**; you send them yourself. Optional workflows
support subscription businesses with customer adoption and recurring-revenue data.

## Get started

1. Open a copy of this repo in an AI workspace that can read and write files and
   run Python 3.9+ and Git. See the [installation guide](setup/installation.md).
2. Tell the agent: **“Read AGENTS.md and run setup.”** Share what you sell, whom
   you want to reach, supporting materials and an example of your email voice.
   The agent can also interview you to fill in missing information.
3. Review the proposed settings and sample emails. Configure the research, CRM
   and email connections needed for your task, then choose a workflow from the
   [task list](CONTEXT.md).

You can complete messaging setup before connecting live tools. The repository
starts with fictional examples; setup prepares your own configuration for review.
See an [example review](examples/review.md) to understand the output.

## Repository map

```text
.
├── README.md                 Start here
├── AGENTS.md                 Starting instructions for AI agents
├── CONTEXT.md                Task list and links to each workflow
├── setup/                    Installation and business setup questions
├── workflows/
│   ├── research/             Find accounts and research buying signals
│   ├── outreach/             Prepare email drafts and follow-up tasks
│   ├── knowledge/            Set up and maintain supported messaging
│   └── run.md                Shared steps for review, approval and results
├── _shared/                  Common rules and example business settings
├── _templates/run/           Blank files for starting a task
├── examples/                 Fictional research and review examples
├── scripts/                  Input, evidence and workflow checks
├── tests/                    Automated tests using fictional data
├── .agents/skills/           Generated agent shortcuts
├── .claude/commands/         Generated Claude command shortcuts
├── output/                   Created locally: task inputs, reviews and results
└── AUDIT-REMEDIATION-SPEC.md  Audit findings, fixes and verification record
```

Setup creates local configuration files in `_shared/`. Each task keeps its work
in `output/{run-id}/`. Those configuration files and task outputs are excluded
from Git; the shared examples remain part of the template.

## Check or change the repo

Run these commands from the repository root:

```bash
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
```

The checks use synthetic data and do not verify live tool connections. See the
[tooling guide](scripts/CONTEXT.md) before changing workflows or generated shortcuts.

[MIT license](LICENSE).
