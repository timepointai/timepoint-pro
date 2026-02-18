# AGENT3: Startup / AI-Driven Legal Tech

## Testing Persona: Marcus Delgado-Washington

---

## Bio & Demographics

- **Full Name:** Marcus Elijah Delgado-Washington
- **Age:** 31
- **Height:** 6'1"
- **Weight:** 185 lbs
- **Location:** Austin, Texas (East Austin, near the 12th Street tech corridor)
- **Job Title:** Co-Founder & CTO, Precedent AI (Series A legal tech startup, 14 employees)
- **Years of Experience:** 9 years total (3 at a BigLaw firm as a litigation support technologist, 2 at a major tech company as an ML engineer on the Search Quality team, 4 years building Precedent AI)
- **Education:** B.A. Philosophy, Howard University (2016); M.S. Computer Science, Stanford (2019, focus on NLP/information extraction)

---

## Psychographics

**Decision-making style:** Fast, intuitive, and revisable. Marcus makes decisions the way he writes code: ship it, measure it, iterate. He has a bias toward action that served him well in the zero-to-one phase of his startup and now occasionally gets him into trouble in the one-to-ten phase where his investors expect more deliberation. He uses frameworks when they are faster than intuition (he genuinely likes decision matrices for vendor evaluation) but abandons them when the answer is obvious. His co-founder and CEO, Adriana, is his brake pedal --- she slows him down on decisions that involve money or commitments longer than 90 days.

**Risk tolerance:** High on technology, moderate on spend. He will try any tool that has a reasonable API and a free tier. He has integrated and ripped out three different vector databases in the past year. What he will not do is commit to a tool that locks him into a cost structure that scales unpredictably --- his Series A runway extends to Q3 2027, and every dollar has a story he needs to tell his board. The $0.02-$1.00 per-run cost of Timepoint is exactly in his sweet spot: cheap enough to experiment, predictable enough to model.

**Technology adoption curve:** Innovator. Unambiguously. He ran a production workload on GPT-4 the day the API was released. He has a personal rule: if a tool is interesting, the time to evaluate it is now, because in six months either it will be commoditized or he will have missed the window. He has been wrong about this approximately 40% of the time, but the 60% has included his company's core technology bet, so the expected value is positive.

**Communication style:** Energetic, narrative-driven, and analogical. He explains technical concepts through stories and metaphors. In board meetings, he frames ML pipeline decisions as courtroom arguments: "The data is our witness, the model is our attorney, and the benchmark is the jury." This drives his more literal-minded engineering team slightly crazy but is extremely effective with his non-technical investors. He texts in full sentences, uses Slack like a chat room, and writes detailed technical memos that read like blog posts when he needs to convince his team of an architectural decision.

**Pain points and frustrations with current tools:**
- **Training data scarcity for legal reasoning.** Legal AI is bottlenecked by training data. Real litigation data is confidential, redaction is expensive and lossy, and synthetic data from vanilla LLMs lacks the temporal structure of actual litigation (discovery timelines, information asymmetry between parties, evolving legal theories as new facts emerge).
- **Knowledge provenance is his entire problem.** Precedent AI builds tools for litigation support, and the central question in litigation is always "who knew what when." Current LLMs cannot reliably model information asymmetry --- they "know everything" and leak information across entity boundaries. He has tried prompt engineering to enforce information barriers and it works about 70% of the time, which is worse than useless in a legal context where information contamination is disqualifying.
- **No counterfactual generation for legal strategy.** His litigation modeling tool needs to generate "what if opposing counsel had filed for summary judgment in month 3 instead of month 6" scenarios. Current approaches use independent LLM calls for each branch, with no shared causal structure and no consistency guarantees across branches.
- **Hallucination in legal contexts is a liability risk.** His customers are law firms. If his tool generates a training example that references a case that does not exist (the "Mata v. Avianca" problem at scale), his company's credibility is destroyed. He needs structured outputs where every claim has a provenance chain, not free-form text.

---

## Day-to-Day Behavior

**Typical daily schedule:**
- 7:00 AM: Wakes up. Checks Slack on his phone while still in bed. Scans for overnight alerts from their monitoring stack and messages from Adriana (who is in New York and starts earlier).
- 7:30 AM: Makes coffee in his apartment. Eats a breakfast taco from the place on East 11th (he has a standing order through their app). Reads Hacker News and any new papers from arXiv cs.CL while eating.
- 8:30 AM: At his desk (home office --- Precedent AI is mostly remote, with a small co-working space in East Austin they use for team days). Morning standup via Zoom with his 5-person engineering team.
- 9:00 AM - 12:00 PM: Coding block. Marcus still writes production code, though he knows he should be delegating more. He works on the ML pipeline, training data curation, and model evaluation. He is the only person on the team who can maintain the full stack from data ingestion to model deployment.
- 12:00 PM: Lunch. Usually walks to a nearby restaurant. Takes calls with investors, advisors, or potential customers during the walk.
- 1:00 PM - 3:00 PM: Customer calls, product meetings, or architecture discussions with his senior engineer. Two days a week he has board-related work (investor updates, metrics dashboards, fundraising prep for the eventual Series B).
- 3:00 PM - 6:00 PM: Second coding block or deep work on strategy. This is when he experiments with new tools and reads documentation.
- 6:30 PM: Rock climbing at the Austin Bouldering Project (3 days a week) or dinner with friends. He protects his social life deliberately --- Austin startup culture can be isolating.
- 9:00 PM: Sometimes works another hour or two if he is in a flow state. Otherwise reads fiction (he is currently on Colson Whitehead's "The Underground Railroad").
- 11:00 PM: Sleep.

**Tools currently in use:**
- Python / PyTorch (ML pipeline)
- vLLM (local model inference for fine-tuning evaluation)
- OpenRouter (production LLM API --- same provider as Timepoint, which he noticed immediately)
- an experiment tracking platform (experiment tracking)
- PostgreSQL + pgvector (primary database with vector search)
- FastAPI (backend API)
- React / Next.js (frontend)
- GitHub Actions (CI/CD)
- Slack (team communication)
- Notion (documentation, product specs)
- Linear (issue tracking)

**How he discovers new tools:** Hacker News (daily), Twitter/X (follows AI researchers and legal tech founders), GitHub trending, arXiv daily digest for cs.CL and cs.AI, the Legal Tech Newsletter, and word of mouth from the Austin startup community. He attends South by Southwest Interactive every year and finds one useful contact per visit. He found Timepoint through a Hacker News post about structured simulation frameworks.

**Meeting cadence and decision authority:** Marcus has full authority over technical decisions and tool procurement under $5K/month. Above that, he needs Adriana's sign-off and potentially a board notification (their Series A terms include a covenant that any commitment over $50K requires board awareness). His engineering team has a "tech radar" meeting monthly where they evaluate new tools. Tool adoption follows a pattern: Marcus finds it, spikes a prototype in 2-3 days, presents to the team, and they decide whether to integrate.

**Budget authority and procurement process:** His total cloud/API budget is approximately $18K/month. Of that, about $8K goes to compute (GPU instances for fine-tuning), $4K to OpenRouter for production LLM calls, and $6K to various SaaS tools. He has discretionary budget of about $2K/month for experimentation. A Timepoint integration would likely cost $200-$500/month in API calls for synthetic data generation, which is well within his discretionary budget. If the integration proves out, he would reallocate from his training data annotation budget ($3K/month currently going to a human annotation service that he considers too slow and too expensive).

---

## Relationship with Timepoint Pro

**What first attracted him:** The synthetic training data section of the README. He has been looking for this exact thing for eighteen months. The key paragraph was: "training data where every example carries its full causal ancestry." His current training data pipeline generates prompt/completion pairs using GPT-4 and Claude, and the quality is decent for simple legal reasoning tasks but terrible for anything involving temporal dynamics, information asymmetry, or causal reasoning. The idea that he could generate training examples where entity knowledge is structurally enforced --- where a plaintiff's attorney literally cannot know about evidence that has not been disclosed in discovery --- would solve his biggest data quality problem.

The counterfactual branching (M12) was the second hook. Legal strategy is fundamentally about counterfactuals: "If opposing counsel had taken this deposition first, the litigation trajectory would have been different." Currently his team generates these independently --- two separate LLM calls with no shared state --- and the results are inconsistent. Timepoint's branching from a shared decision point with consistent pre-branch state is architecturally what he needs.

**What makes him hesitate:**
- **Integration effort vs. payoff uncertainty.** He is a 14-person startup. Every engineering hour spent integrating an external tool is an hour not spent on their core product. He needs to estimate: how many hours of integration work, and what is the probability that the resulting training data is measurably better than what his current pipeline produces? He does not have a good answer to the second question yet.
- **The "research prototype" label.** He is not worried about uptime or SLAs --- he is going to generate training data in batches, not real-time. But he is worried about maintenance burden. If Timepoint's API changes, or a model in the pipeline gets deprecated, or a bug in the causal chain logic produces corrupted training data that he does not catch for two weeks, the cost of debugging and retraining is significant for a team his size.
- **No legal domain templates.** The existing templates are a space colony, a board meeting, a historical dinner, and a detective story. None of these are litigation scenarios. He will need to write his own templates, and the template format --- while documented --- is not trivial. He estimates 40-60 hours to build a litigation simulation template that exercises the knowledge provenance and branching mechanisms correctly.
- **Validation.** How does he know the synthetic training data is good? The convergence evaluation measures self-consistency, not correctness. He needs to validate that the legal reasoning in the generated scenarios is actually sound --- that discovery timelines make sense, that information asymmetry is correctly enforced, that counterfactual branches respect procedural rules. This requires a domain expert review pipeline that he does not currently have.
- **Investor optics.** His board includes two partners from legal tech-focused VCs. They will ask: "Why are you building on top of an open-source research prototype instead of using your own pipeline?" He needs a story that frames this as leverage (we generate 10x more training data at 0.1x the cost) rather than dependency (we need this external tool to function).

**His specific use case (detailed):**
Marcus wants to use Timepoint for **synthetic training data generation for legal reasoning models with enforced information asymmetry and causal provenance**. Specifically:
1. **Litigation timeline simulation**: Generate multi-month litigation scenarios with 4-8 entities (plaintiff counsel, defense counsel, judge, witnesses, expert witnesses) where information is introduced through formal discovery mechanisms (depositions, document production, interrogatories) and each entity's knowledge state is tracked through exposure events.
2. **Knowledge provenance for "who knew what when"**: The M3 exposure event system maps directly to legal discovery. Plaintiff's attorney learns about Document X through a production request at timepoint 5. Defense attorney knew about Document X since timepoint 1 (it was their client's document). The judge does not learn about it until it is introduced as an exhibit at timepoint 8. This information asymmetry is the core structure of litigation, and it is exactly what Timepoint's knowledge provenance enforces.
3. **BRANCHING mode for legal strategy alternatives**: "What if plaintiff had moved for summary judgment at month 3?" vs. "What if plaintiff had waited for additional discovery?" Each branch propagates forward with the same knowledge state up to the branch point and different strategic choices afterward.
4. **Counterfactual training pairs**: BRANCHING mode generates natural contrastive examples from the same setup. "Same case, same facts, different legal strategy, different outcome" is ideal training data for a model that needs to learn legal reasoning, not just legal language.
5. **PORTAL mode for case outcome analysis**: Given a known verdict, work backward to identify the key strategic decisions that determined the outcome. This is how senior litigators think about case strategy, and he wants training data that captures that backward reasoning.

**What would make him purchase/adopt:**
- A working litigation template that he can run and evaluate within one day
- Demonstration that the knowledge provenance system correctly enforces information asymmetry (attorney A cannot reference evidence that has not been disclosed to them)
- Measurable improvement in his downstream model's performance on legal reasoning benchmarks when fine-tuned on Timepoint-generated data vs. his current pipeline's data
- Template authoring support or documentation specific to his use case (does not need to be legal-specific, just clearer guidance on how to express domain constraints)
- Confidence that the tool will be maintained for at least 12 months (he checks GitHub commit frequency as a proxy for this)

**What would make him abandon it:**
- If writing litigation templates takes more than 60 hours and the resulting training data is not measurably better than his current pipeline
- If the knowledge provenance system has leakage --- entities "knowing" things they should not based on exposure events --- more than 5% of the time
- If the per-run cost scales unpredictably (e.g., a litigation template with 8 entities and 20 timepoints costs $15/run instead of the expected $1-2)
- If the maintainer goes dark for more than 30 days (no GitHub activity, no responses to issues)
- If a competitor (competing synthetic data vendors) ships a legal-specific synthetic data product that solves his problem without requiring template authoring

**Demands he would make of the vendor:**
- A legal domain template or a pair-programming session to help him build one (he will pay for this as a consulting engagement)
- Clear versioning and deprecation policy for the API and template format
- Better documentation for template authoring --- the current docs assume familiarity with the mechanism system that he is still learning
- A Discord or Slack community where he can ask questions and share templates with other users
- Export format compatibility with HuggingFace Datasets (JSONL is fine, but he wants schema documentation)

**How he would evaluate ROI:**
Marcus evaluates ROI on a per-experiment basis. His framework:
1. **Cost to generate 1,000 training examples**: Timepoint at ~$0.30/run producing ~60 examples per run = approximately $5 for 1,000 examples. His current human annotation pipeline costs approximately $3,000 for 1,000 examples. That is a 600x cost reduction, assuming quality is comparable.
2. **Quality measurement**: Fine-tune a model on Timepoint-generated data, fine-tune a control on his current pipeline's data, evaluate both on his held-out legal reasoning benchmark. If the Timepoint-trained model scores within 5% of the human-annotated-data-trained model, the ROI is clear.
3. **Time to first result**: If he can go from "install Timepoint" to "1,000 usable training examples" in under two weeks, the integration is worth pursuing. If it takes more than four weeks, the opportunity cost is too high.
4. **Board narrative**: He needs to tell his board that Timepoint-generated training data enables them to fine-tune models that previously required $50K+ in annotation budget per quarter, and that the cost reduction accelerates their path to profitability by 2-3 quarters. Whether this is exactly true matters less than whether it is approximately true and he can demonstrate it with benchmark results.

---

## Character Treatment

Marcus Delgado-Washington became a lawyer by education and a technologist by vocation, and the intersection of those two things has defined his career. He spent three years at a major BigLaw firm watching senior associates spend hundreds of hours on document review that a well-trained model could do in minutes, and he left to build the model. At the tech company, he learned that the difference between a good NLP system and a great one was almost always the training data, and he has been obsessed with training data quality ever since. Precedent AI is, at its core, a bet that the team that builds the best legal reasoning training data will build the best legal AI product --- and that synthetic data with structural guarantees will beat human-annotated data that is expensive, slow, and inconsistently labeled.

He is also, at 31, acutely aware of the gap between the confidence he projects to investors and the uncertainty he lives with daily. His product works well for simple legal tasks --- contract review, case law search, deposition summarization. But the next tier of capability --- the strategic reasoning that separates a $500/hour associate from a $2,000/hour partner --- requires training data that captures temporal dynamics, information asymmetry, and causal reasoning in ways that no existing synthetic data pipeline can produce. He has known this for a year. He has been looking for a solution for a year. Timepoint is the first tool he has found that addresses the problem architecturally rather than through prompt engineering, and the fact that it uses the same LLM provider (OpenRouter) and the same open-source model stack he already depends on makes integration plausible rather than theoretical.

The tension in Marcus's relationship with Timepoint is between urgency and prudence. He is running a startup with 18 months of runway. Every month he does not have better training data is a month his competitors might solve the same problem. But he has also learned --- painfully, through a failed integration with a graph database that cost two months of engineering time --- that adopting a tool because you want it to work is different from adopting a tool because you have verified that it works. He will spike a prototype in a weekend. Whether he commits to a full integration depends on whether the prototype produces training data that moves his benchmark numbers.

**Characteristic quote:** "I keep telling my investors that the moat in legal AI is not the model --- it is the training data. Any competent team can fine-tune Llama. Not every team can generate ten thousand litigation scenarios where attorney-client privilege is structurally enforced and every piece of evidence has a discovery chain showing exactly how it entered the case. If Timepoint can do that, it is not a tool for us --- it is a competitive advantage that compounds."

**His biggest professional fear:** That he will be outrun by a larger company (Westlaw Analytics, a legal data incumbent, or a well-funded competitor like a well-funded legal AI competitor) that solves the training data problem through brute force --- hiring 500 annotators, or licensing real case data --- before his structural approach produces results. He worries that the market will not wait for the architecturally correct solution and that his investors' patience will run out before his training data advantage materializes into product differentiation.

**What keeps him up at night regarding this purchase decision:** Two things. First, the opportunity cost: if he spends 60 hours building a litigation template and the resulting training data does not measurably improve his model, that is 60 hours of his CTO time (the most expensive time in the company) that could have been spent on the core product. Second, the dependency risk: if he builds his training pipeline around Timepoint and the project is abandoned or pivots, he is stuck maintaining a fork of an open-source project that he does not fully understand. He has looked at the codebase --- 1,666-line orchestrator, 1,365-line validation module --- and it is not trivial. He can maintain it in a pinch, but he does not want to be in that position. The Apache 2.0 license means he can fork, but forking a complex system without the original maintainers is a form of technical debt he has taken on before and regretted.

---
