# Final Round Playbook: Managerial / Leadership Discussion

> The final leadership or managerial discussion for a DevOps Engineer role: what the round tests, rules for every answer, and plain-English scripts for the questions most likely to come up.

Leadership or managerial discussion, DevOps Engineer — for any company. This round is not a coding test — it is a judgment test. Below: the questions most likely to come up, and a plain-English script for each, built from your own resume.

Scripts are drafts built from Siva's resume. Swap in the exact numbers and details you can defend, and say only what actually happened. Priority labels: **Almost certain**, **Likely**, **Possible**.

## What this round is really testing

Two technical rounds already proved you can do the work. A leadership discussion asks a different question: can we put this person in front of a client or senior stakeholder, hand them something important, and stop worrying about it?

- **Ownership:** Do you finish things, or do you hand problems upward? They listen for “I” doing something, not “the team decided”.
- **Communication:** Can you explain a technical mess in one clear minute to someone who is not technical?
- **Judgment:** Under pressure, do you stabilise first and argue later? Do you know when to escalate?
- **Stakeholder fit:** Clients or internal stakeholders, deadlines and standards. They want calm, not clever.

---

## Five rules for every answer

1. **Use a real example, in the past tense.** “I would…” sounds like theory. “We had a situation where…” sounds like experience.
2. **Use STAR and stop at 90 seconds.** Situation, Task, Action, Result. Then stop talking. Silence is fine — let them ask the follow-up.
3. **Say “I” for your work, “we” for the team’s.** Interviewers cannot hire a “we”. Be generous about credit, but be clear about what you personally did.
4. **End on the result, with a number when you have one.** “…which cut the release lead time roughly in half.” The number is what they remember.
5. **If you don’t know, say so — then say how you’d find out.** “I haven’t used that. Here’s how I’d approach it.” Bluffing is the one thing that fails this round outright.

---

## Your 60-second opening

The first answer sets the tone for the whole hour. Rehearse this out loud until it is comfortable, not memorised.

**Say this:**

> “I’m Siva, a DevOps and Cloud engineer with about five and a half years on Microsoft Azure. I started at Infosys in 2021 as a Technology Analyst, automating Azure infrastructure for production workloads, and since January 2025 I’ve been at Impressico, where I own an Azure platform end to end.
>
> My work sits on three pillars: Infrastructure as Code with Terraform and Bicep, CI/CD across Azure DevOps, GitHub Actions and Jenkins, and running AKS in production — including zero-downtime cluster upgrades. Around that, I’ve pushed security left with scanning and policy gates in the pipelines, and built the observability side with Azure Monitor, Prometheus and Grafana. I’m AZ-400 and AZ-104 certified.
>
> What I enjoy most is taking a manual, fragile process and turning it into something repeatable that a whole team can trust — that’s where most of my results have come from.”

**Why it works:** Three pillars, one number-free promise, and a closing line that invites their next question. No college, no family, no tool dump.

---

## Motivation and the story so far

The most dangerous questions in the round, because they are the easiest to answer badly. Never criticise a current or past employer.

<details><summary>Q1. Why are you looking to change? <em>(almost certain)</em></summary>

**Why they ask:** You joined Impressico in January 2025. They want to know this is a considered move, not restlessness — and whether you speak badly about people.

**Say this:**

> “I’ve had a good run at Impressico — I own the Azure platform work end to end and I’ve grown quickly there. What I’m looking for now is scale and variety. Today I work inside one product’s boundary. In my next role I want larger and more demanding environments, more teams depending on my work, and stronger engineering standards. That’s the exposure that makes me a better engineer over the next five years. It’s a move towards something, not away from anything.”

**Avoid:** Money as the first reason. Complaints about a manager, appraisal or workload. “There’s no growth here.”

</details>

<details><summary>Q2. Why this company? <em>(almost certain)</em></summary>

**Why they ask:** They want to hear you chose them, not that you applied everywhere.

**Say this:**

> “Three reasons. Scale — you run cloud and DevOps at a size where the problems are bigger than what one product team ever sees. Standards — governance, security and compliance are non-negotiable in your work, and that’s the direction my own work has taken: policy, RBAC, least privilege, security gates inside the pipeline rather than a review at the end. And growth — this role would push me to pick up new domains quickly, and I want that pressure at this stage of my career.”

**Land it:** Swap these three reasons for what is actually true of this company, and add one specific line about its product, platform or engineering practice — read the JD, careers page and engineering blog the night before and quote something real back.

</details>

<details><summary>Q3. Walk me through your current project. <em>(almost certain)</em></summary>

**Why they ask:** This is a communication test disguised as a technical one. Can you describe an architecture in 90 seconds without losing them?

**Say this — business context, then architecture, then your ownership:**

> “The platform runs business-critical workloads on Azure. Traffic comes in through Application Gateway with WAF, into AKS where the microservices run. Data sits in Azure Database for PostgreSQL, and asynchronous work goes through Service Bus and Azure Functions. Everything is provisioned by Terraform and Bicep modules — nothing is created by hand in the portal.
>
> Code moves through Azure DevOps pipelines: build, test, then SonarQube, Trivy and Checkov gates before anything can reach an environment. Secrets live in Key Vault, accessed by managed identity, so there are no credentials in code. Monitoring is Azure Monitor and Log Analytics with KQL-based alerts, plus Prometheus and Grafana for the cluster and services.
>
> My ownership is the infrastructure code, the pipelines, cluster operations and the alerting. Happy to go deeper on any part of that.”

**Land it:** That last sentence is the trick — it hands them control and stops you rambling for ten minutes.

</details>

<details><summary>Q4. What is the hardest thing you have delivered? <em>(likely)</em></summary>

**Why they ask:** They want your best story, told with structure. Use the AKS upgrade — it has risk, method and a clean result.

| STAR | Say this |
| --- | --- |
| **Situation** | “Our AKS clusters were approaching the end of support on their Kubernetes version, and those clusters host business-critical services with a 99.9% availability commitment.” |
| **Task** | “I had to upgrade production without a maintenance window — the business would not accept downtime for it.” |
| **Action** | “I automated the upgrade using Bicep with Shell and Python: control plane first, then node pools one at a time. New nodes come up, workloads are cordoned and drained onto them, and only then are the old nodes removed. Before touching production I made sure pod disruption budgets and readiness probes were correct, because those are what actually protect live traffic. Then I rehearsed the whole sequence in dev and staging.” |
| **Result** | “Production upgraded with zero downtime and no customer impact — and because it was automated, every upgrade cycle since has used the same path instead of being a manual one-off.” |

**Expect the follow-up:** “What if a pod refuses to drain?” — “The disruption budget is blocking the eviction, usually because replicas are too low. You fix the replica count or the budget; you only force it inside an agreed window.”

</details>

<details><summary>Q5. Why should we hire you over another candidate? <em>(likely)</em></summary>

**Why they ask:** A confidence check. They want a short, specific claim — not modesty and not a boast.

**Say this:**

> “I won’t claim I know more Azure than everyone you’re interviewing. What I’d point to is that I’ve owned the whole chain — infrastructure code, pipelines, cluster operations, security gates and monitoring — rather than one slice of it. That means when something breaks I can follow it from the alert to the line of Terraform that caused it. And most of what I’ve delivered has been converting manual, risky work into automation other people can run without me. That’s usually what a team needs from a senior hire.”

</details>

---

## Ownership, incidents and accountability

The heart of the round. Every answer here should show the same shape: stabilise, communicate, root-cause, then make it impossible to repeat.

<details><summary>Q6. Tell me about a production incident you handled. <em>(almost certain)</em></summary>

**Why they ask:** They are listening for calm and for sequence, not heroics.

| STAR | Say this |
| --- | --- |
| **Situation** | “One morning our alerts showed API latency climbing and pods restarting repeatedly in AKS.” |
| **Task** | “I was the one on point, and customers were already seeing slow responses.” |
| **Action** | “First I checked Grafana to see whether it was one service or the whole cluster — it was one service, memory climbing until the pod was killed and restarted. I stopped the bleeding first: rolled back to the previous image, which stabilised traffic within minutes. I posted a short update to the stakeholder channel with what we knew and when I’d update next. Then we root-caused it — a recent change wasn’t releasing connections properly.” |
| **Result** | “Customers saw a slowdown of a few minutes instead of an outage. We fixed the leak, added a memory alert at a threshold that fires before restarts, and added a resource-limits check into the pipeline so the same class of change gets caught earlier.” |

**Land it:** “My rule in an incident is simple — stabilise first, root-cause second, and then make sure it can’t happen the same way again.”

</details>

<details><summary>Q7. Tell me about a mistake you made. <em>(almost certain)</em></summary>

**Why they ask:** This is an honesty test. “I can’t think of one” is the worst possible answer — it reads as either dishonest or inexperienced.

**Say this:**

> “Early on I ran a Terraform apply assuming the plan for that run matched the plan I had reviewed earlier. It didn’t, and it removed a resource that was still in use. I raised it myself within a few minutes rather than waiting to see if anyone noticed, and we restored it inside the hour.
>
> What I changed afterwards mattered more than the fix. Plan output now gets published as a pipeline artifact with a manual approval gate before apply, so a person has to look at the actual plan for that specific run. I haven’t repeated it — and neither has anyone else on the team, because the process changed, not just my habits.”

**The shape that works:** Own it → what you did immediately → what you changed systemically. Never blame a teammate.

</details>

<details><summary>Q8. Tell me about something you improved that nobody asked you to. <em>(likely)</em></summary>

**Why they ask:** Initiative. Engineers who only do the ticket in front of them do not get promoted.

**Say this:**

> “At Infosys, granting access to a subscription or resource group was manual — someone raised a request, someone clicked through the portal, and it was usually a broad Owner or Contributor role because that was the fastest thing to do. Nobody had flagged it as a problem; it was just how it worked.
>
> I built reusable Bicep modules with custom least-privilege role definitions, so teams could request exactly the access they needed, as code. The result was that access grants became reviewable, repeatable and auditable, and a recurring manual task disappeared from the team’s week. It later became the standard way access was granted.”

</details>

<details><summary>Q9. How do you handle being on call? <em>(likely)</em></summary>

**Why they ask:** Most DevOps roles involve support rotations. They want to know you take it seriously without burning out.

**Say this:**

> “I treat every page as one of two things: a real problem or a bad alert. Both need action. If it’s real — stabilise, communicate early, then fix properly in daylight. If it was noise, I tune that alert the same week, because a noisy alert quietly trains everyone to ignore alerts, and that’s how a real one gets missed.
>
> That’s the principle behind how we route alerts now — severity-based routing through Action Groups to email, Teams and the on-call channel, so only things that genuinely need a human at 2 a.m. wake someone up.”

</details>

<details><summary>Q10. You reduced cloud spend by 25%. How? <em>(likely)</em></summary>

**Why they ask:** Cost is a leadership conversation, and it is the number on your resume they are most likely to test. Be able to explain the method and be honest that it was an estimate.

**Say this:**

> “Three levers. Visibility first — moving provisioning into Terraform and Bicep gave us a real inventory, so for the first time we could see what actually existed versus what people thought existed.
>
> Then right-sizing — a lot of VMs and scale sets had been sized for peak load and left there, so we set autoscale rules on CPU and memory and trimmed the idle capacity underneath.
>
> Then lifecycle — non-production environments were running around the clock, and orphaned disks, public IPs and old snapshots were never cleaned up. We automated both. Measured in Cost Management, it worked out to roughly 25% of annual spend.”

**Avoid:** Defending the number as if it were audited. Say “roughly” or “estimated” — precision you can’t back up is worse than a smaller honest number.

</details>

---

## Conflict, influence and communication

They are checking whether you create friction or absorb it. In every answer here, show that you argued about the goal, never about the person.

<details><summary>Q11. Tell me about a disagreement with a developer or an architect. <em>(almost certain)</em></summary>

**Why they ask:** DevOps sits between teams. They want proof you can hold a line without becoming the person everyone routes around.

| STAR | Say this |
| --- | --- |
| **Situation** | “A developer wanted a hotfix pushed straight to production, bypassing the security scan gate, because the scan was failing on a vulnerability in the base image.” |
| **Task** | “I didn’t want to lose the gate, and he had a genuine deadline. Arguing about policy in a group channel would have helped nobody.” |
| **Action** | “I asked him what the actual deadline was — a few hours. Then I gave him two options instead of a refusal: bump the base image, which I estimated at about an hour, or take a documented, time-boxed exception with the risk written down and approved. He chose the base image fix, and I helped him do it.” |
| **Result** | “The fix went out on time, the gate stayed intact, and we didn’t carry an unlogged exception into production.” |

**Land it:** “I don’t try to win disagreements by escalating. I win them by giving the other person a workable option.”

</details>

<details><summary>Q12. How did you get a resistant team to adopt IaC or security gates? <em>(likely)</em></summary>

**Why they ask:** Senior DevOps work is mostly change management. Tools are easy; people are not.

**Say this:**

> “People resist a gate when it feels like a blocker rather than help, so I did three things. I started the scans in warning mode instead of failing mode, so the team could see what would break before anything actually broke. I fixed the first batch of findings myself, so they weren’t handed a wall of red and told it was their problem. And then I showed them the trend — deployments failing less often, rollbacks getting rarer.
>
> Once they could see it made their week easier, the gates stopped being my policy and started being theirs. That’s the only version of adoption that survives after I move on.”

</details>

<details><summary>Q13. How would you explain a technical failure to a non-technical stakeholder? <em>(almost certain)</em></summary>

**Why they ask:** This is the single most important skill in the stakeholder-facing part of the job.

**Say this — impact, cause, plan, in that order:**

> “I lead with impact, then cause, then the plan, and I leave the jargon out. So instead of ‘the pods were OOM-killed and the readiness probe failed’, I’d say: ‘the service ran out of memory and restarted, so some users saw slow responses for about ten minutes. We’ve rolled back the change and everything is normal now. We’ve found the cause and we’re fixing it properly this week, with a new alert so we catch it earlier next time.’
>
> Then I offer the detail if they want it. A manager needs three things — how bad, why, and when it’s fixed. Everything else is optional.”

</details>

<details><summary>Q14. Tell me about critical feedback you received. <em>(likely)</em></summary>

**Why they ask:** Coachability. Seniors who cannot take feedback are expensive.

**Say this:**

> “A lead told me my documentation assumed too much — that I was building things nobody could run without me in the room. It stung a bit, but it was fair. I started writing short READMEs that explain the ‘why’ and not just the commands, and doing a live walkthrough whenever I hand something over. It made my handovers faster too, so it helped me as much as the team.”

</details>

<details><summary>Q15. Two people on your team disagree. What do you do? <em>(possible)</em></summary>

**Why they ask:** A soft lead-role question. It signals they are sizing you for more than an individual contributor seat.

**Say this:**

> “I get both positions written down as options with their trade-offs, then I ask what we’re actually optimising for — usually it’s either reliability or a delivery date, and it can’t be both. We decide against that. If it’s genuinely a coin flip, we pick one, time-box it and agree what evidence would make us change our minds. Most technical arguments drag on because nobody defined the deciding criteria, not because the people are difficult.”

</details>

---

## Pressure, priorities and delivery

The panel is asking one thing underneath all of these: when the deadline and the right thing pull in opposite directions, what do you do — and do you tell anyone?

<details><summary>Q16. Everything is priority one. How do you decide what to do first? <em>(almost certain)</em></summary>

**Why they ask:** They want a repeatable rule, not “I work hard”.

**Say this:**

> “I sort by blast radius and by who’s blocked. Anything affecting customers or production stability goes first — that’s not negotiable. Second is anything blocking other people: a broken pipeline blocks a whole team, so it beats my own task even if mine is more interesting. Third is planned work.
>
> And I say out loud what I’m not doing. The failure mode isn’t picking the wrong order — it’s someone waiting quietly on something I’ve deprioritised without telling them.”

</details>

<details><summary>Q17. A deadline is tight and quality will suffer. What do you do? <em>(almost certain)</em></summary>

**Why they ask:** The classic delivery trade-off. They are checking whether you cut corners silently.

**Say this:**

> “I don’t quietly cut quality — I make the trade-off visible and let the person who owns the risk decide. So I’ll say: we can hit Friday with scope A and B; C needs the following week; if we force all three, here is the specific risk. In my experience most stakeholders pick the smaller scope over a risky release, because they’d rather ship less than roll back in front of their own customers.
>
> What I won’t do is skip the tests and hope. If someone still wants it, that’s their call to make with the risk in writing — not mine to make silently.”

</details>

<details><summary>Q18. Tell me about a time you worked under real pressure. <em>(likely)</em></summary>

**Why they ask:** They want to see your temperature drop, not rise, when it matters.

**Say this — reuse the AKS upgrade or the incident, and emphasise the calm:**

> “The AKS production upgrade was the highest-pressure piece of work I’ve done — a version approaching end of support, business-critical services on it, and no maintenance window available. The pressure was mostly that a mistake would be visible to customers immediately.
>
> What kept it calm was preparation rather than nerve: I rehearsed the full sequence in dev and staging, verified the disruption budgets and probes beforehand, and had a rollback position for each node pool. The production run itself was almost boring, which is exactly what you want. Pressure is usually a sign you haven’t rehearsed enough.”

</details>

<details><summary>Q19. You’re asked to do something you think is a bad idea. Then what? <em>(likely)</em></summary>

**Say this:**

> “I ask why before I push back — often there’s a constraint I don’t know about, like a client commitment or an audit date, and once I know it my objection sometimes disappears. If I still disagree, I state the risk in the language they care about: cost, downtime, or audit exposure. Then I offer an alternative rather than just a ‘no’.
>
> If the decision is still theirs and it isn’t a safety or security issue, I commit to it properly and note the risk. I don’t agree in the meeting and then drag my feet — that’s worse than disagreeing.”

**Land it:** “Disagree and commit — but write the risk down.”

</details>

---

## Self-awareness, growth and team

<details><summary>Q20. What are your strengths and weaknesses? <em>(almost certain)</em></summary>

**Why they ask:** A fake weakness (“I work too hard”) fails this. A real weakness with a real correction passes it.

**Say this:**

> “Strength: I automate the thing rather than getting good at doing it manually. Almost everything I’ve delivered has been turning a repeated manual process into code, and that’s where I add the most value to a team.
>
> Weakness: I used to over-engineer before showing anyone. I’d want the solution to be complete before it was reviewed, and that cost time and occasionally meant building something slightly wrong for longer than necessary. I now share a rough working version early and let people react to it. It’s not fully fixed — it’s still my instinct — but I catch it now.”

</details>

<details><summary>Q21. Where do you see yourself in three to five years? <em>(almost certain)</em></summary>

**Say this:**

> “Technically deeper and one step wider. I want to move from building platforms to designing them — a lead or architect role — and I want to be someone who can be put in front of clients or senior stakeholders, not just given a backlog. Practically that means more platform design, more multi-cloud, and more mentoring. That’s a large part of why this role appeals to me.”

**Avoid:** “I want to start my own thing” or anything that sounds like a two-year stop.

</details>

<details><summary>Q22. Have you mentored anyone? <em>(likely)</em></summary>

**Why they ask:** At five-plus years, they expect you to be lifting others, not just delivering yourself.

**Say this:**

> “I’ve onboarded junior engineers onto our Terraform and pipeline work. I don’t hand over a list of commands — I pair on the first change, let them drive the second while I watch, then just review the third. It’s slower for the first week and much faster after that. The measure I care about is whether they can make an infrastructure change without me in the room, and they can.”

</details>

<details><summary>Q23. How do you keep your skills current? <em>(likely)</em></summary>

**Say this:**

> “Certifications give me structure — I’ve done AZ-900, AZ-104 and AZ-400, and preparing for AZ-400 in particular forced me across parts of Azure DevOps I wouldn’t have touched otherwise. Beyond that it’s hands-on: I keep a personal subscription and rebuild things there rather than only reading about them, and I follow the AKS and Terraform release notes, because in this job the breaking changes matter more than the feature announcements.”

**Land it:** Be ready to name one thing you learned recently and what you did with it. Vagueness here is obvious.

</details>

<details><summary>Q24. What would your current manager say about you? <em>(possible)</em></summary>

**Say this:**

> “That I own things end to end and he doesn’t have to follow up with me — if I’ve taken something, it gets closed. And probably that I’ll tell him when I think something is a bad idea. Politely, but I’ll say it. I think he’d count that as a positive most days.”

</details>

---

## Client and stakeholder fit

Essential at consulting and services firms. At a product company, read “client” as the business owner or internal team you support — the same answers work. Answer with evidence, not enthusiasm.

<details><summary>Q25. Are you comfortable in a client-facing role? <em>(almost certain)</em></summary>

**Say this:**

> “Yes — and I’d define it narrowly, because ‘client-facing’ can sound vague. In practice it’s three habits: say what you’ll do and by when, flag a slip early rather than late, and never let a client be surprised in a status call. I already run releases and incident updates with stakeholders directly, so that part isn’t new to me. What would be new is doing it for an external client with a contract behind it, and I’d expect to be more careful about what I commit to, not less.”

</details>

<details><summary>Q26. A client is angry and blaming your team. What do you do? <em>(almost certain)</em></summary>

**Why they ask:** The most revealing question in the whole round. They want to see that you don’t get defensive.

**Say this:**

> “Listen first and don’t defend. Acknowledge the impact plainly — ‘you’re right, this hit your release, and I understand why that’s a problem for you.’ That takes most of the heat out immediately.
>
> Then separate what I know from what I don’t, and say both. Give them a next update time and actually hit it, even if the update is ‘still investigating’ — missing a promised update is what turns frustration into distrust. Then fix the underlying thing and show them it’s fixed rather than telling them.
>
> Most client anger I’ve seen isn’t really about the outage. It’s about not being told.”

</details>

<details><summary>Q27. A client asks for something that breaks a security standard. Then what? <em>(likely)</em></summary>

**Say this:**

> “Understand the need first — usually there’s a legitimate goal behind the bad request. Then explain the risk in their language, not mine: not ‘that violates RBAC least privilege’ but ‘that gives twelve people the ability to delete production, and it will come up in your next audit.’ Then offer a compliant alternative that gets them the outcome.
>
> If they still want it, I escalate through my lead rather than saying a flat no on my own authority — that’s not my call to make alone. What I won’t do is quietly weaken a control to keep someone happy.”

</details>

<details><summary>Q28. What if you’re staffed on AWS or GCP instead of Azure? <em>(likely)</em></summary>

**Why they ask:** Companies staff you where the demand is, and stacks change. They need to know you won’t stall.

**Say this:**

> “That’s fine, and I’d expect to be productive in weeks rather than months. The concepts carry across — networking, identity and least privilege, pipelines, containers, infrastructure as code. The names change; the discipline doesn’t. Terraform is provider-agnostic, so the modules are different but the workflow I already run is the same. I made a similar jump when I moved from VM-centric work into Kubernetes and AKS, and that ramp took a few weeks of deliberate hands-on work.”

</details>

<details><summary>Q29. Are you okay with shifts, on-call, travel or office presence? <em>(likely)</em></summary>

**Say this — be honest, then flexible:**

> “Yes to on-call rotations and to overlapping hours where a client needs it — that comes with the job and I’ve done it. On location and travel, I’d want to understand the actual pattern rather than agree to something vague, but I don’t have a constraint that would stop me.”

**Land it:** Never say “no” outright here, and never pretend to be fine with something you aren’t — it will surface in week three.

</details>

---

## Resume defence: the numbers they will test

A leadership round probes the claims rather than the tools. For each number, know the method and the honest caveat. “I’m not sure how it was measured” is a bad look on your own resume line.

| Your claim | One-line proof | The follow-up |
| --- | --- | --- |
| ~25% cost cut | IaC inventory → right-sizing and autoscale → lifecycle cleanup of idle non-prod, orphaned disks, IPs and snapshots. Measured in Cost Management. | “Over what period, and against what baseline?” |
| ~50% faster lead time | Parallel stages, build caching, standard pipeline templates, and removing manual handoffs between build and deploy. | “What was it before, and what is it now?” |
| ~40% fewer deploy failures | Quality gates plus IaC-identical environments — most failures were config drift between staging and production. | “What was actually failing before?” |
| 99.9% availability | Multi-node-pool AKS, autoscaling, pod disruption budgets, zero-downtime upgrades, alerting that fires before users notice. | “Who measured that, and did you ever miss it?” |
| Zero-downtime AKS upgrade | Control plane first, then node pools one at a time — surge new nodes, cordon and drain, remove old. Probes and PDBs verified first. | “What happens if a pod won’t evict?” |
| Shift-left security | SonarQube for code, Trivy for images, Checkov for IaC, secret scanning, Azure Policy — all as pipeline gates, not a review at the end. | “What happens when a gate fails a release on a Friday?” |

---

## Closing: notice, offer, and the questions you ask

<details><summary>Q30. What is your notice period, and when can you join? <em>(almost certain)</em></summary>

**Say this:**

> “My notice period is [X] days. I’d serve it properly and hand over cleanly — but I’ll also ask about a buy-out or an early release once I have an offer in hand, and I’ll keep you updated on the actual date rather than letting it drift.”

**Land it:** Offering a clean handover reads as loyalty they’ll one day benefit from. Never say “I can leave immediately.”

</details>

<details><summary>Q31. What are your salary expectations? <em>(almost certain)</em></summary>

**Why they ask:** Usually a fit check against the band they already have, not a negotiation. Stay calm and factual.

**Say this:**

> “My current fixed is [X]. Based on the role, my Azure and AKS ownership and my AZ-400, I’m looking in the range of [Y to Z]. I’d also like to understand the band for this position — if the overall package works, I’m flexible on how it’s structured.”

**Before the interview:** Decide your three numbers in advance and write them down: the number you’d be pleased with, the number you’d accept, and the number you’d decline. Then you are never doing arithmetic in the room.

**Avoid:** Inflating your current salary — offer letters and payslips get verified. And don’t give a single point number when a range serves you better.

</details>

<details><summary>Q32. Do you have any questions for us? <em>(almost certain)</em></summary>

**Why they ask:** “No, I think you covered everything” is read as low interest. Ask two or three. Have five ready.

- “What does the first 90 days look like — joining existing work, or building something new?”
- “How is the DevOps team structured — embedded in delivery teams, or a central platform team the projects consume?”
- “How much of the work is Azure versus multi-cloud right now?”
- “What separates someone who does really well in this role from someone who struggles?”
- “What’s the biggest engineering challenge the team is dealing with at the moment?”
- “How does the team support certifications and skill growth?”

**Then close:** “Thanks — this sounds like the kind of work I want to be doing. Is there anything about my background you’d like me to clarify before we finish?” It gives them one last chance to raise a doubt while you’re still in the room to answer it.

</details>

---

## Six ways people lose this round

- **Criticising the current employer:** Even mildly. The interviewer immediately imagines you describing them the same way in two years.
- **“We” for everything:** They cannot hire a team. If you never say “I did”, they cannot tell what you actually did.
- **Answering with a hypothetical:** “I would handle it by…” when they asked for a time you did. Always reach for a real example.
- **Rambling past two minutes:** Give the answer, then stop. Trailing off into more detail undoes a good answer.
- **A number you can’t explain:** If it’s on your resume, you own it. Know the method or soften the claim before they test it.
- **Bluffing:** One invented answer costs more than ten honest “I haven’t used that, but here’s how I’d approach it.”

---

## The night before

- [ ] Read every line of your resume — assume all of it is fair game
- [ ] Rehearse the 60-second intro out loud, twice
- [ ] Pick your three strongest stories: AKS upgrade, the incident, the cost reduction
- [ ] Write down your three salary numbers
- [ ] Read the JD, the company’s engineering pages and recent news so “why this company” has a specific fact in it
- [ ] Three printed resume copies, photo ID, a notepad and a pen
- [ ] Confirm the address and travel time; plan to arrive 20 minutes early
- [ ] Formal dress, phone on silent before you enter the building

**One last thing:**

> Two technical rounds are already cleared, so they believe you can do the job. This round is them checking what you’re like to work with on a bad day. Slow down, answer in structure, and let a pause sit — measured beats fast in a leadership discussion, every time.
