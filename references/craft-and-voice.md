# Craft and Voice

How to craft the language of a skill so it changes AI output quality — not just controls behavior.

## 目录

- [The Vocabulary Spectrum](#the-vocabulary-spectrum)
- [Writing Constraints That Are Visible](#writing-constraints-that-are-visible)
- [Style Identity Tests](#style-identity-tests)
- [Organizing References Like a Design System](#organizing-references-like-a-design-system)
- [Minimum Density Per Pattern](#minimum-density-per-pattern)
- [Decoupling: Style From Content, Structure From Decoration](#decoupling-style-from-content-structure-from-decoration)
- [The Opening Statement As Design Act](#the-opening-statement-as-design-act)
- [Writing Workflow Steps As Creative Actions](#writing-workflow-steps-as-creative-actions)
- [The Gotcha As A Story](#the-gotcha-as-a-story)
- [The 6-Layer Instruction Staircase](#the-6-layer-instruction-staircase)
- [Designing Gate Failure Paths](#designing-gate-failure-paths)
- [Calibration Rules: Preventing Over-Correction](#calibration-rules-preventing-over-correction)
- [Voice as Design Decision](#voice-as-design-decision)
- [One-Shot Question Design](#one-shot-question-design)
- [Information Density as Rhythm](#information-density-as-rhythm)
- [Thought Interceptors: Catching AI's Internal Rationalization](#thought-interceptors-catching-ais-internal-rationalization)
- [Interaction Cost Model: When to Ask, When to Proceed](#interaction-cost-model-when-to-ask-when-to-proceed)
- [Mode Description: Feeling Over Technical Specs](#mode-description-feeling-over-technical-specs)
- [Methodology Skill Design](#methodology-skill-design)
- [Artifact-as-Gate: Written Intermediates Before Expensive Work](#artifact-as-gate-written-intermediates-before-expensive-work)
- [Recommendation ≠ Authorization](#recommendation--authorization)

---

## The Vocabulary Spectrum

The same instruction can be written at five precision levels. The table describes
expected tendencies, not guaranteed outputs; compare levels on the target task.

| Level | Example (background) | What AI produces |
|---|---|---|
| **Vague** | "Use a nice background" | Training-data default: gradient, flat color, or blur |
| **Named** | "Use a warm paper background" | Better, but still generic paper (#f5f0e0 flat fill) |
| **Layered** | "Paper base + subtle grain + ink wash" | Structured layers, closer to editorial feel |
| **Specified** | "Paper base #f5f1e8, grain at opacity .12 mix-blend-mode:multiply, ink wash radial-gradient at 18% 22%" | Consistent, reproducible, close to reference |
| **Templated** | Seed template HTML with exact CSS layers already wired | More repeatable structure with fewer free choices |

Moving from Level 1 to Level 3 often reduces ambiguity at low authoring cost.
Level 4-5 is for skills that need tighter visual or structural consistency.

**Rule: use the least precision that removes the observed ambiguity. Reserve
Level 4-5 for visual or structural decisions that actually need it.**

### How to build your vocabulary

1. Run the task without a skill. Look at AI's default output.
2. Identify what's generic — the words, structures, choices AI fell back on.
3. Name the specific alternative with precise terms from the skill's domain.
4. Write the instruction using those terms, not the generic ones.

Example (social-card cover):

```
AI default: "Create a cover with a big title and an image"
↓ (identify generic: "big title", "an image")
↓ (name specifics from the domain)
Upgraded: "Large serif/Songti-like title, usually 2-4 lines.
           One large image or photo crop occupying 35%-55% of the page.
           Bottom issue strip with 3-5 points."
```

The vocabulary is not decoration — it is the mechanism. Each specific term narrows AI's choice space and pushes it away from its default.

## Writing Constraints That Are Visible

A constraint is only useful if you can see what it prevents.

```
NO (invisible):
  "Keep the design clean."
  → AI cannot verify this. "Clean" maps to 100 different things in training data.

OK (visible):
  "Do not create random decorative SVG ovals, blobs, rain drops,
   stickers, or meaningless circles."
  → AI can check each generated element against this list.
```

```
NO (invisible):
  "Use appropriate font weights."

OK (visible):
  "The larger, the lighter. Display titles (>=72px) use weight 200-400.
   Body text (24-30px) uses weight 400-500. A 90px h1 at weight 700+
   instantly downgrades the design from Swiss International to
   generic landing-page editorial."
```

The technique: name the specific failure, describe what it looks like, explain the consequence in domain terms.

## Style Identity Tests

A powerful quality tool is the "Style Identity Test" — a boolean check that verifies whether the output actually achieved the intended style.

```
A poster is Swiss only if ALL FOUR hold:
1. Every display title (>=72px) uses a typed class. Computed weight <= 300.
2. No serif family is loaded.
3. Section separators are hairline rules, not card borders + drop shadows.
4. Exactly one accent palette is in use.

If any one fails, the poster is not Swiss — it is "Swiss-flavored card." Fix or relabel.
```

### How to build an identity test for any skill domain

1. Produce 5 examples of the target quality.
2. Produce 5 examples that look close but are subtly wrong.
3. Identify the 3-5 properties that reliably distinguish "right" from "almost right."
4. Write each property as a boolean check.
5. Gate: ALL must hold. Partial pass = not the target style.

This works for any domain:
- **Writing skill**: "The text passes the identity test only if: (1) no paragraph ends with a summary sentence starting with '这说明', (2) no section opens with '随着...的发展', (3) all technical terms are explained only on first use."
- **Code review skill**: "The review passes only if: (1) every finding cites a specific file:line, (2) no finding says 'consider optimizing' without naming what to change, (3) severity labels are present."

## Organizing References Like a Design System

The best skills organize their reference files the way professional design systems organize their documentation:

| Design system concept | Reference file role | Example |
|---|---|---|
| **Brand guidelines** | Style philosophy and visual rules | `style-system.md` |
| **Component catalog** | Reusable patterns with skeletons | `layout-recipes.md` |
| **Design tokens** | Exact values (fonts, colors, sizes) | `components.md`, `theme-presets.md` |
| **Content strategy** | How to plan and compress content | `content-planning.md` |
| **QA checklist** | Pre-ship verification | `qa-checklist.md` |
| **Asset library** | Templates, scripts, images | `assets/template-*.html` |

Why this matters: when each reference file has a clear professional role, both AI and the skill author know exactly where to find information. "I need the exact font size" → tokens file. "I need to choose a layout" → pattern library. "I need to check quality" → QA file.

**Anti-pattern**: dumping all domain knowledge into one 800-line reference file. This is the reference equivalent of a 500-line SKILL.md — Lost in the Middle applies to references too.

## Minimum Density Per Pattern

Define a "Minimum density" for every layout recipe:

```
M07 Closing Note — Minimum density (3:4):
title + >=4 ledger items with sub-lines + closing block.
The previous "2-3 rules" version leaves a visibly under-filled 3:4 composition.
3 short ledger lines on a 3:4 canvas is a failure mode.
```

This prevents AI from choosing a pattern when it doesn't have enough content to fill it.

### Generalize to any skill

When your skill offers multiple templates, modes, or patterns, define the minimum input requirement for each:

```
Mode A — Minimum input: 3+ paragraphs of source material + at least 1 image.
         Below that: switch to Mode B (single-card) or ask for more content.

Mode B — Minimum input: 1 title + 1 key sentence.
         Below that: this is not a card, it is a tweet. Skip the skill.
```

This saves AI from producing thin, under-filled output and saves the user from getting a template with empty slots.

## Decoupling: Style From Content, Structure From Decoration

A decoupling principle worth stating outright:

> "The two modes below are visual stances, not content categories. Any topic can be rendered in either mode — what changes is the page's feel."

This one sentence prevents AI from falling into "outdoor = Editorial, tech = Swiss" category thinking.

The principle generalizes: in any skill, explicitly decouple the dimensions that AI tends to conflate:

- Style from content type ("Swiss is a visual stance, not a tech-only style")
- Structure from decoration ("columns organize information; gradients add nothing")
- Constraint from judgment ("MUST is a rule; 'looks good' is an opinion")
- Recipe from taste ("M16 Image-Led Cover requires a photo that passes the quiet-zone test — this is a gate, not a preference")

## The Opening Statement As Design Act

The first 1-2 sentences after the title set the tone for the entire skill execution. Compare:

```
Weak (describes functionality):
  "This skill helps users create better presentations."
  → AI treats this as a generic helper. No reframing happens.

Strong (sets a point of view):
  "If it could have been generated by a default prompt, it is not good enough."
  → AI immediately filters its output against a higher standard.

Strong (names the core tension):
  "Expression comes first. The goal is not to squeeze text into posters;
   it is to turn the source into a clear visual argument."
  → AI shifts from layout-filling to storytelling.

Strong (states what this skill replaces):
  "A skill is not a prompt. It is a design system for AI behavior."
  → AI stops treating the skill as a one-shot instruction and starts treating it as a system.
```

The opening is not a description — it is a design act. It determines whether AI reads the rest of the file as "just another instruction set" or as "a specific discipline with standards."

## Writing Workflow Steps As Creative Actions

Workflow steps should read as a creative process, not an administrative checklist.

```
NO (administrative):
  "Step 1: 目标拆解"
  "Step 3: 架构决策"
  "Step 6: 测试"

OK (creative):
  "1. Discover" — what AI gets wrong without this skill
  "2. Name It" — the description that makes the skill findable
  "3. Architect" — the information structure
  "6. Test" — prove it works outside your head
```

Each step name should suggest an action the author performs, not a category to fill in. "Extract The Story" is better than "Content Analysis" — it tells AI what to DO, not what to LABEL.

## The Gotcha As A Story

Gotchas work through pattern matching. AI reads a concrete failure story and matches it against its current situation. Abstract rules do not trigger this mechanism.

```
NO (abstract rule):
  "Always check your working directory before moving files."

OK (failure story):
  "Moved files to ~/project. The repo was at ~/www/project.
   Lost 2 hours to a silent path mismatch."
```

```
NO (vague warning):
  "Be careful with font weights in Swiss style."

OK (visible failure):
  "A 92px h1 at weight 800 — 'for emphasis.' Instantly collapsed
   the design from Swiss International to generic landing-page editorial.
   The larger, the lighter. Always."
```

The story format: what happened → what went wrong → what the rule is. The more specific the details (92px, weight 800, "for emphasis"), the stronger the pattern match.

## The 6-Layer Instruction Staircase

The best skills stack their instructions in a deliberate sequence. This is not arbitrary — each layer depends on the one above it:

```
Layer 0: Boundary       can / cannot do (Capability Circle)
Layer 1: Philosophy     why this exists (Core Principle, Opening Statement)
Layer 2: Reference Index what manuals exist and when to read each
Layer 3: Workflow        the creative process, step by step
Layer 4: Sub-domain rules loaded only when a specific path is taken
Layer 5: Non-Negotiables absolute vetoes, placed LAST for recency effect
```

**Why this order matters:**

- Layer 0 before Layer 1: AI must know its scope before it absorbs a philosophy. Otherwise it applies the philosophy to out-of-scope requests.
- Layer 2 before Layer 3: AI must know the reference landscape before entering the workflow. Otherwise it reads the workflow, starts executing, and never loads the references.
- Layer 5 at the end: LLM attention is strongest at the beginning and end of a document (U-shape). Non-Negotiables at the end act as a final veto that catches anything the workflow missed.

The layers are a dependency order, not a rigid section sequence. The binding constraints are three: boundary and philosophy material (Layers 0-1, in either order) lives at the head; the reference index precedes the workflow that uses it; Non-Negotiables sit last. Within the head, opening with philosophy (Core Principle first, as YW SkillFoundry itself does) or with boundary (Capability Circle first) are both valid — pick by what the reader must absorb first for *this* skill.

## Designing Gate Failure Paths

A gate is only as good as its failure path. The success path is obvious — pass the test, continue. The failure path is where skills diverge between mediocre and excellent.

Five failure path types:

| Type | Mechanism | Example |
|---|---|---|
| **Degrade** | Switch to a simpler option | a dense layout fails the quiet-zone test → fall back to a simpler one |
| **Switch container** | Use a different recipe/mode | too few items for the chosen recipe → switch to a pull-quote layout |
| **Change input** | Ask for better material | photo fails both tests → ask the user for a different photo |
| **Honest exit** | Name what cannot be done | out-of-scope request → "push back honestly" instead of faking it |
| **Ban workaround** | Block the tempting hack | "Do not fix it with a mask" / "Do not use flex:1 to center" |

**The ban is the most important part.** AI's default response to a failed gate is to find a workaround — add a mask, shrink the font, center with flex:1. Naming and banning the specific workaround is what makes the gate effective.

When writing gates for your skill, always answer: "When this gate fails, what will AI try to do instead? Ban that."

## Calibration Rules: Preventing Over-Correction

Anti-Rationalization prevents AI from doing too little. Calibration rules prevent AI from doing too much — flattening specific feedback into generic fixes, or overriding real evidence with training defaults.

Six calibration patterns:

| Pattern | Prevents | Example |
|---|---|---|
| **Evidence > Instinct** | Training defaults overriding the real product | "The real running product is the oracle." |
| **Specific > Generic** | Flattening taste into adjectives | "'More premium' is not a diagnosis; 'caption baseline drifts above the Chinese line' is." |
| **Meaning > Polish** | Rewriting changing the author's intent | "If removing an AI pattern would change the author's intended meaning, keep the original." |
| **Content > Container** | Choosing a layout before having content | "Content shape decides layout. Do not pick a pretty layout first." |
| **Hypothesis > Patch** | Coding without understanding the cause | "Do not touch code until you can state the root cause in one sentence." |
| **Honest zero > Manufactured findings** | Inventing problems to justify the skill invocation | "A clean review is a valid review. Do not manufacture findings." |

Add the relevant calibration rules for your skill's domain. The pattern is: "When AI is about to substitute its training default for the real evidence, which specific default and which specific evidence?"

## Voice as Design Decision

The tone of a skill is not incidental — it shapes how AI executes every instruction.

| Voice | Best for | Characteristic |
|---|---|---|
| **Curatorial director** | Visual / brand work with named historical styles | Diagnostic, falsifiable tests, citation-heavy: "A poster is Swiss only if all four hold." |
| **Surgical lead** | Fix-and-verify workflows | Outcome contracts, screenshot-as-brief, anti-vague: "If it could have been generated by a default prompt, it is not good enough." |
| **Mentor** | Complex process skills with brand/asset decisions | War stories, dated postmortems, checkpoints — e.g. a concrete product-photo story as evidence for "use real brand assets." |
| **Line editor** | Prose/content transformation skills | Bilateral rules (what to keep AND what to remove), a pattern catalog of 50+ specific NO/OK examples. |

**Choose deliberately.** If your skill's voice sounds like a bureaucratic manual — "Step 1: Perform analysis. Step 2: Generate output." — it will produce bureaucratic output. If it sounds like an expert with a point of view, AI adopts that stance.

## One-Shot Question Design

When your skill needs to ask the user a branching question, design it as a one-shot:

```
Template:
[Context in 1 line]
A. [Option] (recommended — [why in ≤10 words])
B. [Option]
C. [Option]
```

Design rules:
- **Only ask what changes the output.** If you can proceed with a reasonable default, don't ask.
- **3 options, not 5.** Cover the decision space with minimum cognitive load.
- **Recommend one.** Give a professional bias, but accept any choice.
- **Handle "都行你看着办"** — treat as approval of the recommended option.
- **Close the door.** "Do not re-prompt later." One-shot means one shot.

Why one-shot: every re-prompt turns a design failure (bad recipe, bad crop) into a user-decision failure ("you should have chosen A"). The skill should fix failures within the chosen path, not re-open the intake.

## Information Density as Rhythm

Density should vary intentionally across files — it affects AI's reading mode:

| File role | Target density | AI reading mode |
|---|---|---|
| SKILL.md (hub) | Medium — breathing room between sections | Scanning, routing, decision-making |
| Lookup references (recipes, tokens, specs) | Dense — tables, exact values, paste-ready skeletons | Precise execution, copying |
| Validation references (checklists, identity tests) | Sparse — scannable checks, one per line | Quick pass/fail sweep |
| Philosophy sections (Opening, Core Principle) | Very sparse — 1-2 sentences, white space | Framing, mental model setting |

Dense files without breathing room cause AI to skim. Sparse files where density is needed cause AI to improvise. Match the density to the reading task.

## Thought Interceptors: Catching AI's Internal Rationalization

A debugging-skill pattern targets AI's chain-of-thought directly by naming the rationalization, then the required action:

```
"I'll just try this" means no hypothesis — write it first.
"I'm confident" means run an instrument that proves it.
"Probably the same issue" means re-read the execution path from scratch.
```

This is not advice for humans. It matches **specific language patterns** that appear in LLM internal reasoning when the model is about to shortcut. The format — `"[AI self-talk]" means [corrective action]` — creates a lookup table that activates mid-reasoning.

### How to write thought interceptors for any skill

1. Run your skill 5-10 times. Read the AI's chain-of-thought (or infer it from behavior).
2. Identify the moments where AI rationalized skipping a step or cutting a corner.
3. Write down the **exact phrase** AI would think at that moment.
4. Pair it with the **specific action** it should take instead.

```
For a writing skill:
"This paragraph is fine as-is" means read it against the anti-slop list — item by item.
"The user probably wants this shorter" means check the user's actual request — did they say shorter?
"I'll add a transition sentence" means check if the original had one — do not add what the author omitted deliberately.
```

**When to use**: methodology skills (debugging, reviewing, researching) where the core challenge is changing AI's reasoning path. Generation skills rarely need thought interceptors — they control output format, not thinking.

## Interaction Cost Model: When to Ask, When to Proceed

Three skills, three completely different interaction strategies:

| Skill type | Strategy | Reason |
|---|---|---|
| Visual card | One-shot image source question, then never re-ask | Re-asking = "I don't trust your choice." Costs user trust, not tokens |
| Image generator | Hard gate before generation — must confirm | Image generation is expensive and irreversible. 1 min confirmation saves 10 min wasted generation |
| Debugger | Almost never asks. Hands off after 3 failed hypotheses | Diagnosis is AI-driven reasoning. Interrupting for questions signals "I don't know how to think" |

**The rule**: interaction frequency is driven by `operation cost × irreversibility`, not by politeness.

```
High cost + irreversible (generate images, publish post) → confirm first
Low cost + reversible (choose image source, pick a theme) → ask once, remember
Zero cost (AI reasoning, analysis) → don't ask, just do. Report results
```

When designing your skill's workflow, tag each step:
- **Gate** (must wait for user): only for irreversible expensive operations
- **One-shot** (ask once, remember): for preference choices that affect the whole session
- **Silent** (proceed without asking): for anything AI can do and undo

## Mode Description: Feeling Over Technical Specs

Describe visual modes not by listing CSS properties, but by the feeling they create:

```
Editorial: "slow, considered, hand-set"
Swiss: "engineered, quantified, decisive"
```

When both modes are technically viable for the same content, the tiebreaker is: "Is this a feature story or a release note?" — an editorial judgment, not a spec lookup.

**Why this works better than technical descriptions**: Technical specs (`serif fonts + WebGL background` vs `sans-serif + grid`) create rigid category mappings — AI will always pick Editorial for humanities, Swiss for tech. Feeling descriptions enable AI to make **intent-based routing**: a tech startup's founding story might be Editorial despite being about technology.

Apply to any skill with 2+ modes:
```
NO (technical): "Mode A uses bullet points and headers. Mode B uses flowing prose."
OK (feeling):   "Mode A is structured, scannable, for readers who skim.
                 Mode B is immersive, layered, for readers who linger."
```

The feeling tells AI **when** to choose each mode. The technical specs (which go in the reference files) tell AI **how** to execute the chosen mode.

## Methodology Skill Design

Generation skills (writing, design, image) and methodology skills (debugging, reviewing, researching) are **different species**. They share SKILL.md structure but differ in every design decision:

| Dimension | Generation Skill | Methodology Skill |
|---|---|---|
| Core challenge | Output quality control | Changing AI's reasoning path |
| Opening | Value statement or capability boundary | Cognitive axiom — a claim that creates friction against AI's default behavior |
| Interaction model | Confirm before expensive work | Almost never ask — AI drives the reasoning loop |
| Mode system | Mutually exclusive forks (Editorial OR Swiss) | Stackable tools — Bisect then Scope Blast in one session |
| Failure handling | Always produces something | Dual exit: Success Format + structured Handoff |
| Key patterns | Seed templates, style identity tests, validation scripts | Thought interceptors, cognitive compression tests, evidence ladders |
| Language voice | Curatorial / editorial — describing what good looks like | Surgical / diagnostic — intercepting bad reasoning in real time |

### Cognitive Compression Test

A diagnostic methodology skill can require stating the root cause in **one sentence** before touching code:

> "I believe the root cause is [X] because [evidence]."

This is not a formatting rule. It is a **cognitive test** — if you cannot compress your understanding into one sentence, you have not understood yet. Structured templates (YAML with `cause:` / `location:` / `evidence:` fields) let AI fill each field independently without checking causal coherence between them.

Apply to methodology skills: before the expensive action, require a one-sentence compression of the key insight. The sentence must name specific entities (file, function, line, condition), not abstractions ("a state management issue").

### Dual Exit Design

Methodology skills must allow structured failure:

```
Success Format:
  Root cause: [specific, file:line]
  Fix: [what changed]
  Verified: [evidence]

Handoff Format (after N failed attempts):
  Symptom: [what was observed]
  Tested: [hypotheses tried and ruled out]
  Unknown: [what information is missing]
  Next: [suggested investigation direction]
```

Without the Handoff Format, AI does one of two things after repeated failure: keeps inventing hypotheses (wasting tokens) or says "I'm stuck" (providing zero value). Handoff turns "I don't know" into a structured, valuable output.

## Artifact-as-Gate: Written Intermediates Before Expensive Work

Direction Lock asks questions. Artifact-as-Gate goes further: **force AI to write a reviewable intermediate file before the expensive operation begins.**

Found independently in 5 different skill families:

| Skill type | Intermediate artifact | Blocks what |
|---|---|---|
| Infographic | `prompts/NN-type-slug.md` | Image generation cannot start until prompt file is saved |
| Article illustrator | `outline.md` with frontmatter | Generation cannot start until outline is confirmed |
| Essay writer | 立意卡 → 骨架卡 | 正文 cannot start until both cards are approved |
| Tweet writer | One line of genuine first reaction | Writing cannot start without real emotional anchor |
| Slide deck | 页码→layout→slot draft table | HTML cannot start until layout plan exists |

Why stronger than a question: artifacts can be **diffed, backed up, reviewed by humans, and fed into validators**. A verbal answer vanishes from context; a file persists.

When to use: any skill where the main output costs significant tokens/time/money to produce. The artifact should contain the key decisions that, if wrong, would waste the entire output.

Pattern:
```
Step N: Write [intermediate] to [path].
Step N+1 is BLOCKED until [intermediate] exists.
[Intermediate] is the source of truth — if regeneration is needed, update the intermediate first.
```

## Recommendation ≠ Authorization

Auto-selected defaults, EXTEND.md preferences, keyword matches, and even explicit skill invocation are all **recommendation inputs**. None of them authorize skipping user confirmation before irreversible work.

A policy worth sharing verbatim across artifact-generating skills:
> "Treat explicit skill invocation, a file path, matched keyword shortcuts, EXTEND.md defaults, and the documented default combination as recommendation inputs only. None of them authorizes skipping confirmation."

The opt-out whitelist is precise — not "if the user seems to agree" but exact phrases:
> `--no-confirm`, "直接生成", "不用确认", "跳过确认", "按默认出图"

When to apply: any skill that generates artifacts the user will publish, send, or cannot easily undo. The pattern pairs with One-Shot Question Design but addresses a different problem: one-shot is about **how** to ask; this is about **whether** auto-selection counts as the user's answer (it doesn't).

Exception design: quick mode may skip most confirmations, but **residual gates** protect the highest-cost decisions. A cover-image quick mode may skip type/palette/rendering but **always asks aspect ratio** — because changing aspect ratio after generation means regenerating everything.
