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
