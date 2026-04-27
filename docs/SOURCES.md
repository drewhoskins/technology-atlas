# Source Quality Report — Bus vertical (v1, 2026-04)

This report covers source selection, quality, and noteworthy contradictions for the inaugural `bus` vertical of the tech-atlas. Ten entries were populated: 1 category, 4 variants, 2 standalones, 3 stubs.

## Tooling note

`WebFetch` was unavailable in the sandbox during population. All raw artifacts were captured via `WebSearch`, which returned substantial verbatim excerpts from the underlying sources (Wikipedia, museum archives, government and academic publications). Every `quoted_text` in a seed's `sources[]` matches text returned by a search call and is preserved in `data/raw/wikipedia/*.txt`. Where a search returned a quote that itself paraphrased a primary source, I treated the search-returned text as the verbatim authority for the atlas (and noted the upstream URL). If `WebFetch` is restored later, re-running extraction against full pages would tighten quotation precision but would not change the underlying claims.

## Validation status

`scripts/build_db.py` could not be executed in this sandbox (Python invocation was disallowed). The seeds were validated by:

1. **`jq empty`** on every seed file plus the manifest — all 11 files are syntactically valid JSON.
2. **Enum cross-check via jq** — every `entry_type`, `relationship`, `EnablingComponent.type`, `Funder.type`, `RegulatoryMoment.effect`, `GeographicDiffusion.milestone`, `KeyDate.event_type`, and `Innovator.recognition_status` value used in the seeds is one of the allowed literals in `tech_atlas/schema.py`.
3. **Referential-integrity cross-check via jq** — every `parent_id` in a seed (`bus` for the four variants, `null` elsewhere) resolves against an entry that exists in the seed set.
4. **Manual schema walk** — every required field of `Entry`, `Source`, `Innovator`, `Predecessor`, `EnablingComponent`, `FailedAlternative`, `Funder`, `RegulatoryMoment`, `GeographicDiffusion`, and `KeyDate` was checked file-by-file. `fetched_at` uses ISO-8601 with `Z` suffix that pydantic v2 parses natively. Confidence values are all in `[0.0, 1.0]`.

The first action on receiving these seeds should be `uv run python scripts/build_db.py` to confirm the manual validation. If anything fails, the most likely class of issue would be a stricter pydantic interpretation of a Literal value than the schema implies — fixable in seconds.

## Sources by atlas dimension — what worked best

| Dimension | Best-performing source class | Notes |
|---|---|---|
| **Innovators** (named individuals) | Wikipedia biographical articles (`Stanislas Baudry`, `George Shillibeer`, `John Boyd Dunlop`, `Nicolaus Otto`, `Jaime Lerner`) | Reliable for names, roles, life dates. Recognition-status calls (headline / well_known / underrecognized / obscure) are subjective and not source-derivable; these were assigned by the populator with the recognition heuristic in `tech_atlas/schema.py`. |
| **Predecessors / lineage** | Wikipedia category articles (`Bus`, `Trolleybus`, `Bus rapid transit`) plus `Carrosses à cinq sols` for the deep-history thread | Wikipedia handles "X evolved from Y" cleanly. Crossing from one variant's predecessor list into another atlas entry's `id` (e.g., `bus:trolleybus → bus:horse_omnibus`) was straightforward. |
| **Enabling components** | Wikipedia + corporate archives (Mercedes-Benz `marsClassic`, Daimler Truck press releases) for engineering specifics | Mercedes-Benz's archive supplied verbatim engine specs (2.9L single-cylinder, 5 PS) for the 1895 Netphen omnibus that no general-history source had. |
| **Failed alternatives** | Wikipedia + secondary history sites (Curbside Classic, history blogs) | Wikipedia's "Articulated bus" and "Trolleybus" articles are good on competing-tech threads. The jitney movement is well-served by Reason Magazine's 1972 retrospective and the Saturday Evening Post's 2022 piece, both of which cite the same primary research. |
| **Funders** | Weakest dimension — sources rarely name funding entities directly. Inferred from organisational histories. | The two strongest funder facts ("Government of China NEV subsidies" and "Soviet state planning ministries") came from Wikipedia category articles (`BYD K series`, `Trolleybus usage by country`). Pre-1900 funders (Pascal's `Duc de Roannez`, Baudry's `Entreprise Générale`) are well-documented in French Wikipedia but the English mirrors are thinner — a French-source pass would deepen this dimension. |
| **Regulatory moments** | Government / academic sources for 20th-century events; Wikipedia for 19th-century events | Best single source: the Rollins Scholarship academic PDF on jitneys, which gave precise municipality counts and dollar amounts for 1915 ordinances. The 1865 UK Locomotive Act ("Red Flag Act") and 1896 repeal are well-documented in Wikipedia but I left the citations sparse here because no search returned a verbatim quote suitable for the strict provenance rule — *this is a gap to close in a future pass.* |
| **Geographic diffusion** | Wikipedia city-history articles + IEA / NREL government case studies | The IEA Shenzhen e-bus case study and NREL Foothill Transit evaluation are the strongest sources for modern fleet diffusion (specific dates, vehicle counts). Wikipedia handles 19th-century diffusion (Paris → Nantes → London) cleanly. |
| **Key dates** | Wikipedia for foundational dates; corporate / museum archives for date-stamped commercial firsts | The 18 March 1895 Netphen opening, the 4 July 1829 London Shillibeer service, and the 29 April 1882 Elektromote demonstration are all multiply-corroborated. Where the corroboration came from a museum (London Bus Museum, London Transport Museum), I treated the museum as the citing source for the contemporary press quote (Morning Post 7 July 1829), which is itself in the public domain. |

## Source quality observations

**Where Wikipedia was strongest.** The deep-history origin stories (`Carrosses à cinq sols`, `Stanislas Baudry`, `George Shillibeer`, `Electromote`, `John Boyd Dunlop`, `Nicolaus Otto`, `Bus rapid transit`) are well-developed Wikipedia articles with primary citations. For a seed that only needs verbatim factual claims, English Wikipedia plus the article's own footnotes is sufficient and the highest-confidence single source.

**Where Wikipedia was thin.** Two recurring gaps:
1. *Funders before 1900.* Pascal's enterprise and Baudry's Entreprise Générale des Omnibus are mentioned but the noble consortia / private subscribers are not detailed in the English articles. French Wikipedia is much better here. A future French-source pass would meaningfully improve the `funders` dimension on the horse-omnibus entry.
2. *Mid-20th-century diesel-bus transition.* The displacement of the gasoline bus by the diesel bus in the 1930s–1950s is poorly covered as a unified story; sources are scattered across manufacturer pages (GMC, Mercedes-Benz, Leyland). I did not produce a separate `bus:diesel` variant for this round because the source quality wouldn't support a deep entry — a known gap to close.

**Where academic / government sources added depth.**
- The **Rollins Scholarship Online** academic paper on jitneys provided the precise "27 municipalities by July 1915" / "90% gone by 1918" / "$10,000 liability bond" facts that turned the jitney entry from anecdote into a quantitative case study.
- The **NREL Foothill Transit Battery Electric Bus Evaluation** (US Dept. of Energy report) supplied the 16.1-mile route length, the 3 September 2010 service start, and the fast-charge architecture details.
- The **IEA Shenzhen e-bus case study** is the canonical source for the 16,000-vehicle full-electrification story.
- The **Mercedes-Benz Public Archive** ("marsClassic") supplied engine-spec verbatim for the 1895 Benz omnibus that no history-of-transport site had — corporate archives are surprisingly under-used as primary sources for early-vehicle facts.

**Where I had to manage contradictions.**
- *Articulated-bus origin.* My initial query referenced a "Gaubschat Berlin 1938 push-pull" articulated bus (a claim I had seen elsewhere but couldn't find in Wikipedia or Curbside Classic). The Wikipedia-corroborated answer is **Milan 1937 / Twin Coach Baltimore 1938**. I went with the corroborated answer and noted the unconfirmed Gaubschat claim in the raw cache.
- *Pneumatic tire priority.* Dunlop is widely credited as the inventor (1888), but his patent was invalidated by Robert William Thomson's 1846/47 patents. Both Wikipedia and Britannica handle this cleanly, and the seed records both — Dunlop as the commercially-successful innovator (`well_known`), Thomson as the prior-art holder (`underrecognized`).
- *Curitiba BRT date.* Streetsblog (2024) and Wikipedia agree on 1974 for the first 20 km, but some secondary sources cite 1972 for "ground-breaking". I went with 1974 (revenue service start), which is what the founding-event sources agree on.
- *"Carrosses à cinq sols" end date.* Wikipedia attributes the 1677 termination to Marc Gaillard; some popular sources say "after Pascal's death in 1662 the service declined and ended a few years later" without a specific date. I used 1677 because the Wikipedia attribution is to a named historian and the popular accounts are vaguer.

## Problematic sources and how they were handled

**Paywalled / ToS-restricted.** None used. Mercedes-Benz `marsClassic` and Daimler Truck press releases are corporate-archive material; I used them only for short attributed verbatim quotes (fair use for non-commercial reference) and flagged them `redistributable: false` in the manifest. Wikipedia and US/IEA government sources, which form the bulk of citations, are CC-BY-SA or public domain and flagged `redistributable: true`.

**Low-confidence individual quotes.** Two confidence levels of 0.85 in the seeds:
- The 1677 end-date for Pascal's carrosses (sourced via "According to Marc Gaillard, the service ran until 1677" — the secondary attribution lowers confidence).
- The "three-quarters of European trolleybus systems are in central/eastern Europe" diffusion claim (sourced via trolleybuses.org, which is a trade site, not a primary census).

**Sources I considered and rejected.** Grokipedia mirrors of Wikipedia content (returned by some searches) were treated as redirects to Wikipedia and not cited directly. Fandom wikis (uktransport.fandom.com, bus.fandom.com) appeared in early searches but were rejected because they re-host Wikipedia content with no additional editorial review and no clear license trail.

## Recommendations for source ordering on future verticals

For a tech-history vertical of this depth, the search-and-extract order that worked best was:

1. **Start with Wikipedia category and key-event articles.** Get the canonical timeline and innovators in one pass. Cite the Wikipedia URLs directly.
2. **Bridge to museum / corporate-archive sources for engineering detail.** Mercedes-Benz, London Transport Museum, Science Museum Group, Smithsonian — these supply verbatim spec-level quotes that Wikipedia summarizes or omits.
3. **Pull government / inter-governmental sources for 20th–21st-century diffusion data.** IEA, NREL, EPA, FTA, Eurostat — reliably produce dated, sourced quantitative claims.
4. **Use academic papers for failed-alternatives and regulatory analysis.** Things like the jitney movement only become quantitative through scholarly retrospectives.
5. **Search non-English Wikipedia (German, French, Portuguese) for non-Anglo origins.** The Benz Omnibus story is much fuller on German Wikipedia; the carrosses à cinq sols and Baudry stories are fuller on French Wikipedia; Curitiba's BRT detail is richer on Portuguese Wikipedia.
6. **Treat trade publications (Sustainable Bus, Streetsblog, Urban Transport Magazine) as corroboration only**, not primary sources — useful for "five recent sources agree" but cite the underlying primary.

A worthwhile follow-up pass would be: a French-language Wikipedia trawl on Pascal/Baudry funders, a German-language trawl on Netphen and the early diesel-bus transition, and a dedicated diesel-bus variant entry once those sources are in cache.

---

# Source Quality Report — Diesel Bus Variant + Backfill (v2, 2026-04-25)

This addendum covers the second-pass population of the bus vertical: the new
`bus:motorized_diesel` variant and a backfill pass on the `sources: []` gaps
flagged in the prior agent's eval.

## Tooling note (v2)

`WebFetch` was again denied in the sandbox; `WebSearch` worked. Direct
execution of `scripts/build_db.py` (and any `python` / `uv` invocation) was
blocked by the harness, so structural validation was performed via `jq`
following the same approach the prior agent used:

1. **`jq empty`** on every modified seed and the manifest — all valid JSON.
2. **Enum cross-check** — every `entry_type`, `relationship`, `EnablingComponent.type`,
   `Funder.type`, `RegulatoryMoment.effect`, `GeographicDiffusion.milestone`,
   `KeyDate.event_type`, `Innovator.recognition_status`, and `Source.ai_or_human`
   value in the new and modified seeds is one of the allowed literals in
   `tech_atlas/schema.py`.
3. **Confidence bounds** — all `confidence` values in the new seed are in
   [0.85, 0.95], well within the schema-required `[0.0, 1.0]`.
4. **Year-type check** — all `year` fields are JSON numbers (not strings).
5. **Raw-id integrity** — every `raw_id` used in the new diesel seed and in
   the gasoline-seed backfill resolves against an `id` in
   `data/raw/manifest.json` (15 new manifest entries added).
6. **Parent-id integrity** — `bus:motorized_diesel` has `parent_id: "bus"`,
   which resolves to the existing `bus` category entry.

If `uv run python scripts/build_db.py` reveals any pydantic-strictness
mismatch I missed, the most likely culprit (per the prior agent) is a
Literal-value typo — fixable in seconds.

## What German and French Wikipedia delivered that English was missing

The prior eval explicitly recommended a German-language trawl for the
diesel-bus transition story, and that recommendation paid off. English
Wikipedia covers the diesel engine well (Rudolf Diesel, MAN-Augsburg
prototype, 1893 patent) but thins out sharply on the engine-to-bus jump.
The richest material came from a triangle of German-aware sources:

* **`de.wikipedia.org/wiki/Mercedes-Benz_O_305`** and its English mirror
  identified the VöV-Standard-Bus framework as the canonical late-20th-century
  city-bus design — the Daimler O 305 (1969, 16,000 units) was just one
  manufacturer's implementation of the same standardised dimensions, doorways
  and chassis interfaces also produced by Büssing, Magirus-Deutz, MAN, Ikarus,
  Gräf/Steyr, Heuliez, Renault and Pegaso. English-only sources tend to
  describe the O 305 as a Mercedes product rather than as the canonical
  example of an industry-wide standard.
* **`daimlertruck.com` corporate-archive press release on the 1923 OB 2
  diesel** supplied the precise pre-chamber-system date (14 April 1923
  decision to commence series production) and the 86% fuel-saving figure
  vs. the petrol engine. No English Wikipedia article had this detail.
* **`trans.info` (a German trade publication translated to English)** was
  the only source that gave a clear, datable identification of the
  *first series-production* diesel bus: the Daimler-Benz N 56 in 1928.
  It also dated the MAN NOB diesel option to 1926 — three years earlier
  than the 1928 Daimler series production. Both facts were either absent
  or muddled in English-language sources.
* **`fr.wikipedia.org/wiki/Réseau_de_bus_RATP`** — French Wikipedia gave a
  much clearer account of the 1930 STCRP tramway-to-bus replacement in
  Paris (the canonical European municipal example of diesel-bus
  procurement displacing rail) than any English source. The same article
  also identified Renault's first diesel bus engines (1930–31) with
  precise displacements (7 L / 10.5 L direct-injection).
* **`en.wikipedia.org/wiki/Bus_transport_in_Berlin`** — even the English
  Berlin article had a German-source-derived nugget that English
  Wikipedia's bus-history pages didn't surface: the October 1923 IAA
  exhibition where Daimler showed its 5C diesel bus alongside the truck
  and tipper. That date pins down "first public showing of a diesel-engined
  bus chassis" two months after the OB 2 truck's first road test.

The pattern: where a German manufacturer is centrally involved (Benz, MAN,
Daimler), English Wikipedia tends to summarize while German Wikipedia
records the dated detail. The same holds for French Wikipedia and Renault.
Both languages were essential for the diesel variant.

## Contradictions and priority disputes encountered

* **"First diesel bus" is genuinely contested.** The strongest case is
  MAN NOB (1926, optional diesel engine), but Daimler-Benz N 56 (1928, first
  series production) is the more frequently cited "first" because series
  production has more economic weight than an optional engine spec. The
  seed credits MAN with the chassis-first crown (1926) and Daimler with the
  series-production-first crown (1928), avoiding the false binary. Benz &
  Cie's 1923 prototype bus shown at the IAA is treated as a "first showing"
  rather than a "first commercial bus."
* **GM Yellow Coach 1938 vs. 1947.** Curbside Classic frames the 1947
  PD-3751 Silversides as "the first modern diesel bus." Wikipedia's Yellow
  Coach article credits the 1938 Model 719 (~400 units, 6-71 Detroit Diesel)
  as "the first truly competitive diesel coach." Both can be true — the
  1938 vehicle was the technical breakthrough, the 1947 vehicle was its
  commercial maturation. The seed records the 1938 date as the North
  American `first` milestone and notes the 1947 PD-3751 in the innovator
  contribution text.
* **"Diesel displaces gasoline" date (Europe vs. US).** Wikipedia's
  Diesel-engine article asserts diesel was "the most common power source
  since the 1920s" for buses, which is true for German production but
  optimistic for Western Europe as a whole and clearly wrong for the US
  (where 1938 is the inflection point and full saturation arrives in the
  late 1950s). The seed treats the European 1pct → 10pct → saturation
  curve as 1928 → 1930 (Paris) → 1969 (Western Europe regional saturation
  at the O 305 launch), and notes the US joined later via Yellow Coach 1938.

## How the backfill went

The eval flagged six high-priority `sources: []` gaps. Five of six were
straightforward to backfill from English Wikipedia; one (`bus:trolleybus`
1882 founding entry on `bus:motorized_gasoline.predecessors[]`) was already
sourced indirectly via the trolleybus's own description; I added an
explicit Electromote citation to close it cleanly.

| Gap | Source used | Difficulty |
|---|---|---|
| `bus_motorized_gasoline.predecessors[].steam_bus` | Wikipedia Locomotive_Acts (Red Flag Act) | Easy |
| `bus_motorized_gasoline.predecessors[].trolleybus` | Wikipedia Electromote | Easy |
| `bus_motorized_gasoline.failed_alternatives[].steam_omnibus` | Wikipedia Locomotive_Acts (1865 + 1896 repeal) | Easy |
| `bus_motorized_gasoline.regulatory_moments[].1865_red_flag` | Wikipedia Locomotive_Acts (verbatim 60-yards-ahead quote + railway-lobby attribution) | Easy |
| `bus_motorized_gasoline.regulatory_moments[].1896_repeal` | Wikipedia Locomotive_Acts (1896 light-locomotive class) | Easy |

I did not pursue the longer tail of `sources: []` arrays in the trolleybus,
horse-omnibus, BRT, and battery-electric seeds — those were lower priority
in the eval and cover dimensions (e.g., `enabling_components[].pneumatic_tire`
on trolleybus) where the description-level citation already supports the
claim. A future pass should target them; the German-language trawl for
diesel didn't surface unique sources for those gaps, so they need a
different source pass (e.g., trolleybuses.org for Soviet trolleybus dates,
Russian-language Wikipedia for ZiU-9 specifics).

## Sources newly added to manifest (v2)

15 new artifact entries, bringing the manifest from 25 to 40:

* English Wikipedia: Rudolf Diesel, Diesel engine, Mercedes-Benz O305,
  Yellow Coach Manufacturing Company, European emission standards,
  Ultra-low-sulfur diesel, London Electrobus Company, Locomotive Acts,
  Bus transport in Berlin
* German/French Wikipedia: fr_wikipedia: Véhicules utilitaires Renault 1930,
  fr_wikipedia: Réseau de bus RATP
* Trade / corporate / government: Daimler Truck press release (1923 OB 2),
  trans.info (1928 N 56), EPA Clean Air Act evolution page, Low-Tech
  Magazine wood-gas-vehicles essay

All Wikipedia entries are CC-BY-SA-4.0 and `redistributable: true`. Corporate
press releases and trade publications are flagged `redistributable: false`
under fair-use citation; government works (EPA) are public-domain.
Low-Tech Magazine asserts CC-BY-SA-3.0 on its content, treated as
redistributable.

## Recommendations for the next pass

1. **More US-side diffusion datapoints.** The diesel variant has Paris 1930
   and a regional Western European saturation 1969, but no New York / London
   /Chicago city-level milestones. A pass through `nyct.info` and the FTA
   National Transit Database would close this.
2. **Battery-electric retrofit story.** When the diesel bus phases out, the
   pattern in cities like Shenzhen is *retrofit*, not *replace* — the
   chassis stays, the engine swaps. This is a 2020s story not yet captured
   in the atlas.
3. **A `component:diesel_engine` stub.** Defensible — Rudolf Diesel and the
   1893–1897 Augsburg prototype have enough biographical and corporate
   detail to support a stub similar in shape to
   `component:internal_combustion_engine`. Not added in this pass to keep
   the diesel-variant seed as the primary deliverable, but the source
   material is already in the cache (`Diesel_Bus_History.txt`).
4. **Hybrid-electric variant.** The diesel-electric hybrid bus
   (Allison/BAE Systems Orion VII, 1998–2010s) is the actual technology
   bridge between the diesel bus and the modern battery-electric bus, and
   currently appears only as a passing reference in the battery-electric
   seed. A `bus:hybrid_electric` variant would close the propulsion-tree
   gap. The eval already lists this as suggested extension #8.

