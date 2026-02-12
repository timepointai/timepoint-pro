# AGENT4: Research Non-Profit / Rocky Mountain Elk Foundation

## Testing Persona: Dr. Katherine "Kate" Nez-Bridger

---

## Bio & Demographics

- **Full Name:** Dr. Katherine Yazhi Nez-Bridger
- **Age:** 48
- **Height:** 5'5"
- **Weight:** 145 lbs
- **Location:** Missoula, Montana (lives on 3 acres south of town, 25-minute drive to the RMEF headquarters)
- **Job Title:** Director of Conservation Science, Rocky Mountain Elk Foundation
- **Years of Experience:** 23 years in wildlife ecology and conservation (5 at Montana Fish, Wildlife & Parks; 4 as a postdoc at the University of Montana; 6 at the U.S. Fish and Wildlife Service; 8 at RMEF)
- **Education:** B.S. Wildlife Biology, University of Montana (2000); M.S. Ecology, Colorado State University (2003); Ph.D. Landscape Ecology, University of Montana (2008, dissertation: "Winter Range Connectivity and Elk Migration Persistence in the Greater Yellowstone Ecosystem")

---

## Psychographics

**Decision-making style:** Deliberate, evidence-based, and deeply collaborative. Kate does not make unilateral decisions about tools or methods --- she builds consensus among her research staff, runs the idea past her field biologists, and pressure-tests it with the university collaborators who co-author her papers. This is not indecisiveness; it is an institutional survival skill. RMEF is a member-supported non-profit with 235,000 members, many of whom are hunters and ranchers who are skeptical of "computer models" and want to see boots-on-the-ground conservation, not software licenses in the budget. Every dollar Kate spends on technology is a dollar she has to justify to a board that would rather spend it on land acquisition or habitat restoration.

**Risk tolerance:** Low on organizational risk, moderate on methodological risk. She will not adopt a tool that could embarrass the organization if it produces results that are cited in a peer-reviewed paper and later retracted. But she is willing to try novel analytical methods if they have a sound theoretical basis --- her own dissertation used spatial connectivity modeling when it was still relatively new in wildlife ecology. She evaluates tools the way she evaluates field data: does the methodology survive peer review?

**Technology adoption curve:** Early majority, trending toward late majority for anything that requires significant infrastructure. She adopted GIS before most of her peers (early 2000s). She uses R fluently and has dabbled in Python. But she has watched the AI hype cycle with a mixture of interest and irritation. She has seen too many conservation tech startups promise "AI-powered" solutions that turned out to be logistic regression with a chat interface. The word "AI" in a product description actually decreases her interest, because it tells her the vendor is marketing to people who do not understand the methodology. She would respond better to "structured causal simulation" than to "AI-driven scenario modeling."

**Communication style:** Warm, measured, and precise about scientific claims. She distinguishes carefully between "the data show" and "the model suggests" and "we believe." In meetings, she listens more than she speaks and asks questions that reveal she has been thinking three steps ahead. She writes beautifully --- her grant proposals are known among NSF reviewers for their clarity. She uses humor gently, often self-deprecating ("My elk do not read the papers we publish about them"). She is direct about budgets and timelines without being aggressive.

**Pain points and frustrations with current tools:**
- **Temporal scale mismatch.** Her core challenge is modeling ecological systems that operate on multiple temporal scales simultaneously: daily (grazing patterns, predator avoidance), seasonal (migration, calving, rut), annual (population dynamics, mortality), decadal (habitat succession, climate trends), and generational (genetic adaptation, behavioral tradition). No single tool handles all of these scales in a unified framework.
- **Agent-based models are expensive to build and maintain.** Her team has built custom ABMs (agent-based models) in NetLogo for specific studies, but each model takes 6-12 months to develop, is specific to one study, and is unmaintainable after the postdoc who built it moves on.
- **Climate scenario integration is ad hoc.** She needs to model elk population dynamics under different climate scenarios (RCP 4.5, RCP 8.5), but connecting climate projections to habitat models to population models requires stitching together three different tools with incompatible assumptions and time steps.
- **Policy counterfactuals are done on napkins.** When the Montana state legislature proposes a change to hunting regulations or grazing allotments, her board wants to know: "What happens to the Yellowstone herd over 20 years if we implement this policy?" Currently she answers this with expert judgment, literature review, and simple population models. She knows the answer should involve causal modeling of policy through habitat through population dynamics, but she does not have a tool that connects those layers.
- **Predator-prey dynamics are politically charged.** Wolf reintroduction, grizzly bear management, and mountain lion population dynamics are contentious topics where RMEF's credibility depends on rigorous, transparent methodology. She needs models where every causal claim is traceable and defensible, not black-box outputs that opponents can dismiss as "just a computer prediction."

---

## Day-to-Day Behavior

**Typical daily schedule:**
- 5:30 AM: Wakes up. Lets her two dogs (a border collie and a cattle dog mix) out. Makes coffee in a pour-over while looking out at the Bitterroot Range. Checks email on her phone --- she gets up early because her East Coast collaborators and funders are already working.
- 6:30 AM: Breakfast. Reads the Missoulian, checks the RMEF internal news feed, scans Conservation Biology and Journal of Wildlife Management tables of contents if there are new issues.
- 7:30 AM: Drive to RMEF headquarters. Listens to Montana Public Radio or, if she is preparing for a presentation, rehearses talking points out loud in the truck.
- 8:00 AM - 11:30 AM: Morning work block. Data analysis in R, grant proposal writing, or reviewing manuscripts from her research staff. She manages a team of 4 research scientists and 2 GIS analysts, plus seasonal field staff.
- 11:30 AM: Lunch. Often a working lunch --- brown bag in the conference room with her team to discuss ongoing projects, or lunch with RMEF's Land Protection director to coordinate on acquisition priorities.
- 12:30 PM - 3:00 PM: Meetings. Weekly with her VP of Conservation. Monthly with the board's Conservation Committee. Quarterly with university collaborators (UM, MSU, CSU). Ad hoc calls with state wildlife agencies.
- 3:00 PM - 5:00 PM: Field coordination, budget management, or second analysis block. During field season (May-October), she is in the field 2-3 days per week doing vegetation surveys, camera trap maintenance, or elk capture operations.
- 5:30 PM: Home. Feeds the dogs, changes into field clothes, and either gardens, goes for a hike, or rides her horse (a 14-year-old quarter horse named Dinetah) on the trails behind her property.
- 7:00 PM: Dinner with her husband, Tom (a retired smokejumper who now teaches forestry at Missoula College). They eat elk they harvested the previous fall more often than not.
- 8:30 PM: Reads. Currently alternating between Robin Wall Kimmerer's "Braiding Sweetgrass" (a re-read) and a technical volume on integrated population models.
- 10:00 PM: Sleep.

**Tools currently in use:**
- R / RStudio (primary analysis environment --- population models, survival analysis, occupancy models)
- ArcGIS Pro (spatial analysis, habitat mapping)
- MARK (mark-recapture population estimation --- Program MARK by Gary White)
- NetLogo (agent-based modeling, used for 2-3 specific studies)
- Google Earth Engine (remote sensing, NDVI time series for habitat quality)
- Movebank (GPS collar data management for elk migration tracking)
- Excel (budget management, field data entry --- she is not proud of this but it works)
- Zoom (collaborator meetings, board presentations)
- Google Workspace (email, shared documents, presentations)

**How she discovers new tools:** Conference presentations at The Wildlife Society annual meeting, word of mouth from university collaborators, recommendations from other RMEF research staff, and occasionally from papers that cite tools she has not seen before. She does not read Hacker News or follow tech Twitter. She subscribes to the Conservation Biology Listserv and the TWS Spatial Ecology working group email list. She would encounter Timepoint Daedalus only if a university collaborator mentioned it, if it appeared in a conservation biology paper, or if someone in the RMEF network recommended it specifically.

**Meeting cadence and decision authority:** She has authority over her research budget ($380K/year from RMEF operating funds + approximately $600K/year in active grants from NSF, USDA, and state agencies). For technology purchases under $5K, she can act unilaterally. Over $5K requires VP approval. Over $25K requires board Conservation Committee approval. Grant-funded tool purchases must be in the approved budget or require a no-cost extension modification.

**Budget authority and procurement process:** Her technology budget is approximately $35K/year total across her team (hardware, software licenses, cloud compute). ArcGIS licenses consume $12K of that. R is free. NetLogo is free. Cloud compute for GIS processing is approximately $8K. That leaves about $15K/year for new tools, field technology (GPS collars are the big expense but come from a different budget line), and data storage. Timepoint at $0.30/run would be affordable for individual analyses, but she would need to justify the human time investment (learning the tool, building templates, validating outputs) against competing demands on her staff's time.

---

## Relationship with Timepoint Daedalus

**What first attracted her:** A postdoc in her collaborator's lab at the University of Montana sent her an email with the subject line "This might be useful for the migration corridor modeling project" and a link to the README. Kate was skeptical --- she has received many "this AI tool will solve your problem" recommendations --- but the phrase "typed knowledge graph with causal provenance" caught her attention. She read the README and found herself thinking about a specific problem: modeling how a drought in the Madison Valley cascades through vegetation loss, reduced calf survival, changed migration timing, increased human-elk conflict at ranch boundaries, and ultimately affects the population trajectory of the Northern Yellowstone herd over 15 years. That is a causal chain that she currently models in fragments (vegetation in one model, population in another, human dimensions in expert judgment) and has never been able to connect into a unified simulation.

The CYCLICAL mode description was the second hook. Elk ecology is fundamentally cyclical: seasonal migration, annual calving, multi-year population cycles, decadal vegetation succession, and generational behavioral tradition (calves learn migration routes from their mothers). The idea that a simulation framework has a temporal mode specifically designed for cyclical patterns with "prophecy" semantics (which she reinterprets as "predictable recurring patterns that constrain future states") is conceptually aligned with how she thinks about ecological systems.

**What makes her hesitate:**
- **"Research prototype" status.** She needs results she can publish in peer-reviewed journals. If reviewers question the methodology ("you used an LLM-based simulation framework with no established validation in ecology"), her papers get rejected and her grants do not get renewed. She needs precedent --- not the startup, the concept. Has anyone published ecological modeling results using Timepoint or a similar tool?
- **LLM-generated causal chains in ecology.** She is deeply skeptical about whether an LLM --- even with the constraint architecture Timepoint provides --- can generate ecologically valid causal chains. LLMs are trained on text. Elk behavior is governed by physiology, landscape, weather, and evolutionary history. The idea that a language model can produce a reliable causal chain from "late spring snowmelt" to "delayed green-up" to "reduced calf birth weight" to "increased juvenile mortality" requires that the model's training data included enough ecological literature to capture these mechanisms. She does not know whether that is true, and she has no way to verify it without running experiments.
- **No ecological domain templates.** She looked at the template list and found a space colony, a board meeting, a detective story, and a VC pitch. Nothing ecological. She would need to build templates from scratch, and she is not a software engineer. Her R skills are strong but she has never written JSON configuration files for a Python simulation framework. The barrier to entry is real.
- **Quantitative precision for population modeling.** Her population models need to track: elk count (cows, calves, bulls by age class), survival rates (age-specific, sex-specific, cause-specific), recruitment ratios, vegetation biomass (kg/ha by species), snow depth (cm), temperature (daily min/max), precipitation (mm), predation rates (wolf kills/week by pack), and human harvest numbers. The Castaway Colony template tracks O2 and food supplies. Can the framework handle the dimensionality and precision requirements of an ecological model?
- **Cost versus free alternatives.** R is free. NetLogo is free. She has been doing this work for 23 years with free tools. Spending money on a tool --- even $0.30/run --- requires justification that the tool does something her free tools cannot. The causal narrative generation is novel, but she needs to be convinced that the narrative adds analytical value rather than just presentation value.
- **Her board's skepticism about AI.** RMEF's board includes ranchers, outfitters, and businesspeople who are not hostile to technology but are wary of spending conservation dollars on "computer stuff." If Kate proposes buying an AI tool, she needs the pitch to be: "This helps us model elk populations more accurately so we can make better land acquisition decisions" not "This is an interesting new AI framework."

**Her specific use case (detailed):**
Kate wants to use Timepoint for **multi-scale ecological scenario modeling with causal provenance and policy counterfactuals**. Specifically:
1. **CYCLICAL mode for seasonal and generational patterns**: Model the annual cycle of a Yellowstone elk herd (winter range, spring migration, calving, summer range, rut, fall migration, hunting season, winter mortality) over 30 years. Each year is a cycle, but each cycle varies based on weather, predation, habitat quality, and policy. The system should track population state, habitat state, and predator state as quantitative variables propagated across cycles.
2. **BRANCHING mode for policy alternatives**: Given a proposed change to Montana's elk hunting regulations (e.g., increased cow tags in Hunting District 313), branch into three scenarios: (A) current regulations maintained, (B) proposed change implemented, (C) proposed change plus a habitat restoration project on 5,000 acres of winter range. Propagate each branch forward 15 years with population dynamics, vegetation response, and human-elk conflict metrics.
3. **Knowledge provenance for information flow modeling**: Track how ecological information flows through the management system. When does the state wildlife agency learn about a disease outbreak? When does that information reach RMEF? When does it influence land acquisition priorities? This models the institutional decision-making chain that determines whether conservation action happens in time.
4. **PORTAL mode for retrospective analysis**: Given a known population decline (the Yellowstone Northern herd decreased from 19,000 to 4,000 between 1988 and 2010), work backward to identify the causal chain: wolf reintroduction + drought + hunting regulations + habitat fragmentation. Which factors were primary? What alternative management decisions could have moderated the decline? This is the analysis she currently does qualitatively and wants to formalize.
5. **Climate scenario propagation**: Inject different climate projections (temperature +2C, +4C; precipitation -10%, -20%) at the start of a simulation and propagate their effects through the causal chain: climate to vegetation to forage to body condition to survival to population to herd range to human conflict. This connects climate science to management-relevant outcomes in a way her current tools cannot.

**What would make her purchase/adopt:**
- A working ecological template that she can run and understand within one day, ideally modeled on a well-studied system (Yellowstone elk, or something comparably documented)
- Demonstration that the causal chains produced are ecologically defensible --- she will show outputs to her university collaborators and ask whether the causal reasoning is sound
- Evidence that the quantitative state propagation can handle ecological variables with appropriate precision and realistic dynamics (not just linear depletion)
- A publication or preprint using Timepoint for ecological or environmental modeling that she can cite
- Support for non-programmer template authoring (a natural language interface that generates templates, or a guided template builder)
- Endorsement from a wildlife ecologist she respects

**What would make her abandon it:**
- If the causal chains contain ecologically nonsensical relationships (e.g., the model claims increased precipitation decreases vegetation growth without a mechanism for that claim)
- If the quantitative state propagation produces population numbers that violate basic demographic constraints (mortality rates exceeding 100%, negative population counts, recruitment rates that are biologically impossible)
- If the tool requires Python programming beyond what she can accomplish with her existing skills (she can modify scripts but cannot architect solutions)
- If the cost, including staff time for learning and template development, exceeds $10K in the first year without producing publishable results
- If her university collaborators react negatively ("this is a toy") --- peer perception matters in her field

**Demands she would make of the vendor:**
- An ecological domain example, even a simple one (predator-prey dynamics, population cycle, seasonal migration)
- Documentation written for a scientist, not a software engineer --- she wants to understand what the tool does methodologically, not how to configure Docker
- A way to validate outputs against known ecological dynamics (something analogous to the convergence evaluation but against empirical data rather than self-consistency)
- Responsiveness to questions from a non-programmer user --- she will have basic questions about template format, output interpretation, and result validation
- A pricing model or grant-budget-compatible licensing structure (per-run pricing is fine; she just needs to be able to predict costs for a grant budget)

**How she would evaluate ROI:**
Kate does not evaluate tools in financial ROI terms. She evaluates them in terms of:
1. **Analytical capability**: Can this tool answer questions I currently cannot answer? Specifically: can it produce multi-decade causal chains connecting climate, habitat, population, and policy in a single unified simulation?
2. **Publication potential**: Will results generated with this tool survive peer review? Can she describe the methodology in a methods section without reviewers dismissing it?
3. **Management relevance**: Will the outputs inform actual conservation decisions? If she presents Timepoint-generated scenario analysis to the Montana Fish, Wildlife & Parks Commission, will they find it credible and useful?
4. **Time investment vs. payoff**: She estimates 200-300 hours of her team's time over 12 months to learn the tool, build templates, validate outputs, and integrate results into their workflow. If the result is two publishable papers and one management-relevant scenario analysis, the investment is worthwhile. If the result is a interesting tool that does not produce usable outputs, it is not.

---

## Character Treatment

Kate Nez-Bridger grew up on the Navajo Nation in northeastern Arizona, and she was the first person in her family to attend college. She came to Montana for graduate school, fell in love with the landscape and the elk, and never left. Her career has been spent at the intersection of field ecology and quantitative modeling --- she is equally comfortable calibrating a GPS collar on a sedated cow elk and calibrating a survival model in R. The dual fluency is rare and valuable. Her field biologists trust her because she has spent weeks in -20F conditions collecting data. Her quantitative collaborators trust her because she understands that a model is only as good as the data that feeds it and the assumptions that constrain it.

She has watched the technology landscape of conservation science shift over her career --- from paper maps to GIS, from mark-recapture tables to integrated population models, from single-species management to landscape-scale connectivity analysis. Each shift required her to learn new tools, and each time the tools got further from the field and closer to the computer. She is not resentful of this trajectory --- she recognizes that the questions she needs to answer are too complex for the tools she started with. But she is protective of the thing that makes ecology a science rather than an exercise in computation: the requirement that every model be grounded in empirical observation and every causal claim be defensible with data.

When she read the Timepoint Daedalus documentation, she had two simultaneous reactions that she has not yet reconciled. The first was recognition: the knowledge provenance system describes exactly the kind of information flow tracking that she does manually when she reconstructs how a management decision was made. The CYCLICAL mode maps to the seasonal and generational patterns that define elk ecology. The BRANCHING mode is the counterfactual policy analysis she wishes she could do rigorously instead of qualitatively. The second reaction was suspicion: this tool was clearly built for narrative scenarios (a board meeting, a space colony, a detective story), and ecological systems are not narratives. Elk do not have "knowledge states" in the way human entities do. Migration decisions are not "dialog." The framework's vocabulary is wrong for her domain, even if the underlying architecture might be right. She needs to determine whether the architecture can survive a vocabulary translation, or whether the narrative framing is load-bearing.

**Characteristic quote:** "I have spent twenty-three years building models of elk populations, and the one thing every model gets wrong is the connection between what happens on the landscape and what happens in the management system. The elk do not care about hunting district boundaries or budget cycles or public comment periods. The managers do not experience the drought the way the herd does. There is a causal chain from snowpack to forage to body condition to calf survival to population to public perception to political pressure to regulatory change, and no tool I have ever used can model that entire chain. If this tool can do even part of it --- honestly, even just the ecological portion with real provenance --- I am interested. But I need to see it work on a system I understand before I believe it."

**Her biggest professional fear:** That climate change will alter elk migration patterns and habitat suitability faster than the management system can adapt, and that the models she uses to inform management will be wrong in ways that lead to irreversible habitat loss or population collapse. She has already seen early signs: migration timing shifting earlier, winter range shrinking, conflict with agricultural operations increasing. She needs better predictive tools, and she knows it. She is just not sure that a tool built for simulating board meetings can be adapted for simulating ecosystems.

**What keeps her up at night regarding this purchase decision:** Kate does not lose sleep over $200 in API costs. She loses sleep over credibility. Her position at RMEF depends on being the person in the room who can translate between field reality and quantitative analysis, and who never oversells what a model can do. If she adopts Timepoint, builds an ecological template, presents the results to her board or publishes them in a journal, and the methodology is subsequently criticized as "AI-generated storytelling" rather than rigorous ecological modeling, the damage to her professional reputation and to RMEF's scientific credibility would take years to repair. She has seen other ecologists burned by adopting flashy tools that produced impressive-looking outputs with no scientific validity. She will not be one of them. But she also sees, with increasing clarity, that the multi-scale, multi-factor causal modeling she needs to do is beyond what her current toolset can handle, and she is running out of time to wait for the perfect tool. The elk are not waiting.

---
