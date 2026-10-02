# My Projects

> How to turn your own projects into strong STAR answers for Senior and Lead DevOps interviews, and a template file per project to fill in.

## What These Files Are For

Interviewers at senior and lead level almost always ask "Tell me about a project you led" and then go deep with follow-up questions. These files are **templates**. They hold the structure and the likely follow-up questions; the real facts must come from you.

Every place that needs your real story is marked `TODO (Siva):`. Nothing in these files is an invented fact about your work. Replace every TODO before you rely on a file in an interview.

## The STAR Format

| Letter | Meaning | What to say | Rough share of the answer |
| --- | --- | --- | --- |
| **S** | Situation | The context: the system, the team, the problem, why it mattered | ~15% |
| **T** | Task | Your specific responsibility and the goal or constraint | ~10% |
| **A** | Action | What **you** did, step by step, and why you chose that approach | ~55% |
| **R** | Result | The outcome, with numbers, plus what you learned | ~20% |

Most people spend too long on the Situation and rush the Action and Result. The Action is where the interviewer judges your skill. The Result is where they judge your impact.

A two-minute answer is usually right for the first telling. Let the interviewer pull you deeper with follow-up questions.

## Tips for Lead-Level Answers

- **Quantify results.** "Reduced alert noise by about 60%" beats "reduced alert noise". If you do not have an exact number, give an honest estimate and say it is an estimate. Good metrics: time saved per week, MTTD or MTTR change, cost per month, incidents per quarter, manual steps removed, adoption by number of teams.
- **Show trade-offs.** Say which options you considered and why you rejected them. "We considered X, but it needed Y, so we chose Z." This is what separates a lead answer from a senior engineer answer.
- **Be clear about your role vs the team.** Use "I" for what you did and "we" for what the team did. Interviewers listen for this. Do not take credit for others' work, and do not hide your own behind "we".
- **Show influence, not only implementation.** Who did you convince? Which teams adopted it? How did you handle disagreement?
- **Include what went wrong.** One honest problem and how you handled it makes the story believable.
- **End with the lesson.** "Next time I would ..." shows reflection.
- **Prepare the diagram.** Be ready to sketch the architecture on a whiteboard in under two minutes.

## How to Use the Project Files

1. **Fill in Situation, Task, Action, Result** in each file. Keep each section to a few bullets.
2. **Draw the real architecture.** Replace the placeholder Mermaid diagram with your real components.
3. **List the real tech stack** and be ready to explain why each piece was chosen.
4. **Answer every follow-up question** under Interview Questions in your own words. Use the hints to check your answer covers what interviewers look for.
5. **Practise out loud.** Time yourself: a two-minute version and a five-minute version.
6. **Check confidentiality.** Remove internal names, customer names, and anything under NDA. Describe systems generically if needed.

## Project Files

| # | Project | File |
| --- | --- | --- |
| 1 | Statuspage.io monitoring improvements | [01-statuspage-monitoring-improvements.md](01-statuspage-monitoring-improvements.md) |
| 2 | Vendor cost and renewal register feeding Splunk | [02-vendor-cost-and-renewal-register.md](02-vendor-cost-and-renewal-register.md) |
| 3 | Clone Migration Manager (Databricks Unity Catalog migration) | [03-clone-migration-manager.md](03-clone-migration-manager.md) |
| 4 | Data-factory ingest monitoring service | [04-data-factory-ingest-monitoring.md](04-data-factory-ingest-monitoring.md) |
| 5 | Databricks/Splunk monitoring dashboards | [05-databricks-splunk-monitoring-dashboards.md](05-databricks-splunk-monitoring-dashboards.md) |

See also: [Leadership](../leadership/01-architecture-decision-records.md) for how to structure behavioural answers about decisions, incidents, mentoring, and stakeholders.
