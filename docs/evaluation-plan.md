# cwyde Evaluation Plan

Target venue: *Journal of Biomedical Informatics* (JBI)

---

## Goals

1. Demonstrate that cwyde **replicates** established pyConTextNLP/ConText results on the English test cases used in the original papers (Chapman 2011, Harkema 2009).
2. Benchmark cwyde against the standard English assertion classification dataset (i2b2/n2c2 2010) with NegEx, pyConTextNLP, medspaCy, and transformer baselines.
3. Validate cross-domain generalization on MIMIC-III (different institution and note type from i2b2 training data).
4. Validate the multilingual plugin system on Spanish (NUBes, IULA-SCRC) and Swedish (Stockholm EPR subset / pyConTextSwe).
5. Report where cwyde's richer categories (INDICATION, HISTORICAL, FAMILY) contribute beyond what the gold-standard corpora annotate.

---

## Evaluation 1: Reproducibility (already complete)

### Chapman 2011

- **Source:** Chapman WW et al. "A simple algorithm for identifying negated findings and diseases in discharge summaries." *J Biomed Inform* 2001 (and follow-up pyConTextNLP paper 2011).
- **Cases:** 12 manually curated examples from the pyConTextNLP paper, documenting expected assertion category per target entity.
- **Status:** 12/12 exact match in `tests/reproducibility/test_chapman_papers.py`.
- **Comparison systems:** pyConTextNLP (by construction; these are the paper's own cases).

### Harkema 2009

- **Source:** Harkema H et al. "ConText: An algorithm for determining negation, experiencer, and temporal status from clinical reports." *J Biomed Inform* 2009;42(5):839–851.
- **Cases:** 16 manually curated examples from the ConText paper.
- **Status:** 16/16 exact match in `tests/reproducibility/test_chapman_papers.py`.
- **Comparison systems:** ConText (by construction).

**Note:** These are documented vignettes, not independently distributed corpora. They establish that cwyde's rule base faithfully replicates the original systems' decisions on their own reported examples, but they are not a held-out evaluation.

---

## Evaluation 2: English Primary — i2b2/n2c2 2010 Assertion Challenge

### Dataset

- **Citation:** Uzuner Ö et al. "2010 i2b2/VA challenge on concepts, assertions, and relations in clinical text." *JAMIA* 2011;18(5):552–560. PMC3168320.
- **Size:** 394 train + 477 test discharge summaries and progress notes; 18,550 annotated medical-problem assertions.
- **Annotation scheme (6 classes):**

  | i2b2 label | cwyde mapping |
  |---|---|
  | Present | `DEFINITE_EXISTENCE` |
  | Absent | `DEFINITE_NEGATED_EXISTENCE` |
  | Possible | `PROBABLE_EXISTENCE` / `AMBIVALENT_EXISTENCE` |
  | Hypothetical | `HYPOTHETICAL` |
  | Conditional | `HYPOTHETICAL` (merged — cwyde does not distinguish conditional from hypothetical in v0.2) |
  | Associated | `FAMILY` |

  The Possible → {`PROBABLE_EXISTENCE`, `AMBIVALENT_EXISTENCE`} split cannot be resolved by the gold standard; both cwyde outputs will be scored as Possible for evaluation purposes.

- **Source text:** Partners Healthcare + BIDMC + UPMC discharge summaries and progress notes (de-identified).
- **Institution:** Harvard DBMI.

### Data access

- **Primary access point:** n2c2 NLP Research Data Portal — [https://portal.dbmi.hms.harvard.edu/projects/n2c2-nlp/](https://portal.dbmi.hms.harvard.edu/projects/n2c2-nlp/)
- **DUA required:** Yes. Standard n2c2 Data Use Agreement via the portal. Institutional affiliation required; individual researcher accounts supported.
- **HuggingFace mirror:** `bigbio/n2c2_2010` at [https://huggingface.co/datasets/bigbio/n2c2_2010](https://huggingface.co/datasets/bigbio/n2c2_2010) — note this may require the same DUA or have terms-of-service restrictions; verify before use in publication.
- **Action required:** Apply for access at the n2c2 portal if not already held.

### Comparison systems and published baselines

| System | Type | Best F1 (micro, test set) | Source |
|---|---|---|---|
| NegEx | Rule-based | ~0.85 | Uzuner et al. 2011 |
| ConText | Rule-based | ~0.87 | Uzuner et al. 2011 |
| pyConTextNLP | Rule-based | ~0.89 | Uzuner et al. 2011 |
| Best 2010 challenge system | ML | ~0.94 | Uzuner et al. 2011 |
| Recent transformer fine-tune | DL | ~0.962 | "Beyond Negation Detection," arXiv:2503.17425 |

### Evaluation protocol

1. Apply cwyde (medspaCy + cwyde components) to i2b2 test set without KB modification beyond standard English lexicons.
2. Map cwyde output to the 6-class i2b2 scheme using the table above.
3. Report per-class F1, macro-F1, and micro-F1.
4. Run medspaCy alone (without cwyde layers) as the direct comparison to isolate cwyde's contribution.
5. Compare against published rule-based baselines and the transformer upper bound.

### Scope gaps

- INDICATION has no gold label in i2b2 2010 — report INDICATION fire rate as supplementary information.
- HISTORICAL is not a top-level i2b2 category (it is implicit in note structure) — same treatment.

---

## Evaluation 3: English Cross-Domain — Aken MIMIC-III (2021)

### Dataset

- **Citation:** Aken B et al. "Assertion Detection in Clinical NLP." *EMNLP 2021 ClinicalNLP workshop.*
- **Size:** 5,000 manually annotated assertions from MIMIC-III clinical notes.
- **Annotation scheme:** Same 6-class scheme as i2b2 2010 (Present, Absent, Possible, Hypothetical, Conditional, Associated). Designed for cross-corpus transfer evaluation.
- **Source text:** MIMIC-III (mixed note types — discharge summaries, nursing notes, physician notes); PhysioNet.

### Data access

- **PhysioNet MIMIC-III:** [https://physionet.org/content/mimiciii/](https://physionet.org/content/mimiciii/)
  — CITI training required; DUA via PhysioNet credentialing. UT Southwestern likely already has institutional access.
- **Aken et al. annotation layer:** Released alongside the paper. Check the paper's GitHub or supplementary material for the exact distribution URL. The annotations are a layer on top of MIMIC-III, so MIMIC-III access is the prerequisite.
- **Action required:** Verify MIMIC-III access; locate Aken annotation release.

### Evaluation protocol

Train/tune on i2b2 2010 (no MIMIC-III training data), evaluate on Aken MIMIC-III. This tests domain generalization — the key claim for a rule-based system that should transfer better than models overfitted to Partners/BIDMC note style.

---

## Evaluation 4: Spanish — NUBes

### Dataset

- **Citation:** Lima Lopez S et al. "NUBes: A Corpus for Negation and Uncertainty Detection in Spanish Biomedical Texts." *LREC 2020.* ACL Anthology: [https://aclanthology.org/2020.lrec-1.708/](https://aclanthology.org/2020.lrec-1.708/)
- **arXiv:** [https://arxiv.org/abs/2004.01092](https://arxiv.org/abs/2004.01092)
- **Size:** 29,682 sentences from anonymized Spanish EHRs (private hospital). Annotates negation cues, speculation/uncertainty cues, scopes, and negated/speculated events.
- **Annotation scheme:** Negation + Speculation (cue + scope). The Lima Perez et al. 2023 paper (*Artificial Intelligence in Medicine*, [https://www.sciencedirect.com/science/article/pii/S0933365723001963](https://www.sciencedirect.com/science/article/pii/S0933365723001963)) converts NUBes to a 3-class assertion scheme (Present / Absent / Possible) that maps directly to the cwyde existence axis.
- **License:** Apache 2.0.
- **GitHub:** [https://github.com/Vicomtech/NUBes-negation-uncertainty-biomedical-corpus](https://github.com/Vicomtech/NUBes-negation-uncertainty-biomedical-corpus)
- **Access:** Fully open — no DUA. **This is the only major clinical assertion corpus in any language that requires no data agreement.**

### cwyde category mapping

| NUBes annotation | cwyde mapping |
|---|---|
| Asserted (no cue) | `DEFINITE_EXISTENCE` |
| Negated | `DEFINITE_NEGATED_EXISTENCE` |
| Speculated | `PROBABLE_EXISTENCE` / `PROBABLE_NEGATED_EXISTENCE` / `AMBIVALENT_EXISTENCE` |

### Comparison systems and published baselines

- **Lima Perez et al. 2023:** Best transformer (XLM-RoBERTa fine-tuned) on the 3-class assertion scheme — these are the numbers to compare against. See [https://www.sciencedirect.com/science/article/pii/S0933365723001963](https://www.sciencedirect.com/science/article/pii/S0933365723001963) for per-class F1.
- No published pyConTextNLP / medspaCy baseline on NUBes — cwyde would be the first rule-based system evaluated on this corpus, which is itself a contribution.

### Evaluation protocol

1. Expand cwyde's Spanish KB (`cwyde-knowledge/data/lang/es/`) with NUBes-derived negation and speculation cues.
2. Run cwyde on NUBes text; map output to the 3-class Lima Perez scheme for scoring.
3. Compare against Lima Perez 2023 transformer baseline.
4. Report separately on negation-only (matching IULA-SCRC scope) and full negation+speculation.

### KB development dependency

The Spanish skeleton currently has stub lexicons. A meaningful NUBes evaluation requires populating the Spanish KB — either from the NUBes cue lexicon or from pyConTextSwe-style manual curation. This is the primary development cost for Spanish evaluation.

---

## Evaluation 5: Spanish Secondary — IULA-SCRC

### Dataset

- **Citation:** Marimon M et al. "Annotation of Negation in the IULA Spanish Clinical Record Corpus." *Workshop on Computational Semantics Beyond Events and Roles, ACL 2017.* [https://aclanthology.org/W17-1807/](https://aclanthology.org/W17-1807/)
- **Size:** 3,194 sentences from 300 anonymized Barcelona hospital records. Negation cues and scopes only (no speculation/uncertainty).
- **License:** CC-BY-SA 3.0.
- **Access:** Publicly available — no DUA.
- **Published baseline:** NegEx/pyConTextNLP F1 ~0.92 on negation detection.

### Evaluation protocol

Run cwyde Spanish on IULA-SCRC; compare negation detection (DEFINITE_NEGATED_EXISTENCE) against the published NegEx/pyConTextNLP baseline. Secondary metric: scope delimitation vs. NUBes guidelines.

---

## Evaluation 6: Swedish — Stockholm EPR / pyConTextSwe

### Background

Swedish was one of the earliest non-English pyConTextNLP ports. The key paper is:

- **pyConTextSwe:** Velupillai S, Skeppstedt M, Kvist M, Mowery D, Chapman BE, Dalianis H, Chapman WW. "Cue-based assertion classification for Swedish clinical text — developing a lexicon for pyConTextSwe." *Artif Intell Med* 2014;61(3):137–144. PMC4104142. [https://pmc.ncbi.nlm.nih.gov/articles/PMC4104142/](https://pmc.ncbi.nlm.nih.gov/articles/PMC4104142/)
  - Brian Chapman is a co-author — direct lineage to cwyde.
  - Corpus: Stockholm EPR subset + SEPR-DUC (diagnostic uncertainty corpus).
  - 4-class scheme: definite existence, probable existence, probable negated, definite negated — **exactly** the cwyde existence axis.
  - Reported F1: 88% (DEFINITE_EXISTENCE), 81% (PROBABLE_EXISTENCE), 63% (DEFINITE_NEGATED_EXISTENCE), 55% (PROBABLE_NEGATED_EXISTENCE); binary existence 97%/87%.
  - Lexicon (454 cues) is publicly available.

### Dataset access

All Swedish annotated corpora derive from the **Stockholm EPR Corpus** (Karolinska University Hospital, TakeCare EHR system, 2006–2014).

- **Stewardship:** DSV group, Stockholm University (PI: Hercules Dalianis; Sumithra Velupillai was a key collaborator; she is now at King's College London).
- **Access mechanism:** Research agreement with Stockholm University / DSV. Not a formal DUA portal — contact is required.
  - Dalianis lab page: [https://dsv.su.se/en/research/research-areas/bioinformatics-and-computational-biology/healthbank](https://dsv.su.se/en/research/research-areas/bioinformatics-and-computational-biology/healthbank) (Health Bank project)
  - Contact point: Hercules Dalianis (hercules@dsv.su.se) or current DSV lab contact.
- **Existing relationship:** The Chapman lab co-authored pyConTextSwe with the DSV group. This is the relationship to leverage for data access.

### SweClinEval (2025)

- **Citation:** Vakili T, Hansson M, Henriksson A. "SweClinEval: A Benchmark for Swedish Clinical Natural Language Processing." *NoDaLiDa/Baltic-HLT 2025.* [https://aclanthology.org/2025.nodalida-1.76/](https://aclanthology.org/2025.nodalida-1.76/)
- First public Swedish clinical NLP benchmark with 6 tasks including negation/uncertainty classification.
- Data access managed via agreement given clinical sensitivity — contact authors (Aron Henriksson, KTH).
- This is the most current Swedish clinical benchmark and the right comparison point for transformer baselines.

### Evaluation protocol (contingent on data access)

1. Port the pyConTextSwe 454-cue lexicon into cwyde's Swedish KB (`cwyde-knowledge/data/lang/sv/`).
2. Run cwyde on the same Stockholm EPR subset used in pyConTextSwe.
3. Compare per-class F1 against the pyConTextSwe published numbers.
4. The natural framing: cwyde as a successor to pyConTextSwe — same assertion scheme, richer categories (INDICATION, HISTORICAL, FAMILY), formal doxastic semantics.

### Fallback (if data access is not obtained)

- Port the pyConTextSwe lexicon into cwyde and report lexicon coverage statistics only.
- Evaluate on synthetic or publicly available Swedish clinical case reports (SciELO-style if available).
- Acknowledge in the paper that the Swedish evaluation is lexicon-level only, pending data agreement.

---

## Summary: Data Access Action Items

| Dataset | Language | License / Access | Link | Action |
|---|---|---|---|---|
| i2b2/n2c2 2010 | English | DUA via n2c2 portal | [portal.dbmi.hms.harvard.edu](https://portal.dbmi.hms.harvard.edu/projects/n2c2-nlp/) | Apply for access |
| Aken MIMIC-III 2021 | English | PhysioNet DUA + paper release | [physionet.org/content/mimiciii/](https://physionet.org/content/mimiciii/) | Verify MIMIC-III access; locate annotation release |
| NUBes | Spanish | Apache 2.0 — no DUA | [github.com/Vicomtech/NUBes-negation-uncertainty-biomedical-corpus](https://github.com/Vicomtech/NUBes-negation-uncertainty-biomedical-corpus) | Download immediately |
| IULA-SCRC | Spanish | CC-BY-SA — no DUA | [aclanthology.org/W17-1807/](https://aclanthology.org/W17-1807/) | Download immediately |
| Stockholm EPR / pyConTextSwe corpus | Swedish | Research agreement | [DSV Health Bank](https://dsv.su.se/en/research/research-areas/bioinformatics-and-computational-biology/healthbank) | Contact Dalianis lab via Chapman lab relationship |
| SweClinEval | Swedish | Data agreement | [aclanthology.org/2025.nodalida-1.76/](https://aclanthology.org/2025.nodalida-1.76/) | Contact Aron Henriksson (KTH) |

---

## Metrics

All evaluations use standard token-level assertion classification metrics:

- **Per-class F1** (precision, recall, F1 for each assertion category)
- **Macro-F1** (unweighted average across classes)
- **Micro-F1** (weighted by class frequency — dominated by the majority class, Present/DEFINITE_EXISTENCE)

Where a dataset does not annotate a cwyde category (e.g., INDICATION in i2b2 2010), that category is excluded from F1 computation and reported separately as a fire-rate statistic.

For cross-lingual evaluations (Spanish, Swedish), also report KB coverage: proportion of gold-annotated cue tokens covered by the cwyde lexicon, to separate lexicon-gap errors from algorithm errors.

---

## Comparison Systems

| System | Type | Languages | Notes |
|---|---|---|---|
| NegEx | Rule-based | EN, ES, SV (ports) | Cue-based, no scope |
| ConText | Rule-based | EN | Original Harkema 2009 system |
| pyConTextNLP | Rule-based | EN, SV (pyConTextSwe) | Direct predecessor to cwyde |
| medspaCy (no cwyde) | Rule-based | EN | Ablation: medspaCy alone vs. medspaCy + cwyde |
| XLM-RoBERTa fine-tuned | Transformer | EN, ES, SV | Lima Perez 2023 (ES); "Beyond Negation Detection" arXiv:2503.17425 (EN) |

The medspaCy-alone ablation is the most important comparison — it isolates cwyde's contribution (INDICATION, section propagation, conflict resolution, formal semantics) from what medspaCy provides out of the box.

---

## KB Development Dependencies

Before formal evaluation can run:

| Task | Language | Estimated effort |
|---|---|---|
| Populate `cwyde-knowledge/data/lang/es/` with NUBes-derived negation and speculation cues | Spanish | Medium — NUBes cue lexicon can be semi-automatically adapted |
| Port pyConTextSwe 454-cue lexicon into `cwyde-knowledge/data/lang/sv/` | Swedish | Low — lexicon is public; schema mapping is mechanical |
| Add `sv` language adapter to `cwyde/lang/registry` | Swedish | Low |
| Extend `section_assertions.yaml` with Spanish and Swedish section headers | ES, SV | Medium — requires clinical informatics input |
