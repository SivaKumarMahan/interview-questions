# Git: Branching Strategies and Releases

> Gitflow and other branching strategies for larger teams, hotfixes, representing environments in Git, and release tags.

## Interview Questions

<details><summary>Q1. [Basic] Explain the Gitflow branching strategy.</summary>

**Answer:**

Gitflow uses two long-lived branches: `main` and `develop`. Feature branches start from `develop`. A release branch stabilizes a planned version. When a release is done, it merges into both `main` and `develop`. Urgent production fixes get their own hotfix branches, started from `main`.

```text
main ────────────────●────────────●
                     \ hotfix     /
develop ──●──●──●────●───────────●
           \ feature / \ release /
```

It gives you explicit control over releases, which suits products with scheduled versions or several supported releases at once. The downside is extra merge overhead and branches that drift apart the longer they stay open.

For teams delivering continuously, trunk-based development with short feature branches and feature flags is usually simpler. I pick a strategy based on release frequency, regulatory requirements, team size, and how long releases need to be supported — not by defaulting to Gitflow.

</details>

<details><summary>Q2. [Intermediate] What branching strategy would you recommend for a team of more than 20 developers?</summary>

**Answer:**

First, I'd ask about release frequency, how many versions need support at once, regulatory approvals, repository ownership, and whether incomplete work can just hide behind a feature flag. Team size alone doesn't decide the strategy.

For frequent delivery, I prefer trunk-based development: short-lived branches, small pull requests, a protected `main`, mandatory automated checks, a merge queue, and feature flags. This cuts down long-running conflicts and integration risk.

For scheduled releases or several supported versions at once, I add release branches with clear owners and a limited lifespan.

I track lead time, how long pull requests stay open, change-failure rate, how often conflicts happen, and rollback time. If branches sit open for weeks, that's a sign the process itself is creating integration risk.

CODEOWNERS, component-level tests, and clearly defined repository boundaries help a large team work independently without weakening code review.

</details>

<details><summary>Q3. [Intermediate] What branching strategy do you follow / recommend for a 20+ dev team? (justify) <em>(asked in interview round)</em></summary>

Here are the common options and when each one makes sense:

- **Trunk-based development (recommended for large, fast-moving teams):** everyone commits to short-lived branches and merges to `main` quickly, within a day or two. Unfinished work stays hidden behind feature flags instead of a long-lived branch. This needs strong CI and good test coverage. I recommend it because it avoids messy merges and long branch divergence, and it scales well with many contributors.
- **GitHub Flow:** `main` plus short-lived feature branches, a pull request, then deploy. Simple, and works well for web apps deployed continuously.
- **GitFlow:** uses `main`, `develop`, `feature/*`, `release/*`, and `hotfix/*` branches. Good for scheduled releases or versioned products, but it is heavy and slow for continuous delivery.

For a 20+ dev team doing continuous delivery, I recommend trunk-based development with feature flags, pull request reviews, and strong CI with branch protection. It keeps integration continuous and avoids the long-lived branches that GitFlow tends to create.

</details>

<details><summary>Q4. [Intermediate] What branching strategy keeps releases clean, and how do you handle a production hotfix?</summary>

**Answer:**

For frequent delivery, I prefer protected trunk-based development: short-lived branches, small pull requests, mandatory checks, and feature flags. I only create a release branch when a supported release needs to be stabilized. New feature work keeps going on `main`, while the release branch accepts only approved fixes.

For a hotfix, I branch from the exact production tag, make the smallest change that fixes the issue, get it reviewed, build a new version that won't change once created, and deploy it through the emergency pipeline — which is still audited.

Then I merge or cherry-pick the fix back into `main` and any release branches still being supported, so it isn't lost in the next release.

I tag the fixed release and document the incident.

The branch itself doesn't guarantee stability — the controls around it do. I require reproducible builds, tests, security checks, code owners, traceable approvals, and a verified rollback path. I also delete or close stale release branches so they don't drift out of sync.

</details>

<details><summary>Q5. [Intermediate] How should Dev, QA, UAT, and Production be represented in Git?</summary>

**Answer:**

I avoid permanent environment branches that hold different versions of the application code, because merging between them creates drift and makes it unclear what's actually in a release. Application code should normally live on one protected main branch, with release tags that don't change once created.

The same built artifact then gets promoted through Dev, QA, UAT, and Production — nothing gets rebuilt along the way.

Environment-specific configuration can live in clearly separated directories or repositories, with protected pull requests and environment owners. Promoting to the next environment just changes the image digest or chart version there — it doesn't rebuild the source.

Secrets stay as external references, never checked into the repo.

If an organization insists on environment branches, I define one-way promotion, automated comparison between environments, branch protection, and rules that block direct commits to production. But I'd also explain the drift risk this creates and push toward artifact-based promotion instead.

</details>

<details><summary>Q6. [Basic] How do you handle release tags?</summary>

**Answer:**

I create an annotated tag on the exact reviewed commit that was used to build the release. Once created, a tag like this should never change — that's what makes it trustworthy as a release marker. Semantic versioning, like `v2.4.1`, makes compatibility clear at a glance.

```bash
git tag -a v2.4.1 -m "Release 2.4.1"
git push origin v2.4.1
git show v2.4.1
```

CI builds a versioned artifact or image and records the commit SHA, tag, checksums, and release notes. Promoting to production reuses that same artifact rather than rebuilding from a branch that keeps moving.

I restrict who can create or delete tags, sign tags when required, and never quietly move a published release tag. If something needs fixing, it gets a new version instead.

</details>
