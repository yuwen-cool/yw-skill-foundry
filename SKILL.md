---
name: yw-skill-foundry
description: "Use when creating, optimizing, reviewing, or extracting reusable Agent Skills, SKILL.md, AGENTS.md, prompts, or agent instructions; or when designing instruction architecture and evals. Triggers on 写/改/审查 skill, skill 质量, 提示词工程, 指令设计, create/optimize/review skill, prompt engineering, instruction design. Not for application code, multi-agent runtime architecture, general prose, or explanation/summary/translation requests that do not create or change instructions."
license: MIT
compatibility: "Install in a parent directory named yw-skill-foundry. Bundled tooling requires Python >=3.10 and Bash >=3.2 on macOS or Linux. WSL is expected but not CI-verified."
---

# YW SkillFoundry

A skill is not a prompt. It is a design system for AI behavior — architecture, vocabulary, constraints, and craft working together to make domain-specific behavior more repeatable. Whether it improves real outcomes must be demonstrated against a baseline; the document itself is never proof.

The difference between a mediocre skill and an excellent one is not more rules. It is sharper language, tighter structure, and the discipline to make every sentence do exactly one job. A generation skill (writing, design, image) controls output quality. A methodology skill (debugging, reviewing, researching) changes how AI thinks. They share structure but differ in every design decision — interaction model, mode system, failure handling, and language voice.

## Core Principle

**Precision over flexibility.** The more specific your vocabulary, the more consistent AI's output.

- "Use a nice background" → AI picks its training-data default (gradient, blur, or flat color).
- "Paper base, subtle grain, ink wash or contour field, and optional WebGL canvas" → AI produces a layered editorial atmosphere.

The same principle applies everywhere: layout descriptions, constraint wording, quality checks, failure examples. Vague instructions produce average output. Precise vocabulary produces distinctive output.

## Outcome Contract

- **Outcome**: A skill with tight structure, precise vocabulary, reliable triggers, and verifiable quality.
- **Done when**: A Scaffold is ready for labeled trial use after Routing + Contract pass; it may not claim proven effectiveness. Production requires all 4 layers (Routing / Contract / Content / Regression). Content uses persisted comparative evidence or a stronger controlled business metric; no layer passes by self-attestation.
- **Evidence**: Public Agent Skills specifications, bounded research on long-context position and persuasion effects, runnable structural checks, and task-specific baseline comparisons. Public sources and claim limits are listed in the repository README.
- **Output**: SKILL.md + references/ + optional scripts/, or concrete optimization recommendations for an existing skill.

## Capability Circle

✅ Write new skills from scratch or conversation patterns
✅ Optimize existing skills across 7 dimensions
✅ Review and score skill quality with evidence
✅ Extract reusable patterns from conversations
❌ Not for multi-agent runtime architecture — if the problem is agent orchestration, state management, or execution engines, skill instructions will not fix it
❌ Not for model capability gaps — if the model cannot reason about X, no SKILL.md will teach it
❌ Not for business logic code — YW SkillFoundry designs AI behavior, not application features

## Mode Router

| Signal | Mode |
|---|---|
| "写一个 skill" / "create a skill" / starting from scratch | **Write** — full 7-step workflow |
| "优化这个 skill" / "效果不好" / "improve" | **Optimize** — diagnose, locate, fix |
| "看看写得怎么样" / "review" / "audit" | **Review** — 7-dimension scoring |
| "把对话提取成 skill" / "extract" | **Extract** — identify patterns, distill, test |

**Methodology vs. Generation**: if the target skill changes **how AI thinks** (debugging, reviewing, researching), read `references/craft-and-voice.md` § Methodology Skill Design before starting. Its interaction model, mode system, and language voice are fundamentally different from a generation skill.

## Working With the User

YW SkillFoundry's users span from skill veterans to someone who heard the word "skill" today. Meet them where they are — the workflow serves the skill, not the reverse.

- **Enter at the user's step, don't restart.** If they arrive with a draft description, start at Step 2; if they have a finished skill that mis-fires, go straight to Optimize. Re-running the full 7 steps on someone who is 80% done is friction, not rigor.
- **Match their vocabulary.** Use "eval", "frontmatter", "CSO", "holdout" only after they signal they know the terms; otherwise name the thing in one plain line before using the jargon. A confused user can't give you good feedback.
- **One artifact beats three questions.** When inputs are thin, produce a draft skill (or a draft description) with assumptions marked, and let them react to something concrete — per the 3-question budget in `references/behavior-control.md`.
- **Honor "just vibe with me."** If the user wants to skip the process and think out loud, do that. Pull in the rigor (eval, run-compare, holdout) when there's something worth hardening, not as a gate on every exchange.

## Thought Interceptors

"This skill looks straightforward" means run the 7-dimension scoring — do not skip to writing.
"The description is fine as-is" means test it with 3+3 routing prompts in a fresh session.
"I already know how to structure this" means read `references/architecture.md` — follow the 4 decisions, not your training default.
"Adding more rules will make it better" means check if existing rules conflict first and pressure-test the combined set.
"This is a generation skill" means verify — does it change output format, or does it change how AI thinks? Misclassification produces the wrong design patterns.

## Write Mode

Two tracks through the same steps. **Scaffold** (default for a first version): Steps 0-2 in full, then a minimal body — frontmatter, opening statement, workflow, a few hard rules, output format — and a 3+3 routing fixture with one positive and one negative holdout; ship it as unproven trial use and let real usage generate Gotchas. **Production** (for distribution or after a Scaffold survives real use): add Content evidence and regression gates. Mode Router, Direction Lock, Capability Circle, and Gotchas remain conditional; empty scaffolding is context tax.

### 0. Qualify (gate)

Before anything else, decide whether this should be a skill at all — the highest-leverage YW SkillFoundry decision is often "don't build one." Build only if **at least one** holds:

- the workflow will be **reused** (not a one-off answer),
- it is **easy to mis-route** — a near-neighbor request the agent handles wrong by default,
- a **deterministic script** removes repeated manual work, or
- the output needs a **reusable contract** that others depend on.

Reject — do the task inline, or hand back a near-neighbor — when the request is only: explain, summarize, translate, brainstorm, document-without-agent-execution, or a one-off with no reuse. These are exactly the near-misses that make a meta-skill wrongly fire; they belong in the routing fixture as **negatives** (`evals/trigger_cases.example.jsonl`), not as new skills.

**Even when it should be captured, a skill is not the only vehicle — route to the right one** (a skill fires *non-deterministically*, so the wrong vehicle silently fails):

| The need | Vehicle | Why not a skill |
|---|---|---|
| A durable rule/fact that must hold **every** session | `AGENTS.md` / `CLAUDE.md` | Always in context; a must-always rule put in a skill loads only *sometimes* |
| A deterministic action that must run **every time** an event fires | a **hook** | Bypasses the trigger gamble entirely |
| A big, context-heavy sub-task to **isolate** | a **subagent** | Keeps main context clean; a skill runs inline and competes for attention |
| An **occasionally**-needed reusable workflow/contract | a **skill** | The one case skills are genuinely best at |

The most common mis-vehicle is putting a must-always rule into a skill: skills under-trigger, so the rule you needed every time shows up only some of the time.

### 1. Discover

Before writing anything, answer five questions:

1. **What mistake does AI make without this skill?** Name it: "AI 在做 XX 时默认用 YY，但应该用 ZZ." If you cannot name the specific default behavior and the specific replacement, you do not have a problem statement yet. "帮助用户做 XX" is a wish, not a problem.
2. **What does AI do by default?** Run the task without any skill. Save the output — this is your baseline. If the baseline is already good, you do not need this skill.
3. **How will users trigger it?** Write 5-8 natural phrases — the exact words a person would type, in the language they would type them. These become your description keywords.
4. **Where does the expertise come from?** Point at real source material — a runbook, past corrections, expert answers, failure records, house style docs. A skill grounded only in the model's general knowledge produces *precisely worded genericness*: the instructions read sharp, but the content is what the model would have said anyway. No source material → the run-compare delta in Step 6 will be thin, and you'll discover it late. Gather the material now or lower the ambition.
5. **Draft the eval before the body.** Turn the trigger phrases from 1.3 and the baseline failures from 1.2 into concrete eval cases (should-trigger / should-not-trigger / expected output) now — before writing any instructions. Anthropic's official guidance: "Create evaluations BEFORE writing extensive documentation." Evals written after the body test what you wrote; evals written before test what users need.

### 2. Name It (Description)

The description is the skill's front door. Write it wrong and the skill is invisible.

Read `references/description-and-triggering.md` for CSO rules. The essentials:
- What + when: one clause naming the capability, then "Use when..." trigger scenarios. Never workflow steps (the "how").
- Include the exact keywords from Step 1.3 in the languages users actually use, with precise and fuzzy phrasing. Skills under-trigger more often than they over-trigger, so lean slightly generous and rein in with "Not for X".
- ≤ 1024 characters. Sweet spot: 200-400.

Then **lint it before moving on**: `python3 scripts/trigger_eval.py lint --skill <skill-dir>`. Fix every FAIL (empty / over-length / workflow-leak) before writing the body — a broken routing surface makes the rest invisible.

### 3. Architect

Read `references/architecture.md`. Four decisions:

1. Can SKILL.md stay at or below 500 lines? If not → justify what must remain resident and split conditional material; >700 fails the default validator.
2. Which content is only needed in specific scenarios? → Conditional reference: "when X, read Y."
3. Are there rules that can be verified by script? → Put them in scripts/, execute don't read. Run `scripts/validate-skill.sh <skill-dir>` to check metadata and structural compliance signals; use task evals to test whether Hard Rules are actually followed.
4. Is this the first usable version? → Start from `templates/scaffold-starter.md`. Use `templates/skill-starter.md` only for Production complexity. A template with marked editable regions beats ten pages of formatting rules.

### 4. Write the SKILL.md

Use modules by track; empty completeness is not the goal. **Scaffold requires** Frontmatter, Opening Statement, Workflow, Hard Rules, Output Format, and a 3+3 routing fixture. **Production adds** the modules whose conditions below are true:

```
Frontmatter          route (decides if skill activates)
Opening Statement    philosophy (1-2 sentences — set the mental model)
Outcome Contract     add for externally checked deliverables
Capability Circle    add for real scope or refusal boundaries
Mode Router          add when 2+ distinct execution modes exist
Direction Lock       add before expensive/irreversible work
Workflow             the creative process (each step names its reference)
Hard Rules           absolute boundaries (MUST / NEVER / No exceptions)
Anti-Rationalization add after an observed shortcut
Reference Map        add when references/ exists
Gotchas              add after real failure stories exist
Output Format        deliverable spec
```

The canonical track and threshold rules live in `references/invariants.md`; explanations elsewhere must not redefine them.

Read `references/prompt-patterns.md` for the detailed craft of each section — including Direction Lock, Decision Tree, Premise Breakdown, and Reasoning Model considerations.

Read `references/craft-and-voice.md` for the language dimension — vocabulary precision, style identity tests, voice as design decision, the 6-layer instruction staircase, gate failure path design, calibration rules, one-shot question design, and information density as rhythm.

**The Opening Statement sets the tone for everything.** It is the first thing AI reads after activation. A sharp opening — "If it could have been generated by a default prompt, it is not good enough" — reframes AI's entire approach. A bland opening — "This skill helps with X" — changes nothing.

### 5. Write the References

Each reference file mirrors a professional concept:

| File role | Real-world analogy | Example file |
|---|---|---|
| Style system | Brand guidelines | `style-system.md` |
| Pattern library | Component catalog | `layout-recipes.md` |
| Design tokens | Variable definitions | `components.md`, `theme-presets.md` |
| Quality gate | QA checklist | `qa-checklist.md` |
| Domain knowledge | Subject-matter reference | `terminology-zh.md` |

Rules:
- One depth from SKILL.md. Every reference must work standalone: optional peer links are allowed, required peer loads are not.
- Descriptive filenames (`api-patterns.md`, not `doc2.md`).
- TOC at top if > 100 lines.
- Route co-required files directly from SKILL.md instead of building a nested load chain.

### 6. Test (4-Layer Eval)

1. **Routing** (runnable, not self-attested): write a fixture of ≥3 should-trigger + ≥3 should-not-trigger prompts as JSONL (see `evals/trigger_cases.example.jsonl`). Mark ≥1 positive + ≥1 negative as `"holdout": true` — you tune the description against the rest, then prove it on these unseen cases (anti-overfit; a description tuned to pass cases it has already seen proves nothing).
   - **Tune**: `trigger_eval.py worksheet --skill <dir> --fixture <f> --phase train` → judge each shuffled, **unlabeled** prompt in a fresh context (description only, no body), write `{"id":N,"decision":"trigger"|"no"}` per line, `score`, and fix the description until train passes.
   - **Validate**: `worksheet ... --phase holdout`, judge in a fresh context, `score`. A single-phase run gates that phase; a combined run requires **both train and holdout** to pass. Misses come back tagged UNDER-TRIGGER (widen keywords) or OVER-TRIGGER (tighten / add "Not for").
2. **Contract (runnable)**: express deterministic requirements in a contract JSON and run `python3 scripts/contract_eval.py --contract <contract.json> --output <artifact>`. Put subjective requirements in `manual_checks` and supply criterion-level `--manual-results`; pending manual checks exit 2 and never count as pass.
3. **Content (comparative, not self-attested)**: use a controlled business metric when one exists; otherwise run baseline vs with-skill. Persist the task, raw outputs, exact blind candidates, judge inputs, `runs.json`, `judges.json`, mapping, and verdict; create and verify the manifest with `scripts/evidence.py`. Exploratory evidence may use one run per side but cannot support a stable-effect claim. Production requires ≥2 matched run pairs; every pair gets both A/B judge positions. Record model IDs and token/time metrics when available; when the host does not expose them, record an explicit unavailable reason instead of inventing values. Full protocol and v2 schema: `references/quality-assurance.md` § Run-Compare and `references/evidence-schema.md`.
4. **Regression**: After changes, do previously passing cases still pass? Keep the fixture; re-run `score` (and a run-compare on the changed path) after every meaningful change.

Before shipping, run `python3 scripts/citation_lint.py --skill <dir>` — the body must not name private skills a reader cannot open. After changing YW SkillFoundry itself, run `bash scripts/regress.sh --library-root <loaded-skills-dir>`; it executes checker bite tests plus persisted routing regressions, privacy checks, and the library audit.

**If you are adding this skill into a library that already has others, also run `python3 scripts/skill_library_audit.py` (pass every `--root` the host actually loads — user skills, project skills, plugin caches; it scans recursively).** Routing collision is a property of the *set*, not the skill: the platform has no algorithmic router — the model reads every description and picks one, so a skill that routes perfectly *alone* can steal or lose triggers once it sits next to 20+ siblings. The audit flags description-budget pressure (the real ceiling is host-specific and dynamic — hosts drop or truncate descriptions past their budget; the script's default is a heuristic, tune with `--budget`), unroutable skills (empty / over-1024 description), duplicate names, and overlapping trigger vocabulary. Step 1 routing (`trigger_eval`) tests one skill; this tests the library.

For skills with multiple supported models or hosts, test every declared supported combination when feasible; otherwise test at least one stronger and one weaker representative and label the remaining matrix unverified. A single-model skill does not add artificial model breadth.

Read `references/quality-assurance.md` for the full eval framework, domain slop catalog methodology, and Design Invariants.
Read `references/iteration.md` for TDD for Skills (RED → GREEN → REFACTOR) and pressure testing.

### 7. Iterate

Every test failure is a signal:

- A new real-world failure case → append to Gotchas, do NOT lengthen the main workflow. The workflow stays the stable spine; failures accumulate in the table. A workflow that grows with every incident becomes unreadable and unfollowable.
- AI took a shortcut → add an Anti-Rationalization entry (read `references/behavior-control.md`)
- AI ignored a rule → check its position. Long-context middle placement can degrade retrieval depending on task and model; move critical rules to the head/tail and rerun the failing case.
- AI output is inconsistent → reduce freedom. Provide a template, a decision tree, or tighter constraints.
- AI followed the rule but the output is wrong → the rule itself is broken. Fix the rule, not the AI.

**Capture loop:** after the agent uses the skill, ask where it went off-track and what context was missing, then turn verified failures into a Gotchas row or fixture. Iterate on one hard task until it succeeds, then generalize.

**Read the transcript, not just the output.** The output says whether the result is right; the transcript says how the skill shaped the process. Watch for three signals — the skill sent the agent on a detour (cut that instruction), the agent re-wrote the same helper across runs (extract it to `scripts/`), or with-skill burned far more tokens than baseline for no quality gain (trim the body). Script extraction should come from *observing* repeated work, not from armchair guessing — guessed scripts become dead code nobody calls. See `references/iteration.md` § 读 transcript.

## Optimize Mode

Read the target skill, then diagnose across 7 dimensions (priority order):

1. **Trigger accuracy** — Does the description match real user language?
2. **Information architecture** — Is the skill at or below 500 lines by default? Are references independently usable?
3. **Instruction precision** — Are constraints bright-line rules, or vague suggestions? Do any constraints conflict with each other?
4. **Output reliability** — Is there a validation script? A seed template?
5. **Behavior control** — Can AI find a rationalization to skip a step?
6. **Iteration support** — Are Gotchas from real failures? Is there version tracking?
7. **Token efficiency** — Is anything loaded that is not used?

For each: current state → problem → specific fix.

## Review Mode

Score 1-5 on each dimension. Cite specific lines as evidence:

| Dimension | 1 | 5 |
|---|---|---|
| Trigger precision | Vague description, no keywords | CSO-optimized, tested with 3+3 |
| Architecture | Single file >500 lines | Three-layer progressive disclosure |
| Instruction clarity | "consider doing X" | Bright-line rules + NO/OK contrast |
| Behavior control | No safeguards | Anti-Rationalization + Hard Stops |
| Output reliability | AI judgment only | Script validation + seed template |
| Iteration support | No Gotchas | Real failure stories + version log |
| Token efficiency | Everything inline | Conditional loading + script execution |

< 20 → rewrite. 20-28 → targeted optimization. 29-35 → structurally mature and ready for Production eval; the score never proves effectiveness.

## Extract Mode

Turn a successful conversation into a reusable skill:

1. Identify instructions and constraints that **recurred** across turns.
2. Separate reusable patterns from project-specific details — extract only the former.
3. Write a minimal SKILL.md covering only the identified patterns.
4. Test in a fresh session — can AI reproduce the conversation's behavior from the skill alone?

## Handoff

When YW SkillFoundry cannot help — the problem is at the architecture layer, model capability layer, or outside the instruction design domain:

```
Problem: [what the user is trying to solve]
Tried: [which YW SkillFoundry approaches were attempted]
Why insufficient: [architecture / model capability / out of scope]
Suggest: [alternative approach, tool, or discipline]
```

Do not keep iterating on SKILL.md when the root cause is not in instructions. A structured handoff is more valuable than a sixth rewrite.

## Hard Rules

- SKILL.md body should stay **≤ 500 lines**. At 501–700, explain why the content must remain resident or split low-frequency material into references; >700 fails the default validator. Do not pad, and do not amputate necessary instruction just to hit a number.
- Description **MUST NOT** contain workflow steps. Only trigger conditions.
- References **MUST** be discoverable one depth from SKILL.md and independently usable. Optional peer links are allowed; required reference-to-reference loads are not.
- Match constraint register to stakes (three tiers, never "consider/try to"): (1) **non-negotiable / irreversible / safety** → MUST / NEVER / No exceptions; (2) **everything else** → imperative + the reason ("Do X, because Y") — explaining *why* outperforms a bare MUST on smart models, and stacking MUSTs on ordinary rules dilutes the ones that matter (official skill-creator calls all-caps ALWAYS/NEVER on routine rules a "yellow flag"); (3) **never** weak words like "consider", "try to", "you might want to". See `references/prompt-patterns.md` § Authority 用词.
- Do not explain concepts AI already knows. Do not teach what Markdown is.
- Every sentence in a skill is a tax — indexed descriptions cost every session, loaded bodies cost every turn. For each sentence ask: without it, would the agent err? If not, delete it.
- One excellent example beats five mediocre ones. Never duplicate examples across languages just for coverage.
- Every constraint should be specific enough to visualize. "Do not use decorative blobs" is testable. "Keep it clean" is not.
- The body (SKILL.md + references) **MUST NOT** name private/internal skills a reader cannot open — a name with no verifiable content is noise that reads like an ad. Keep the technique and any inlined evidence; drop the name. Public, checkable sources (Anthropic spec, agentskills.io, Meincke PNAS 2026, Lost in the Middle) are fine. Enforce with `scripts/citation_lint.py`; public provenance belongs in `CHANGELOG.md` or an evidence note.

## Reference Map

| File | What it provides | Load when |
|---|---|---|
| `templates/scaffold-starter.md` | Minimal first-version template: opening, workflow, hard rules, output, routing-fixture reminder | Default in Write Mode |
| `templates/skill-starter.md` | Production module template with conditions and deletion guidance | After Scaffold survives usage or distribution requires more controls |
| `references/invariants.md` | Single source of truth for metadata, size, module tracks, reference, eval, evidence, and authority rules | Before changing any repeated threshold or checker |
| `references/evidence-schema.md` | Complete v2 format for matched runs, bound contract reports, blind candidates, and per-pair position swaps | Before creating Production content evidence |
| `scripts/validate-skill.sh` | Automated checks: line count, description, standalone references, map consistency, authority wording, TOC | Step 6 — run `bash scripts/validate-skill.sh <skill-dir>` |
| `scripts/contract_eval.py` | Executes deterministic Output Contract checks and blocks ungraded manual criteria | Step 6 Contract layer |
| `scripts/evidence.py` | Creates and verifies v2 run-compare manifests, repeated-run metadata, blind candidate identity, and position swaps | Step 6 after raw artifacts are saved, and before citing a verdict |
| `scripts/citation_lint.py` | Scans the body for private/internal skill names a reader cannot open; fails if any leak in | Step 6 and before publishing |
| `scripts/self-check.sh` | Runs the checker suite on good inputs and bite tests each guard with broken inputs | After editing any script |
| `scripts/privacy_lint.py` | Scans public files, reachable Git history, and release archives for private identifiers and secrets | Before publishing or packaging |
| `scripts/regress.sh` | One command for self-check, structure, routing evidence, privacy, and optional library audit | Before publishing YW SkillFoundry changes |
| `scripts/trigger_eval.py` | Runnable Routing eval: `lint` (description defects), `worksheet --phase train/holdout` (fresh-context judging), `score` (complete phase coverage; combined runs gate both train and holdout; maps under/over-trigger to fixes) | Step 2 (lint) and Step 6 (worksheet → score) |
| `scripts/skill_library_audit.py` | Set-level routing audit across a whole library (recursive, multi-root): description budget vs a host-tunable ceiling, unroutable (empty / over-1024) skills, duplicate names, and cross-skill trigger-overlap candidates | Step 6 when adding a skill to an existing library, or to audit library health |
| `evals/trigger_cases.example.jsonl` | Fixture format for routing cases (should-trigger / should-not), with YW SkillFoundry's own cases | Step 1.4 (draft cases) and Step 6 (run the harness) |
| `examples/worked-example.md` | One fully self-contained before→after build (raw workflow → final SKILL.md), no external skill needed to verify the craft | When you want a reproducible demonstration of the method |
| `examples/run-compare-bug-report.md` | A real, executed with-skill vs baseline run-compare with a criterion-level diff and honest verdict | When you want to see what a Step 6 run-compare actually looks like |
| `examples/run-compare-pr-describe.md` | A fuller dogfood showing P5 (holdout-picked description), P1 (variance/noise floor over 2 baseline runs), and P2 (blind judge) together | When you want to see candidate selection + variance + blind eval in one worked run |
| `references/architecture.md` | Three-layer disclosure, token budgets, bootstrap injection, platform adaptation, sub-agent orchestration, cross-skill pipeline handoff contracts | Step 3 or Optimize dimension 2 |
| `references/description-and-triggering.md` | CSO rules, trigger word design, testing methodology | Step 2 or Optimize dimension 1 |
| `references/prompt-patterns.md` | Instruction patterns with principles: Outcome Contract, Mode Router, Direction Lock, Decision Tree, Truth-Source Precedence, NO/OK, Authority wording, Reasoning Model guidance | Step 4 or when understanding a specific pattern |
| `references/craft-and-voice.md` | Design language precision, vocabulary spectrum, style identity tests, voice as design decision, 6-layer instruction staircase, gate failure paths, calibration rules, one-shot question design, information density, thought interceptors, interaction cost model, feeling-based mode description, methodology skill design (cognitive compression, dual exit) | Step 4-5 or when the skill's language feels generic or structurally weak |
| `references/behavior-control.md` | Anti-Rationalization, Iron Law, Hard Stops, Gate Whitelist (closed action list while awaiting confirmation), Gate Before Conclude, Evidence Ladder, Capability Circle, Calibration Rules (anti-overcorrection) | When designing safeguards against AI shortcuts or overcorrection |
| `references/quality-assurance.md` | 4-layer eval, risk-tiered verification budget, domain slop catalog methodology, Design Invariants, density checks, pre-ship checklist | Step 6 or Review Mode |
| `references/iteration.md` | TDD for Skills, failure typology, pressure testing, privacy-safe version tracking | Step 7 or when planning an iteration cycle |
| `references/anti-patterns.md` | 17 anti-patterns with NO/OK contrast, quick self-check checklist | Self-check during writing, or Review Mode |

## Gotchas

| What happened | Rule |
|---|---|
| A description summarized an internal multi-step review workflow. The agent treated that summary as complete and skipped a required second review pass. | Description is a trigger, not a workflow summary. Putting execution steps there can make the agent skip the body because it thinks it already knows what to do. |
| SKILL.md was long; middle-positioned Hard Rules were missed in repeated task runs. | Long-context retrieval can be weaker in the middle. Keep critical rules near the head/tail, split low-frequency material, and verify on the failing task. |
| Wrote "始终检查工作目录" as a rule. AI still operated in the wrong directory. | Abstract rules are invisible. Concrete failures are memorable: "Moved files to ~/project, but the repo was at ~/www/project — lost 2 hours." Gotchas work through pattern matching, not principle comprehension. |
| Used "consider doing X" for a safety check. AI skipped it under time pressure from the user. | "Consider" grants permission to skip; "MUST" does not — weak words are semantically optional. (Indirect support: LLMs are measurably sensitive to authority framing — Meincke et al. PNAS 2026 — but the binding reason is semantic, and your own run-compare is the direct test.) |
| Wrote instructions in generic language: "use a good layout." AI repeatedly fell back to generic defaults in the tested cases. | Increase only the vocabulary precision needed to remove that observed ambiguity, then compare again. |
| AI said "I'm following the spirit, not the letter" and skipped TDD. | Add one sentence: "Violating the letter IS violating the spirit." This blocks the entire class of rationalization. |
| Reference files required each other in a loop. AI bounced between them, wasting tokens and losing context. | Each reference must be independently usable. Optional peer links are fine; required peer-load chains are not. |
| A gate said "check the photo has a quiet zone" but didn't say what to do when it fails. AI added a dark overlay — the exact hack the skill was designed to prevent. | Every gate needs a designed failure path: degrade, switch container, change input, honest exit — and an explicit ban on the tempting workaround. |
| Added aggressive anti-slop rules. AI corrected so thoroughly it changed the author's voice and meaning. | Anti-Rationalization prevents doing too little; Calibration Rules prevent doing too much. Every behavior control system needs both sides. |
| Wrote a methodology skill (debugging) using generation-skill patterns: linear workflow, heavy seed templates, auto-validation. AI followed the steps but still skipped diagnosis and jumped to patching. | Methodology skills change thinking paths, not output format. They need thought interceptors, cognitive compression tests, and dual-exit (success + structured handoff). Generation patterns do not transfer. |
| Described two modes by their technical specs: "Mode A uses serif fonts, Mode B uses sans-serif." AI always picked Mode B for tech content and Mode A for humanities — rigid category mapping. | Describe modes by feeling: "slow, considered, hand-set" vs "engineered, quantified, decisive." Feeling-based descriptions let AI make editorial judgments; spec-based descriptions create brittle category bindings. |
| Reference list was alphabetically sorted. AI loaded `background-systems.md` in Step 1 (never needed that early) and ran out of context budget by Step 5. | Sort the Reference Map by probable access order, not by name. Files needed in Step 1-2 go first; rarely-triggered conditional files go last. |
| Skill had many well-written Hard Rules, but several competed — "MUST be ≤500 lines" conflicted with "MUST include every optional module." | More constraints ≠ more compliance. Before adding a rule, check it against the existing set and run the affected eval; delete or scope conflicting rules. |
| A skill routed perfectly in isolation, then started stealing (or losing) triggers as the library grew. | Collision is a property of the **set**, not the skill. Test one skill with `trigger_eval`, then test the loaded library with `skill_library_audit.py`; fix overlaps with exclusions or a rename. |
| Put a must-always rule into a skill; it loaded only some sessions because skills under-trigger. | A non-deterministic vehicle can't carry an always-on rule. Durable rules → `AGENTS.md`; must-run-on-event → hook; isolation → subagent; only *occasional* workflows → skill (see Qualify gate). |
| A public skill repo put "if you edit me, co-update the README index" comments in every file header — its README still listed a skill that didn't exist in the repo. | Comment-based co-update reminders don't survive iteration. Cross-file consistency (index ↔ directory, Reference Map ↔ files) must be script-checked, not comment-reminded. |

## Anti-Patterns (Quick Self-Check)

The full list with NO/OK contrast is in `references/anti-patterns.md` (don't restate it here). Top scan:

- Description contains workflow steps, or the body exceeds ~500 lines without justification.
- Constraints use "consider" / "try to" / "you might want to".
- Narrative content or generic labels (helper1, step3) instead of named, specific instruction.
- Deployed without testing, or `@file.md` force-loads a large file every session.
- Language is generic enough that removing the skill name would make the instructions unrecognizable.
