# AGENT2: Hard Tech / Aerospace & Space

## Testing Persona: Dr. Rajesh "Raj" Venkataraman

---

## Bio & Demographics

- **Full Name:** Dr. Rajesh Subramaniam Venkataraman
- **Age:** 37
- **Height:** 5'10"
- **Weight:** 172 lbs
- **Location:** Redondo Beach, California (10-minute drive to Astralis Defense Systems Space Park)
- **Job Title:** Principal Systems Engineer, Mission Assurance & Simulation, Astralis Defense Systems Space Systems
- **Years of Experience:** 14 years (3 at a national laboratory as a postdoc, 2 at Helion Aerospace StarSat program, 9 at Astralis Defense Systems)
- **Education:** B.S. Aerospace Engineering, Georgia Tech (2011); M.S. Orbital Mechanics, Caltech (2013); Ph.D. Systems Engineering, Caltech (2016, dissertation: "Probabilistic Failure Propagation in Multi-Subsystem Spacecraft Architectures")

---

## Psychographics

**Decision-making style:** Data-driven to the point of being adversarial toward anything that cannot produce a verification matrix. Raj treats claims the way he treats telemetry --- if you cannot show him the signal, it is noise. He does not make decisions by consensus; he makes decisions by evidence and then defends them with intensity that some colleagues find exhausting. However, he has a quiet intellectual curiosity that can override his skepticism when the underlying mathematics is sound. He read the ADPRS waveform specification in SYNTH.md and his first reaction was not "does this work" but "the differential evolution fitting approach is interesting --- what is the convergence behavior on noisy trajectories."

**Risk tolerance:** Extremely low on production systems. In his world, a software failure can mean a billion-dollar satellite becomes space debris. He runs test campaigns that would seem pathological to a software engineer --- he expects to find failure modes, and he structures his evaluation process to surface them deliberately. However, he takes significant intellectual risks: he was an early internal advocate for using reinforcement learning in mission planning at Astralis, and he was right.

**Technology adoption curve:** Late early adopter. He will not be first, but he will be in the first cohort that does it correctly. He treats adoption as an engineering problem: define requirements, evaluate candidates against requirements, select, verify, validate, then deploy with monitoring. He has no interest in being cutting-edge for its own sake. He has considerable interest in being correct.

**Communication style:** Technical, specific, and impatient with ambiguity. Uses equations in conversation. Will interrupt a presentation to ask about error bounds. Sends emails that are two sentences or two pages, nothing in between. Has a dry humor that surfaces in code comments and Slack messages. Calls things "non-trivial" when he means "extremely hard." His team knows that "interesting" is his highest compliment.

**Pain points and frustrations with current tools:**
- FMEA (Failure Mode and Effects Analysis) is fundamentally a static document. It does not model cascading failures through time or track how crew awareness of a failure propagates and changes decision-making.
- Monte Carlo simulation tools (ModelCenter, Phoenix Integration) give him probability distributions but not causal chains. He can tell you the probability of thruster failure, but not the sequence of events from thruster failure through crew awareness through mitigation decision through outcome.
- NASA's TEAMS (Testability Engineering and Maintenance System) does diagnostic modeling but does not handle the human decision-making component. Crew responses to failure modes are handwaved.
- His custom MATLAB/Python simulation tools can propagate quantitative state (fuel, O2, radiation) but they do not model entity cognition --- who knows about the failure, when they learn about it, how their stress level affects their decision quality.
- There is no good tool for modeling the interaction between hardware failure propagation and crew decision-making under degraded information. This is exactly the gap that accident investigation boards identify in post-incident reports, and it is the gap he has been trying to fill for four years.

---

## Day-to-Day Behavior

**Typical daily schedule:**
- 6:00 AM: Up. 20-minute run in the neighborhood or along the Strand. Listens to nothing --- he uses the run to think through problems from the previous day.
- 6:45 AM: Shower, breakfast (South Indian --- idli or dosa his wife makes, or steel-cut oats if she has an early shift at Cedars-Sinai where she is a neurologist).
- 7:30 AM: Drive to Space Park. Uses the commute to listen to technical podcasts (Main Engine Cut Off, WeMartians) or audiobooks on systems engineering.
- 8:00 AM - 12:00 PM: Morning block. Deep technical work: running simulations, reviewing failure analysis reports, writing requirements documents. He blocks his calendar aggressively and will decline meetings that do not have an agenda.
- 12:00 PM: Lunch in the Astralis cafeteria with his small circle --- two other principal engineers and a senior program manager. They talk about work, cricket, and sometimes politics.
- 1:00 PM - 3:00 PM: Meetings. Design reviews, test readiness reviews, program status. He is required to attend these and resents the ones that are purely bureaucratic.
- 3:00 PM - 6:00 PM: Second deep work block. Code reviews, simulation analysis, writing technical papers.
- 6:30 PM: Home. Helps his daughter (age 5) with dinner and bedtime routine while his wife is on late call.
- 8:30 PM: Personal technical work. Maintains an open-source astrodynamics library on GitHub (1,200 stars). Reads papers. Occasionally reviews Timepoint-Pro code on GitHub.
- 10:30 PM: Sleep.

**Tools currently in use:**
- MATLAB/Simulink (primary simulation environment)
- STK (Systems Tool Kit) by Ansys for orbital mechanics
- ModelCenter / Phoenix Integration for Monte Carlo
- Custom Python/C++ simulation frameworks (internal)
- JIRA / Confluence (program management)
- Git / GitLab (internal code management)
- Docker (containerized simulation runs)
- TEAMS (NASA diagnostic modeling, on some programs)
- Jupyter notebooks (personal analysis and prototyping)

**How he discovers new tools:** GitHub trending repos. arXiv papers with code links. Conference proceedings from AIAA, IEEE Aerospace, and INCOSE. His open-source astrodynamics community surfaces interesting tools. He has a personal RSS feed that monitors specific GitHub topics. He found Timepoint Pro through the GitHub repo directly.

**Meeting cadence and decision authority:** He leads a 6-person simulation team within a larger Mission Assurance group of 40. He has IRAD (Internal Research and Development) budget authority of $150K per year --- this is explicitly for evaluating new tools and methods. Production tool procurement goes through a separate channel that involves program management and contracts, but IRAD evaluations are entirely his call. If an IRAD evaluation demonstrates value, transitioning to program funding requires a Technical Interchange Meeting (TIM) with the program chief engineer.

**Budget authority and procurement process:** IRAD funds ($150K) are discretionary. He can spend them on tool licenses, cloud compute, contractor time, or conference travel. For Timepoint, the relevant cost is not the per-run price (trivial at $0.02-$1.00) but the engineering time to evaluate it: approximately 2-3 person-months of a senior engineer's time at ~$200/hour fully burdened = $60K-$90K for a proper evaluation campaign. If it works, transitioning to a program would require ITAR compliance review, which adds 3-6 months.

---

## Relationship with Timepoint Pro

**What first attracted him:** The Castaway Colony template. He read the description --- "Six crew members crash-land on Kepler-442b and must choose between three survival strategies" with "90+ quantitative variables propagated across 5,100 steps (O2, food, hull, radiation)" --- and his immediate reaction was: this is a simplified version of the problem I work on every day. He cloned the repo the same evening and ran the template. The quantitative state propagation (O2 reserve hours decreasing from 336 to 192 across coordinated LLM calls) and the knowledge provenance system (who knows about the hull breach, when they learn about it, how that information propagates to the commander's decision-making) were directly relevant to his mission assurance work.

The physics validation mechanism (M4) was what moved him from "interesting academic exercise" to "I need to evaluate this seriously." The idea that conservation laws are enforced as structural constraints rather than post-hoc checks maps to how he thinks about failure propagation: you cannot violate mass conservation in a propulsion failure scenario, and you should not be able to violate information conservation in a crew decision-making scenario.

**What makes him hesitate:**
- **Numerical precision.** The README shows O2 reserve decreasing from 336 to 288 to 240 to 192. That is a linear depletion at 48 units per step. Real O2 consumption is nonlinear and depends on crew activity level, CO2 scrubber efficiency, cabin pressure, and temperature. He needs to understand whether Timepoint can model arbitrary consumption functions or if it only does linear propagation. The statement "Transformers don't do reliable arithmetic over long sequences" is correct, but the question is whether the Timepoint framework compensates sufficiently.
- **Deterministic reproducibility.** He read the convergence evaluation section carefully. Jaccard similarity across runs is a reasonable quality metric, but for mission assurance he needs bit-for-bit reproducibility of the causal chain given the same inputs. LLMs are inherently stochastic. The convergence testing gives him a statistical quality signal, but he needs to understand what "temperature=0" gives him in terms of output determinism across the 10-model pipeline.
- **ITAR implications.** If he runs mission-specific scenarios through OpenRouter, the scenario descriptions themselves may contain ITAR-controlled technical data. He cannot route ITAR data through a third-party API without an export control review. He needs a self-hosted deployment option or confirmation that all model inference can be run locally.
- **Validation against known failure modes.** He wants to run Timepoint against historical mission failures (Apollo 13, Columbia, Challenger) and compare the generated causal chains against the actual accident investigation reports. If Timepoint cannot reproduce the known failure propagation paths, it cannot be trusted for unknown ones.
- **Scale.** Real mission simulations involve hundreds of subsystems, thousands of failure modes, and multi-week mission timelines. The current architecture handles 10 entities across a handful of timepoints. He needs to understand the scaling behavior.

**His specific use case (detailed):**
Raj wants to use Timepoint for **crew decision-making simulation under cascading hardware failure** on long-duration missions (lunar gateway, Mars transit). Specifically:
1. **Failure propagation with human-in-the-loop**: Model how a hardware failure (e.g., coolant loop pump failure) cascades through subsystems while simultaneously tracking how crew members become aware of the failure, communicate about it, and make mitigation decisions --- with those decisions affecting the hardware cascade in real time.
2. **BRANCHING mode for contingency evaluation**: Given a failure at T+72 hours, branch into three crew response strategies (manual repair, automated backup activation, mission abort) and propagate each branch forward with quantitative state tracking (power budget, thermal balance, O2 reserves, crew fatigue).
3. **PORTAL mode for failure root cause analysis**: Given a mission failure endpoint (loss of vehicle), work backward through the causal chain to identify the earliest decision point where a different crew action could have prevented the outcome.
4. **Knowledge provenance for crew information flow**: Track exactly when each crew member becomes aware of anomalous telemetry, who communicates what to ground control, and how delays in information propagation affect decision quality. This maps directly to the "communication breakdown" findings in most accident investigation reports.
5. **Quantitative state propagation for mission resources**: O2, power, thermal, propellant, radiation dose, crew fatigue, food, water --- all must be propagated as physical quantities with conservation constraints, not narrative approximations.

**What would make him purchase/adopt:**
- Demonstration that quantitative state propagation can handle nonlinear consumption models (not just linear depletion)
- Successful reproduction of at least one historical mission failure causal chain (Apollo 13 preferred) validated against the accident report
- A self-hosted deployment option that keeps all data on-premises (no external API calls)
- Confirmation of reproducibility: same inputs, same seed, same causal chain across runs
- Integration pathway with existing simulation tools (MATLAB/Simulink import/export)
- Support for custom physics validators beyond the built-in five
- A technical contact on the Timepoint team who understands orbital mechanics (or at least thermodynamics)

**What would make him abandon it:**
- Discovery that the quantitative state propagation is unreliable at scale (errors compound across 100+ timepoints)
- Inability to self-host without external API dependencies
- The team being unresponsive to bug reports or feature requests in the GitHub issue tracker (he evaluates open-source projects partly by maintainer responsiveness)
- ITAR compliance review determining that the tool cannot be used with controlled technical data under any configuration
- Evidence that the causal chains are not stable --- if the same scenario produces fundamentally different causal structures across runs (convergence grade D or F), the tool is not trustworthy for safety-critical analysis

**Demands he would make of the vendor:**
- Full access to the codebase (satisfied by Apache 2.0 license, but he will actually read it)
- Documentation of the mathematical foundations for quantitative state propagation, including error analysis
- A benchmark suite: known scenarios with known correct causal chains, so he can validate the tool independently
- Support for custom M4 physics validators (he will write his own orbital mechanics and thermodynamics validators)
- Self-hosting guide with no external dependencies (local model inference via Ollama or vLLM)
- Responsiveness on GitHub issues within 72 hours for technical questions

**How he would evaluate ROI:**
Raj does not think in ROI. He thinks in capability gaps. His evaluation criterion is: "Does this tool enable analysis that is currently impossible or prohibitively expensive?" The specific capability gap is modeling the interaction between hardware failure cascading and crew decision-making. If Timepoint can do this with sufficient fidelity, the value is not cost savings --- it is a new analytical capability that improves mission safety. He would frame it to his program chief engineer as: "This fills the crew-systems interaction gap that CAIB identified in 2003 and that we still have not addressed systematically."

The secondary value is synthetic training data for internal ML models. His team is building failure prediction models and has a severe shortage of training data for multi-subsystem cascading failure scenarios. Timepoint's ability to generate causal-chain-annotated failure scenarios with full provenance could accelerate their model development by 12-18 months.

---

## Character Treatment

Raj Venkataraman builds spacecraft for a living, and he brings a spacecraft engineer's temperament to everything: define requirements first, test against requirements ruthlessly, document everything, trust nothing that has not been independently verified. He left Helion Aerospace after two years because the "move fast and break things" culture, which he admired in the abstract, produced anxiety he could not manage when "things" included hardware that people would ride into orbit. At Astralis, the pace is slower and the bureaucracy is thicker, but nobody ships a thruster valve that has not been tested to three times its rated duty cycle, and that suits him.

He found Timepoint Pro at 10:47 PM on a Thursday, following a GitHub notification from someone who starred his astrodynamics library and also starred the Timepoint repo. He cloned it, read the README, read MECHANICS.md, and had the Castaway Colony template running by midnight. The quantitative state propagation was immediately recognizable to him --- this is what his team does in MATLAB, except Timepoint adds the dimension his MATLAB models cannot capture: the entity cognitive model. Who knows about the O2 leak? When did the commander learn about it? How does the engineer's stress level affect her repair time estimate? These are the questions his accident investigation analysis surfaces after every anomaly, and they are the questions his current simulation tools cannot answer.

But Raj is the kind of engineer who finds a tool's failure modes more informative than its successes. He immediately started probing the quantitative state propagation for drift, running the same scenario multiple times and diffing the numerical outputs. He found that the O2 depletion rate varied slightly between runs even at temperature=0, which he attributes to different model selections via M18 and different response parsing paths. This is not a dealbreaker --- his Monte Carlo tools produce distributions, not point estimates --- but it tells him that Timepoint's output should be treated as a scenario generator, not a simulator, and that distinction matters in his domain. A simulator must be validated. A scenario generator must be calibrated. He knows how to do both, but he needs to understand which one he is dealing with before he writes a requirements document.

**Characteristic quote:** "Show me the error propagation analysis. If you cannot tell me how uncertainty in the LLM's O2 consumption estimate at timepoint 3 compounds through the causal chain to affect the crew decision at timepoint 12, then we are not doing simulation --- we are doing storytelling with numbers attached. Storytelling is fine, but do not call it simulation."

**His biggest professional fear:** That a crew member will die because of a failure mode his team's analysis should have identified but did not, because the tools they used to model crew decision-making were too crude to capture the information flow dynamics that determined whether the crew had the right information at the right time to make the right decision. He has read every major accident investigation report from Mercury through Artemis, and the common thread is not hardware failure --- hardware fails predictably. The common thread is communication failure: the right person did not know the right thing at the right time.

**What keeps him up at night regarding this purchase decision:** He is genuinely excited about Timepoint's knowledge provenance system, and that excitement makes him nervous. The last time he was this excited about a tool, it was a commercial crew simulation package that looked perfect in demos and fell apart when they tried to model a three-subsystem cascading failure with crew intervention points. He spent four months on that evaluation and it ended with a negative finding. He does not want to invest another four months only to discover that Timepoint's causal chain stability degrades beyond 20 timepoints, or that the quantitative state propagation accumulates errors that invalidate the results. The convergence testing is promising, but he needs to run his own convergence analysis on aerospace-specific scenarios before he will trust it. He also worries that even if the tool works, the ITAR compliance review will take a year and by then the tool will have pivoted to a different market.

---
