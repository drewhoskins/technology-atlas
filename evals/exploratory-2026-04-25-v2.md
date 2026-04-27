# Exploratory query test v2 — 14 bus history questions (post-diesel-addition)

**Atlas state (counts by entry_type):** 11 entries total — 1 `category` (`bus`), 5 `variant` (`bus:horse_omnibus`, `bus:motorized_gasoline`, **`bus:motorized_diesel` — new in v2**, `bus:trolleybus`, `bus:battery_electric_modern`), 2 `standalone` (`standalone:bus_rapid_transit`, `standalone:jitney_movement`), 3 `stub` (`component:internal_combustion_engine`, `component:pneumatic_tire`, `component:articulated_bus`). All entries are in domain `transit`. (Counts derived from direct read of `data/seeds/`; see methodological note.)

**Tester:** Sub-agent run, second pass after diesel addition + source backfills.
**Date:** 2026-04-25
**Purpose:** Re-run the v1 exploratory test now that (a) `sqlite3` is supposedly pre-allowed in `.claude/settings.json`, (b) a `bus:motorized_diesel` variant has been added, and (c) some empty `sources: []` arrays have been backfilled. Compare coverage against v1.

---

## Methodological note (sqlite3 status)

**`sqlite3` was again blocked by the harness on this run, despite `.claude/settings.json` listing `Bash(sqlite3 data/atlas.db:*)` and `Bash(sqlite3 ./data/atlas.db:*)` in `permissions.allow`.**

What I tried:

1. `sqlite3 data/atlas.db "SELECT entry_type, COUNT(*) FROM entries GROUP BY entry_type;"` — denied by harness ("Permission to use Bash has been denied").
2. `sqlite3 /Users/drewhoskins/tech-atlas-prototype/data/atlas.db "..."` (absolute path) — denied.

The relative-path form matches the configured allow pattern verbatim, and the working directory is the project root, so the denial is **unexpected**. Possible explanations (cannot verify from inside the harness):

* The allow rule pattern does not match the way Claude Code's permission engine canonicalises commands (e.g., requires no leading `./` or `/`, or expects a different glob form).
* `settings.local.json` is empty/missing and an organisation-level deny rule is overriding the allow.
* The harness this sub-agent runs in inherits a more restrictive policy than the parent session.

**Per the user's instruction, I fell back to reading `data/seeds/*.json` directly.** This worked. Every SQL query shown below is what I *would* have executed against `data/atlas.db`; the "Raw results" sections summarize what those queries return based on direct seed reads. Per `docs/SCHEMA.md`, "the DB is rebuilt from seeds via `scripts/build_db.py`", so the seeds and the DB are equivalent for read queries.

**This is a regression vs. v1's expectation.** v1 ran without sqlite3 access too (and called it out as an eval signal); v2 was supposed to validate that the SKILL.md's "query via direct SQL" promise is now testable end-to-end. It is not.

**Recommended action:** add an explicit harness-level test (e.g., a startup probe that runs `sqlite3 data/atlas.db ".tables"` and surfaces a clear error if it fails) so this failure mode cannot be silently routed around. See "Eval-precursor signal" at the end.

---

## Q1: Who invented the motorized bus, and where? What were the key priority disputes?

**SQL:**
```sql
SELECT json_extract(i.value, '$.name')               AS name,
       json_extract(i.value, '$.role')               AS role,
       json_extract(i.value, '$.country')            AS country,
       json_extract(i.value, '$.year')               AS year,
       json_extract(i.value, '$.recognition_status') AS recognition,
       json_extract(i.value, '$.contribution')       AS contribution
FROM entries e, json_each(json_extract(e.data, '$.innovators')) i
WHERE e.id = 'bus:motorized_gasoline'
ORDER BY year;
```

**Raw results:**
```
Nikolaus Otto                 | well_known       | Germany | 1876
Carl (Karl) Benz              | headline         | Germany | 1895
Netphener Omnibusgesellschaft | underrecognized  | Germany | 1895
```

**Atlas-grounded answer:**
The atlas attributes the motorized (gasoline) bus to a **two-party event in Germany, 18 March 1895**: Carl Benz's Benz & Cie built the vehicles, the Netphener Omnibusgesellschaft operated the line.

According to the Mercedes-Benz Public Archive (https://mercedes-benz-publicarchive.com/marsClassic/en/instance/ko/Benz-buses-1895--1898.xhtml?oid=16438713): *"The Benz Omnibus was the first internal combustion engine-powered omnibus in the world, built by Benz & Cie of automotive pioneer Carl Benz and had eight seats, including the driver's seat."*

According to Urban Transport Magazine (https://www.urban-transport-magazine.com/en/130-years-of-motor-bus-service/): *"On 18 March 1895, the world's first public transport line operated by a motorised bus rather than a stagecoach was opened. The newly founded Netphener Omnibusgesellschaft opened the first ever bus route from Siegen via Netphen to Deuz."*

The atlas does not record a "priority dispute" over the bus itself, but surfaces one **at the propulsion-component layer**. According to Wikipedia (https://en.wikipedia.org/wiki/Nicolaus_Otto): *"Although Otto was the first to build an engine based upon this principle, the four-stroke cycle was patented in 1862 by the French engineer Alphonse Beau de Rochas, but it is commonly known as the Otto cycle."* The component:internal_combustion_engine entry's 1877 key_date notes Otto's German patent was *"later partially invalidated due to Beau de Rochas's prior art, but commercial dominance was already established."*

**v2 addition (diesel layer):** the new `bus:motorized_diesel` entry adds a **different** priority story for the *diesel* propulsion: Rudolf Diesel built the engine, but only with explicit consortium funding from Krupp + Maschinenfabrik Augsburg. Per Wikipedia (https://en.wikipedia.org/wiki/Diesel_engine): *"In April 1893, Diesel and Krupp signed a contract that allows Diesel to build a prototype engine, and both Krupp and the Maschinenfabrik Augsburg decided to collaborate and build a single prototype in Augsburg."* This is more a co-invention/funding story than a priority dispute, but it bears noting because it parallels the Otto/Benz pattern (theorist + industrial sponsor + manufacturer).

**Coverage assessment:** complete (for the gasoline bus); rich (priority disputes exist but at the component layer). The diesel addition does not change Q1's headline answer but adds a parallel pattern.

---

## Q2: What were the predecessors to the motorized bus — horse omnibus, steam, trolleybus?

**SQL:**
```sql
SELECT json_extract(p.value, '$.name')           AS name,
       json_extract(p.value, '$.relationship')   AS relationship,
       json_extract(p.value, '$.year')           AS year,
       json_extract(p.value, '$.brief')          AS brief,
       json_extract(p.value, '$.linked_entry_id') AS linked
FROM entries e, json_each(json_extract(e.data, '$.predecessors')) p
WHERE e.id = 'bus:motorized_gasoline'
ORDER BY year;
```

**Raw results:**
```
Horse-drawn omnibus       | evolved_from         | 1826 | linked: bus:horse_omnibus
Steam bus / steam carriage| competing_predecessor| 1830 | linked: null
Trolleybus (Elektromote)  | competing_predecessor| 1882 | linked: bus:trolleybus
```

**Atlas-grounded answer:**
The atlas records all three predecessors the question names, with explicit relationship typing:

* **Horse-drawn omnibus (1826) — `evolved_from`.** Per the motorized gasoline bus entry: *"The motorbus inherits the horse omnibus's route-and-timetable model wholesale; only the propulsion changes. In the 1890s and 1900s many cities ran horse and motor buses on the same routes side-by-side."* (`sources: []` on this element — narrative is implicit-in-description.)
* **Steam bus / steam carriage (1830) — `competing_predecessor`.** Now backed by an inline source on the failed-alternatives side. Per Wikipedia (https://en.wikipedia.org/wiki/Locomotive_Acts): *"The Locomotive Act 1865 (also known as the 'Red Flag Act') was introduced as a result of the increasing popularity of self-propelled traction engines (known then as 'road locomotives') on British public thoroughfares after 1850."* (**v2 backfill:** v1 noted the steam-bus predecessor element had `sources: []`; this remains true on the predecessor element itself, but the related Locomotive Acts source IS attached on the same entry's `failed_alternatives` for the steam omnibus, so the audit trail is reachable cross-array.)
* **Trolleybus / Elektromote (1882) — `competing_predecessor`.** Per Wikipedia (https://en.wikipedia.org/wiki/Electromote): *"The Electromote was the world's first vehicle run like a trolleybus, which was first presented to the public on April 29, 1882, by its inventor Dr. Ernst Werner von Siemens in Halensee, a suburb of Berlin, Germany."*

The horse omnibus itself has its own deep lineage in the atlas (Pascal 1662 → Baudry 1826 → Shillibeer 1829), with stagecoach (1640) listed as `evolved_from` and hackney coach (1620) as `competing_predecessor`.

**Coverage assessment:** complete. v2 source-backfill on the Locomotive Acts narrative tightens the audit trail (was missing in v1 in the form most useful to a reader).

---

## Q3: Give me a timeline of bus adoption in major cities, 1900-1930.

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(g.value, '$.place')     AS place,
       json_extract(g.value, '$.year')      AS year,
       json_extract(g.value, '$.milestone') AS milestone,
       json_extract(g.value, '$.brief')     AS brief
FROM entries e, json_each(json_extract(e.data, '$.geographic_diffusion')) g
WHERE CAST(json_extract(g.value, '$.year') AS INTEGER) BETWEEN 1900 AND 1930
ORDER BY year;
```

**Raw results:**
```
1911 | London, United Kingdom              | saturation | bus:motorized_gasoline
1915 | Western and southern United States  | 10pct      | standalone:jitney_movement
1923 | Berlin (Marienfelde + IAA), Germany | first      | bus:motorized_diesel  ← NEW in v2
1928 | Germany (national)                  | 1pct       | bus:motorized_diesel  ← NEW in v2
```

**Atlas-grounded answer:**
The 1900–1930 window now contains **four** city/regional diffusion datapoints (up from one in v1). The diesel addition added two of them.

* **UK — London, 1911 (saturation, gasoline bus).** Per the motorized gasoline bus entry (no inline source URL on this element): *"London's last horse omnibus is withdrawn. The motorbus has effectively replaced the horse on London streets within sixteen years of the Netphen experiment."*
* **US — western/southern states, 1915 (10pct, jitney).** Per Reason (https://reason.com/1972/02/01/taxis-and-jitneys/): *"By March 1915, thousands of jitneys operated in the southern and western United States."*
* **Germany — Berlin, 1923 (first, diesel bus). v2 NEW.** Per Wikipedia (https://en.wikipedia.org/wiki/Bus_transport_in_Berlin): *"The first Daimler 5C commercial diesel vehicles produced in Marienfelde – a truck, a three-sided tipper and a bus – were presented at the beginning of October 1923 at the Berlin automobile exhibition."*
* **Germany — national, 1928 (1pct, diesel bus). v2 NEW.** Per trans.info (https://trans.info/en/history-transport-part-7-first-business-diesel-omnibuses-88347): *"In 1928, Daimler-Benz produced a series-production bus with diesel engine. More specifically, in 1928, Daimler-Benz sent its first series-production bus on a promotional journey – the three-axle N 56."*

The European city-by-city motorbus rollout (Paris, individual German cities, etc.) is still mostly unrepresented for the *gasoline* line, but the diesel entry meaningfully closes the German gap.

**Coverage assessment:** **partial → improved from v1's "sparse"**. Doubled the data density (1 → 4 datapoints) with the diesel addition; still missing Paris, New York, Chicago, Berlin gasoline rollout, etc. before 1930.

---

## Q4: How did regulation in different countries shape the early bus industry?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(r.value, '$.year')         AS year,
       json_extract(r.value, '$.jurisdiction') AS jurisdiction,
       json_extract(r.value, '$.effect')       AS effect,
       json_extract(r.value, '$.description')  AS description
FROM entries e, json_each(json_extract(e.data, '$.regulatory_moments')) r
ORDER BY year;
```

**Raw results (early-bus + diesel windows):**
```
1662 | Parlement of Paris (France)             | restricting | Bars commoners from carrosses
1826 | Municipality of Nantes (France)         | enabling    | First municipal bus license to Baudry
1865 | UK (Locomotive Act / 'Red Flag Act')    | restricting | 4 mph cap, man with flag
1882 | Berlin (Halensee), Germany              | enabling    | Permission for Elektromote
1896 | UK (Locomotives on Highways Act)        | enabling    | Repealed Red Flag
1915 | 27 US municipalities                    | restricting | Anti-jitney $10k bonds
1915 | Salt Lake City, Utah                    | restricting | SLC fleet 40→2
1916 | San Francisco                           | restricting | Jitney Bus Ordinance
1968 | Curitiba, Brazil                        | enabling    | Master Plan
1970 | US (Clean Air Act amendments)           | restricting | EPA authority on diesel  ← v2 NEW
1990 | US (1990 CAA Amendments)                | restricting | 92% PM cut for urban buses ← v2 NEW
1992 | EU (Council Directive 91/542/EEC)       | restricting | Euro I heavy-duty         ← v2 NEW
2006 | US (EPA Highway Diesel Rule) + CARB     | mixed       | ULSD mandate              ← v2 NEW
2017 | Shenzhen, China                         | enabling    | Full-fleet electrification
2018 | Madrid (and Paris/London)               | restricting | Low-emission zones        ← v2 NEW
2019 | EU (Clean Vehicles Directive 2019/1161) | enabling/restricting | Procurement targets
```

**Atlas-grounded answer:**
The atlas now shows **four** regulatory regimes for the early bus and a much richer **late-20th-century emissions sequence** for diesel (six new regulatory moments).

* **France (enabling, route-licensed).** Per Wikipedia (https://en.wikipedia.org/wiki/Omnibus): *"The company appeared publicly on August 10, 1826, after obtaining permission from the municipality, and began operating on September 30, 1826."* The horse-omnibus entry adds: *"The bus business is a regulated business from day one; route licensing is a recurring theme across the variants."*
* **United Kingdom (initially crippling, then liberating).** v2 backfilled the Locomotive Acts source. Per Wikipedia (https://en.wikipedia.org/wiki/Locomotive_Acts): *"The Locomotives Act 1865 (the 'Red Flag Act') imposed on road locomotives a speed limit of 2 mph in towns and 4 mph in the country. It increased the crew to three, of which one was to walk 60 yards ahead carrying a red flag."* And the 1896 reversal: *"The Locomotives on Highways Act 1896 defined a new class of light locomotives weighing less than 3 tons, to which the 1861, 1865 and 1878 Locomotive Acts did not apply. This removed from such vehicles the requirement for a crew of three with one man walking ahead, the speed limits and the bridge restrictions."* (**v1 flagged both as missing inline source URLs — v2 backfilled both.**)
* **Germany (enabling, technology-tolerant).** Per Wikipedia (https://en.wikipedia.org/wiki/Electromote): *"The world's first trolleybus operated from April 29 to June 13, 1882, on a 540 m (591 yard) trail-track starting at Halensee railway station."*
* **United States (incumbent-protecting against new entrants, then emissions-heavy).** The 1915–1916 anti-jitney ordinances remain the most extensively documented regulatory moment in the atlas. Per Rollins (https://files01.core.ac.uk/download/pdf/235715894.pdf): *"By July 1915, twenty-seven municipalities had already imposed burdensome liability costs to all jitney drivers. Drivers were compelled to post up to $10,000 in liability insurance, biting into 25 to 50 percent of drivers' annual earnings."* **v2 NEW** adds the late-20th-century US emissions sequence — 1970 CAA empowering EPA, per EPA (https://www.epa.gov/clean-air-act-overview/evolution-clean-air-act): *"The first on-road diesel emission standards established by the EPA went into effect in 1974, specifically targeting carbon monoxide (CO), and hydrocarbons and nitrogen oxide (HCa+NOx)."* And the 1990 amendments: *"The 1990 amendments required new urban buses to reduce emissions of diesel particulates 92% by 1996, and all other heavy-duty diesel engines to achieve an 83% reduction by the same year."*
* **EU emissions sequence (v2 NEW).** Per Wikipedia (https://en.wikipedia.org/wiki/European_emission_standards): *"Euro I standards were introduced in 1992 and followed by the introduction of Euro II regulations in 1996. These standards applied to both truck engines and urban buses; the urban bus standards, however, were voluntary."*
* **Modern urban diesel bans (v2 NEW).** Madrid Central (2018, source on the regulatory_moment is empty `[]` but the description is rich — gap), Paris, London ULEZ, Barcelona — first wave of city-centre diesel bans.

**Coverage assessment:** **complete → improved from v1's "complete for headline regimes"**. The full UK source backfill closes the most-flagged v1 gap. The diesel emissions sequence is a substantial addition that makes the atlas usable for late-20th-century regulatory history of the bus, not just early-20th.

---

## Q5: Why did electric buses lose to gasoline buses in the 1910s-20s?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(f.value, '$.name')       AS name,
       json_extract(f.value, '$.period')     AS period,
       json_extract(f.value, '$.why_failed') AS why_failed
FROM entries e, json_each(json_extract(e.data, '$.failed_alternatives')) f
WHERE json_extract(f.value, '$.name') LIKE '%batter%'
   OR json_extract(f.value, '$.name') LIKE '%electric%';
```

**Raw results:**
```
bus:trolleybus | Battery streetcars / battery buses (early 20th century) | 1900–1920
  "Electric buses with on-board lead-acid batteries were tried in the 1900s–1910s but
   the energy density was far too low... The trolleybus won by leaving the batteries
   on the grid. Battery-electric buses only become viable a century later."
   sources: [] (still empty in v2)

bus:battery_electric_modern | Early-20th-century battery streetcars and battery buses | 1905
  "Lead-acid battery buses operated briefly in cities like New York and London in the
   1900s–1910s but lost decisively to ICE buses on energy density."
   sources: [] (still empty in v2)

bus:motorized_diesel | London Electrobus Company battery-electric buses (1907–1909) | 1907–1910 ← v2 NEW
  "Eight units were sold to Brighton, Hove and Preston United where they ran reliably
   for ten years — but the model could not scale: lead-acid energy density was too low,
   battery swaps too operationally heavy, and the diesel engine that arrived a decade
   and a half later closed the energy-density gap from the propulsion side rather than
   the chemistry side."
   sources: 2 (Wikipedia London Electrobus Company)
```

**Atlas-grounded answer:**
The atlas frames this question two ways, both of which the question's note anticipates. **v2 adds a third, much more sourced, frame.**

**Frame 1: Battery-electric buses lost on energy density (legacy entries, still without inline sources).** From the trolleybus entry: *"Electric buses with on-board lead-acid batteries were tried in the 1900s–1910s but the energy density was far too low: vehicles were heavy, ranges short, and battery swaps onerous. The trolleybus won by leaving the batteries on the grid. Battery-electric buses only become viable a century later, with lithium chemistry."* The modern battery-electric bus entry corroborates: *"Lead-acid battery buses operated briefly in cities like New York and London in the 1900s–1910s but lost decisively to ICE buses on energy density."* (**Both elements still have `sources: []` in v2 — not backfilled.**)

**Frame 2: Trolleybuses (overhead-wire electric) did *not* lose in the 1910s–20s.** Per trolleybuses.org (https://trolleybuses.org/history/): *"At the peak of their operation in the early 1950s, trolleybuses represented about 10 percent of the transit activity in the United States, with more than 6500 units in operation."*

**Frame 3 (v2 NEW): Concrete case study, the London Electrobus Company, with two inline sources.** The new diesel entry's `failed_alternatives` array contains a London Electrobus Company entry with verbatim citations. Per Wikipedia (https://en.wikipedia.org/wiki/London_Electrobus_Company): *"The company, which was first registered in April 1906, started running a service of electrobuses between London's Victoria Station and Liverpool Street on 15 July 1907."* And: *"By 3 January 1910 the electrobus service had ceased and the company went into liquidation amid accusations of fraud."* The diesel entry adds the framing: *"Eight units were sold to Brighton, Hove and Preston United where they ran reliably for ten years — but the model could not scale... A reminder that battery-electric buses had a serious 1900s prototype run that failed precisely because diesel was about to win."*

**Synthesis:** in the 1910s–20s, the loss is specifically *battery* electric vs. ICE (energy-density failure of lead-acid). The London Electrobus case study (v2) gives the answer a concrete, dated, sourced exemplar that v1 could only describe in the abstract. The *wired* electric (trolleybus) did not lose then and continued to be a serious competitor for decades — though the new diesel entry now makes clear that diesel's postwar cost advantage is what *eventually* killed Western trolleybus networks (1950s+).

**Coverage assessment:** **partial → improved**. Frame 3 (London Electrobus) is a major addition; the legacy `failed_alternatives` elements on trolleybus and battery-electric-modern still need source backfill.

---

## Q6: What was the "jitney war" and how did it reshape transit regulation in the US?

**SQL:**
```sql
SELECT json_extract(r.value, '$.year')         AS year,
       json_extract(r.value, '$.jurisdiction') AS jurisdiction,
       json_extract(r.value, '$.description')  AS description,
       json_extract(r.value, '$.effect')       AS effect
FROM entries e, json_each(json_extract(e.data, '$.regulatory_moments')) r
WHERE e.id = 'standalone:jitney_movement'
ORDER BY year;
```

**Raw results (unchanged from v1):**
```
1915 | Salt Lake City, Utah | restricting | Fleet 40→2 in 4 days
1915 | 27 US municipalities | restricting | $10k liability bonds
1916 | San Francisco        | restricting | 700-driver cap; banned Market St 10:30am–4pm
```

**Atlas-grounded answer:** (unchanged from v1)
The jitney movement has its own dedicated standalone entry. Per Reason (https://reason.com/1972/02/01/taxis-and-jitneys/): *"The jitney movement began in late 1914 in Los Angeles, when enterprising Model T owners discovered they could offer seats in their private cars for the same fare as a trolley: a nickel, or 'jitney.' The first documented jitney operation began on July 1, 1914, when driver L.P. Draper used his Ford Model T to transport a passenger for five cents. By March 1915, thousands of jitneys operated in the southern and western United States."*

The "war" was a coordinated regulatory rollback, with three concrete instruments:

1. **Liability bonds.** Per Rollins (https://files01.core.ac.uk/download/pdf/235715894.pdf): *"By July 1915, twenty-seven municipalities had already imposed burdensome liability costs to all jitney drivers. Drivers were compelled to post up to $10,000 in liability insurance, biting into 25 to 50 percent of drivers' annual earnings."*
2. **License restrictions.** Per slchistory.org (https://www.slchistory.org/2020/02/jitneys-early-automobile-ridesharing.html): *"For example, in Salt Lake City, a new city ordinance went into effect on April 1, 1915, and by April 4 nearly all of the SLC Jitney operators surrendered their licenses leaving only 2 Jitney busses in operation out of a previous fleet of nearly 40."*
3. **Route and time-of-day bans.** Per slchistory.org: *"The Jitney Bus Ordinance passed in August 1916 in San Francisco limited the number of jitney drivers to 700 and forbade jitneys on Market Street from Fremont to 6th Street between the hours of 10:30 a.m. and 4 p.m."*

**Outcome.** Per Rollins: *"By 1918, more than 90% of the jitney services that opened in 1915 had ceased operations."*

**Coverage assessment:** complete and well-sourced (unchanged from v1). This entry remains a model for what a fully-populated standalone looks like.

---

## Q7: How did buses interact with the streetcar industry — competition, replacement, regulatory capture?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(p.value, '$.name')         AS name,
       json_extract(p.value, '$.relationship') AS relationship,
       json_extract(p.value, '$.brief')        AS brief
FROM entries e, json_each(json_extract(e.data, '$.predecessors')) p
WHERE json_extract(p.value, '$.name') LIKE '%streetcar%'
   OR json_extract(p.value, '$.name') LIKE '%tram%'
   OR json_extract(p.value, '$.name') LIKE '%trolley%';
-- Also scan funders / regulatory_moments / descriptions in the diesel entry.
```

**Raw results:**
```
standalone:jitney_movement → predecessor "Streetcar (electric tram)" (competing_predecessor, 1888)
bus:trolleybus            → predecessor "Electric tram (Siemens 1881, Lichterfelde)" (evolved_from)
bus:battery_electric_modern → predecessor "Trolleybus" (competing_predecessor, 1882)

bus:motorized_diesel — funder STCRP/RATP (1924–1960s):  ← v2 NEW (substantive on streetcar replacement)
  "À partir de 1930, sous l'effet des pressions politiques, la STCRP supprime
   rapidement les lignes de tramway et les remplace par des lignes d'autobus."

bus:motorized_diesel — geographic_diffusion Paris 1930 (10pct):  ← v2 NEW
  "From 1930, under political pressure, Paris's STCRP began rapidly suppressing
   tramway lines and replacing them with bus lines — Renault diesel chassis were
   the dominant procurement."

bus:motorized_diesel — predecessor "Trolleybus" (competing_predecessor, 1882):  ← v2 NEW
  "the diesel bus's postwar cost advantage (no overhead infrastructure, no per-route
   capex) is what triggered the Western dismantling of trolleybus networks from the
   early 1950s onward."
```

**Atlas-grounded answer:**
**v2 substantially improves coverage** of the bus-vs-streetcar story by adding two of the three sub-questions through the new diesel entry.

**Competition / regulatory capture (jitney era).** Per the jitney entry: *"The five-cent streetcar fare set the price point that jitneys imitated. Streetcar companies were the chief lobbyists behind the anti-jitney ordinances."* And from the motorized gasoline bus entry's `failed_alternatives` for the jitney: *"Killed within four years by combinations of liability insurance requirements, route restrictions, and operating-time limits sponsored by streetcar companies and supportive municipalities."*

**Replacement (trolleybus side).** Per the trolleybus entry's `evolved_from` predecessor: *"Siemens's 1881 Lichterfelde tram, then the Paris Electric Exposition tram with overhead lines, are direct technological parents of the trolleybus. Removing the rails (and the rail-vehicle franchise) was the trolleybus's main innovation."*

**Direct motorbus replacement of streetcars (v2 NEW — was missing in v1).** The diesel entry now documents this directly. Per French Wikipedia, cited in the diesel entry's STCRP funder element (https://fr.wikipedia.org/wiki/R%C3%A9seau_de_bus_RATP): *"À partir de 1924, la STCRP abandonne le constructeur Somua au profit de Renault et de ses petits autobus KX1 pour 25 voyageurs. À partir de 1930, sous l'effet des pressions politiques, la STCRP supprime rapidement les lignes de tramway et les remplace par des lignes d'autobus."* The diesel entry's framing adds: *"The case is a clean example of municipal-government capital driving the diesel-bus replacement of streetcars in a major Western European city."* And the diesel-vs-trolleybus story: *"the diesel bus's postwar cost advantage (no overhead infrastructure, no per-route capex) is what triggered the Western dismantling of trolleybus networks from the early 1950s onward. The Soviet bloc kept its trolleybus systems precisely because diesel fuel had to be imported while electricity was domestic."*

What's still missing: a US-specific narrative. The atlas does not document the 1930s–50s US streetcar dismantling (no NCL/General Motors conspiracy or Great American Streetcar Scandal entry). Paris is now covered; US cities are not.

**Coverage assessment:** **partial → improved**. Paris streetcar replacement is now well-sourced. US streetcar replacement narrative still missing. v1 called this gap out specifically; the diesel addition closes ~half of it.

---

## Q8: Who were the key engineers behind the modern bus, beyond the headline inventors?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(i.value, '$.name')               AS name,
       json_extract(i.value, '$.role')               AS role,
       json_extract(i.value, '$.country')            AS country,
       json_extract(i.value, '$.year')               AS year,
       json_extract(i.value, '$.recognition_status') AS recognition
FROM entries e, json_each(json_extract(e.data, '$.innovators')) i
WHERE json_extract(i.value, '$.recognition_status') IN ('underrecognized', 'obscure')
ORDER BY year;
```

**Raw results:**
```
v1 list (still present):
1662 | Blaise Pascal             | underrecognized | France
1826 | Monsieur Omnès            | obscure         | France
1862 | Alphonse Beau de Rochas   | underrecognized | France
1846 | Robert William Thomson    | underrecognized | UK (Scotland)
1895 | Netphener Omnibusgesellschaft | underrecognized | Germany
1914 | L.P. Draper               | obscure         | USA
2010 | Proterra (Dale Hill, Jeff Granato) | underrecognized | USA
2010 | Foothill Transit          | underrecognized | USA

v2 NEW (from bus:motorized_diesel):
1893 | Heinrich von Buz / Maschinenfabrik Augsburg | underrecognized | Germany
1893 | Krupp                                        | underrecognized | Germany
1923 | Benz & Cie. (Mannheim diesel team)           | underrecognized | Germany
1926 | MAN (Maschinenfabrik Augsburg-Nürnberg)      | underrecognized | Germany
```

**Atlas-grounded answer:**
The v1 list of 8 underrecognized/obscure innovators is preserved. **v2 adds 4 more, all on the diesel side**, materially closing one of v1's specifically-flagged gaps.

* **Heinrich von Buz / Maschinenfabrik Augsburg (Germany, 1893) — `underrecognized`.** Per Wikipedia (https://en.wikipedia.org/wiki/Rudolf_Diesel): *"From 1893 to 1897, Heinrich von Buz, director of Maschinenfabrik Augsburg in Augsburg, provided Rudolf Diesel the opportunity to test and develop his ideas. The first functional engine prototype (150mm bore and a 400mm stroke, producing 25 hp) was built at Maschinenfabrik-Augsburg AG (MAN) plant in July 1893 and started on August 10, 1893."* Diesel engine atlas annotation: *"Without Augsburg's industrial backing the engine would not have left the patent office."*
* **Krupp (Germany, 1893) — `underrecognized`.** Per Wikipedia (https://en.wikipedia.org/wiki/Diesel_engine): *"In April 1893, Diesel and Krupp signed a contract that allows Diesel to build a prototype engine, and both Krupp and the Maschinenfabrik Augsburg decided to collaborate and build a single prototype in Augsburg."*
* **Benz & Cie. Mannheim diesel team (Germany, 1923) — `underrecognized`.** Per daimlertruck.com (https://www.daimlertruck.com/en/newsroom/pressrelease/the-worlds-first-ever-diesel-trucks-from-benz-and-daimler-in-1923-50057802): *"In 1923, Benz & Cie. presented the first diesel truck to the world, driven by a four-cylinder diesel OB 2 engine with an output of 33 kW (45 hp) at 1000 rpm."* Atlas annotation: *"The pre-chamber design — small antechamber that initiated combustion before the main charge — was the breakthrough that made the diesel viable in a road vehicle."*
* **MAN / Maschinenfabrik Augsburg-Nürnberg (Germany, 1926) — `underrecognized`.** Per trans.info: *"The MAN type NOB omnibus was offered commencing in 1924, and starting in 1926 it was also offered with a 65 HP four-cylinder diesel engine."* (First commercially-offered diesel bus chassis.)

What v1 specifically flagged as missing is now partly addressed: v2 names 20th-century industrial-engineering organisations (MAN, Benz & Cie diesel team) and identifies Heinrich von Buz as the under-credited industrial sponsor. Yellow Coach / GM's Detroit Diesel team is also named (rated `well_known`, so doesn't show in this filter — but is in the diesel entry). What's still missing: individual chassis/coachbuilder engineers (no AEC, Leyland, ACF, Yellow Coach individuals named by name; companies are named).

**Coverage assessment:** **partial → improved from v1's "complete (for the recognition_status field) but missing chassis engineers"**. v2 fills in the diesel-engine industrial story specifically; chassis/coachbuilder engineer gap remains.

---

## Q9: Compare bus diffusion in the US vs. UK vs. Germany, 1900-1940.

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(g.value, '$.place')     AS place,
       json_extract(g.value, '$.year')      AS year,
       json_extract(g.value, '$.milestone') AS milestone,
       json_extract(g.value, '$.brief')     AS brief
FROM entries e, json_each(json_extract(e.data, '$.geographic_diffusion')) g
WHERE CAST(json_extract(g.value, '$.year') AS INTEGER) BETWEEN 1900 AND 1940
ORDER BY year;
```

**Raw results:**
```
1911 | London, United Kingdom               | saturation | bus:motorized_gasoline
1915 | Western and southern United States   | 10pct      | standalone:jitney_movement
1923 | Berlin (Marienfelde + IAA), Germany  | first      | bus:motorized_diesel  ← v2 NEW
1928 | Germany (national)                   | 1pct       | bus:motorized_diesel  ← v2 NEW
1930 | Paris, France (STCRP/RATP)           | 10pct      | bus:motorized_diesel  ← v2 NEW
1938 | United States (national)             | first      | bus:motorized_diesel  ← v2 NEW
```

**Atlas-grounded answer:**
The 1900–1940 window now has **six** datapoints (vs. two in v1), with all four of the new ones from the diesel entry.

* **UK — London, 1911 (saturation, gasoline bus):** *"London's last horse omnibus is withdrawn..."* (No inline source URL; gap remains.)
* **US — western/southern US, 1915 (10pct, jitney):** Per Reason: *"By March 1915, thousands of jitneys operated in the southern and western United States."*
* **Germany — Berlin, 1923 (first, diesel):** Per Wikipedia (https://en.wikipedia.org/wiki/Bus_transport_in_Berlin): *"The first Daimler 5C commercial diesel vehicles produced in Marienfelde – a truck, a three-sided tipper and a bus – were presented at the beginning of October 1923 at the Berlin automobile exhibition."*
* **Germany — national, 1928 (1pct, diesel):** Per trans.info: *"In 1928, Daimler-Benz produced a series-production bus with diesel engine."*
* **France — Paris, 1930 (10pct, diesel):** Per French Wikipedia: *"À partir de 1930, sous l'effet des pressions politiques, la STCRP supprime rapidement les lignes de tramway et les remplace par des lignes d'autobus."*
* **US — national, 1938 (first, diesel):** Per Wikipedia (https://en.wikipedia.org/wiki/Yellow_Coach_Manufacturing_Company): *"Some 400 units were built in 1938, with GM's very advanced Yellow Coach Model 719 being the primary recipient. Its rear-mounted 6-71 DD made 165 hp—also available in GM's transit buses—making it the first truly competitive diesel coach."*

**Comparison across the three countries (atlas-grounded):**

* **UK:** earliest motorbus saturation in the atlas (London 1911); v1 already covered. No diesel datapoint in this window.
* **Germany:** richest period coverage in v2 (1923 Berlin first diesel showing → 1928 national 1pct). The German pioneer status (1895) is contiguous with the new diesel-era data; Germany is the only country with both a "first" (1895 motorbus) and a "first" + "1pct" (1923, 1928 diesel) within the atlas's 1900–1940 window.
* **US:** jitney 1915 (atypical adoption pattern — owner-operators, killed by regulation); diesel transit arrives later (1938) than European diesel transit (1923–28).

A defensible *atlas-grounded* comparison: **Germany was first on both gasoline (1895) and diesel (1923) — a 28-year German lead on diesel propulsion that the US closed only in 1938.** This was not visible in v1 because diesel had no entry.

**Coverage assessment:** **sparse → partial**. Six datapoints across three countries and 40 years still doesn't support quantitative diffusion-rate comparison, but is now adequate for *qualitative* country-by-country sequencing. A real improvement.

---

## Q10: Who funded the early bus industry, how did that shape it?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(f.value, '$.entity') AS entity,
       json_extract(f.value, '$.type')   AS type,
       json_extract(f.value, '$.period') AS period,
       json_extract(f.value, '$.brief')  AS brief
FROM entries e, json_each(json_extract(e.data, '$.funders')) f
ORDER BY period;
```

**Raw results (early-bus + diesel additions):**
```
v1 funders (still present): horse omnibus (royal/private), motorized gasoline (private),
trolleybus (private/government/Soviet state), jitney (owner-operator), BRT (municipal),
battery-electric modern (China NEV / US FTA Low-No).

v2 NEW from bus:motorized_diesel:
- Krupp + Maschinenfabrik Augsburg consortium (private, 1893–1897)
- Daimler-Benz / Benz & Cie internal R&D (private, 1922–1928)
- Société des Transports en Commun de la Région Parisienne (STCRP) / RATP (government, 1924–1960s)
- US municipal transit authorities + Federal Urban Mass Transportation Act of 1964 (government, 1948–2010)
- Marshall Plan / European Recovery Programme (government, 1948–1952)
```

**Atlas-grounded answer:**
The v1 picture is preserved, and v2 adds five new diesel-era funder entries that materially extend the funding-history narrative into the 20th century.

**v1 picture (unchanged):** horse omnibus funded by mixed royal/private (Pascal had Louis XIV / Duc de Roannez); Baudry self-funded from a mill business. Motorbus 1895 was purely private and bottom-up (Netphen line filled a gap left by the Royal Prussian Postal Service). Trolleybus moved from corporate demonstration (Siemens 1882) to municipal capex (1930s–50s) to Soviet-state strategic capex (1933–91). Jitney was owner-operator capital. Modern battery-electric is government-led (China NEV, US FTA Low-No).

**v2 NEW — diesel funder pattern:** unique among the variants in being a **theory→prototype industrial consortium** (Krupp + Maschinenfabrik Augsburg jointly funded the 1893 prototype before any bus existed) followed by **corporate R&D** (Daimler-Benz internal budget for OB 2 and N 56, 1922–28) and then **municipal/national capex** (STCRP/RATP from 1924, US transit agencies + 1964 UMTA grants from 1948). Per the diesel entry: *"Industrial-consortium funding of the upstream technology, before any bus exists, is the funding pattern that distinguishes the diesel bus from the gasoline bus (which had Benz's car business as the parent)."*

**Marshall Plan addition (v2):** per the diesel entry funder element: *"Although the Marshall Plan did not target transit fleets specifically, the European Recovery Programme funded reconstruction of national transport networks in West Germany, France, Italy and the UK during the 1948–52 window — the same years European cities were re-equipping their war-damaged bus fleets. Italian provinces, for example, applied an average of 52% of their Marshall Plan grants to transportation infrastructure."* (Note: this funder element has `sources: []` — quantitative claim about Italian provinces is uncited; verification gap.)

**Cross-variant pattern (preserved from v1):** funder type predicts regulatory survival. Capital-heavy government-funded modes survive permitting fights; capital-light owner-operator modes are killed by insurance mandates. The diesel addition adds a third pattern: **theory→prototype industrial consortium** (a propulsion-technology funding pattern, distinct from operating-company funding), enabled when the propulsion technology has parallel non-bus markets (trucks, marine, locomotive) that justify the up-front R&D.

**Coverage assessment:** **complete → improved**. Was already well-covered in v1; v2 adds 5 new funder entries and a distinctive funding pattern (theory→prototype consortium) that wasn't visible before. One v2 element (Marshall Plan) has `sources: []` despite making a verifiable quantitative claim — minor gap.

---

## Q11: What's the lag between the invention of the internal combustion engine and the first motorized gasoline bus?

**SQL:**
```sql
SELECT e.id,
       json_extract(k.value, '$.year')       AS year,
       json_extract(k.value, '$.event')      AS event,
       json_extract(k.value, '$.event_type') AS type
FROM entries e, json_each(json_extract(e.data, '$.key_dates')) k
WHERE e.id IN ('component:internal_combustion_engine', 'bus:motorized_gasoline', 'bus:motorized_diesel')
  AND json_extract(k.value, '$.event_type') IN ('invention', 'patent')
ORDER BY year;
```

**Raw results (gasoline path unchanged; diesel path NEW in v2):**
```
1862 | Beau de Rochas patents the four-stroke cycle as a concept.    | patent     | component:ICE
1876 | Otto builds the first working compressed-charge 4-stroke, 9 May. | invention | component:ICE
1877 | Otto granted German patent.                                    | patent     | component:ICE
1885 | Carl Benz builds the Patent-Motorwagen.                        | invention | bus:motorized_gasoline
1893 | Diesel patent + Krupp/Augsburg contract.                       | patent    | bus:motorized_diesel  ← v2 NEW
1895 | Netphener Omnibusgesellschaft opens, 18 March.                 | invention | bus:motorized_gasoline
1897 | Diesel Motor 250/400 successfully tested at MAN Augsburg, 17 Feb. | invention | bus:motorized_diesel  ← v2 NEW
1923 | Benz OB 2 first commercial diesel road vehicle.                | invention | bus:motorized_diesel  ← v2 NEW
1926 | MAN type NOB diesel bus chassis offered commercially.          | invention | bus:motorized_diesel  ← v2 NEW
```

**Atlas-grounded answer:**

**Gasoline path (computed lags, unchanged from v1):**

* **Otto's working engine (1876) → first motorbus (1895): 19 years.** Per Wikipedia (https://en.wikipedia.org/wiki/Nicolaus_Otto): *"After 14 years of research and development, Otto succeeded in creating the compressed charge internal combustion engine on May 9, 1876."* Per Urban Transport Magazine: *"On 18 March 1895, the world's first public transport line operated by a motorised bus rather than a stagecoach was opened."*
* **Beau de Rochas concept patent (1862) → first motorbus (1895): 33 years.**
* **Benz Patent-Motorwagen (1885) → motorbus (1895): 10 years.**

**Diesel path (computed lags, v2 NEW):**

* **Diesel patent (1893) → first commercial diesel bus chassis (MAN NOB, 1926): 33 years.** Per Wikipedia (https://en.wikipedia.org/wiki/Rudolf_Diesel): *"On February 23, 1893, German engineer Rudolf Diesel was granted a patent by the Imperial Patent Office in Berlin for 'working methods and design for internal combustion engines.'"* Per trans.info: *"The MAN type NOB omnibus was offered commencing in 1924, and starting in 1926 it was also offered with a 65 HP four-cylinder diesel engine."*
* **Diesel working engine (1897) → first commercial diesel bus chassis (1926): 29 years.** Per Wikipedia: *"A successful test on February 17, 1897, showed Diesel's engine had an efficiency of 26.2 percent."*
* **Diesel working engine (1897) → first series-production diesel bus (Daimler N 56, 1928): 31 years.**
* **Benz OB 2 first commercial diesel road vehicle (1923) → first commercial diesel bus (1926): 3 years.** This is the diesel-bus parallel to the gasoline-engine "car-to-bus 10-year lag" — *truck* arrived in commerce 1923, *bus* arrived in commerce 1926. Faster diffusion than the gasoline path because the engine was already in road service.

**Synthesis:** the diesel propulsion took noticeably *longer* to get from working engine to first commercial bus (29 years for diesel vs. 19 years for gasoline). But once diesel reached *commercial road service* (in trucks, 1923), the road-vehicle-to-bus lag was much *shorter* (3 years vs. 10 for gasoline car-to-bus). This is a structural insight v1 could not access — the diesel addition makes the gasoline-vs-diesel lag comparison computable for the first time.

**Coverage assessment:** **complete → enriched**. Both engines now have invention dates AND first-bus dates AND first-commercial-road-vehicle dates, making cross-propulsion lag analysis tractable.

---

## Q12: What's the lag between bus invention and various levels of adoption (first → 1pct → 10pct → saturation)?

**SQL:**
```sql
SELECT e.id, e.name,
       json_extract(g.value, '$.year')      AS year,
       json_extract(g.value, '$.milestone') AS milestone,
       json_extract(g.value, '$.place')     AS place
FROM entries e, json_each(json_extract(e.data, '$.geographic_diffusion')) g
ORDER BY e.id, year;
```

**Raw results (v2 — diesel adds three new milestones):**
```
bus:motorized_gasoline      | 1895 first → 1911 saturation                              | 16-year lag, no 1pct/10pct
bus:horse_omnibus           | 1662 first → 1826 first → 1829 first                      | three "first" entries
bus:trolleybus              | 1882 first → 1952 10pct (US) → 2024 saturation (CEE)      | 70 years to 10pct
bus:battery_electric_modern | 2010 first (Shenzhen + Pomona) → 2017 saturation (Shenzhen) | 7-year lag
standalone:bus_rapid_transit| 1974 first (Curitiba) → 2014 saturation (Curitiba)        | 40-year lag
standalone:jitney_movement  | 1914 first (LA) → 1915 10pct (US south/west)              | 1-year lag
bus:motorized_diesel        | 1923 first (Berlin) → 1928 1pct (Germany) → 1930 10pct (Paris) ← v2 NEW
                            | → 1938 first (US) → 1969 saturation (Western Europe + N. America)
                            | → 2018 saturation (Madrid/Paris/London — bookend)
```

**Atlas-grounded answer:**
**v2 dramatically improves milestone coverage**, especially the formerly-empty `1pct` and `10pct` brackets.

* **Motorbus (gasoline ICE):** first 1895 → saturation 1911 = 16 years (unchanged).
* **Trolleybus:** first 1882 → US 10pct ~1952 = 70 years to 10pct (unchanged).
* **Jitney:** first 1914 → 10pct 1915 = 1 year (unchanged).
* **BRT:** first 1974 → Curitiba saturation 2014 = 40 years within one city (unchanged).
* **Battery-electric:** first 2010 → Shenzhen saturation 2017 = 7 years for one city (unchanged).
* **Diesel bus (v2 NEW):** first 1923 (Berlin) → **1pct 1928 (Germany national) = 5 years** → **10pct 1930 (Paris) = 7 years** → first US 1938 = 15 years to cross the Atlantic → saturation Western Europe + N. America 1969 = **46 years to saturation** → bookend (urban diesel bans, Madrid/Paris/London) 2018 = 95 years from first to phase-out signal.
* **Horse omnibus:** atlas only records "first" milestones in three cities; no saturation date globally. (The motorized bus's 1911 London saturation can be read as the implicit displacement point, but is not coded.)

The **previously-systematic underuse** of the `1pct` and `10pct` enums is now partly addressed: the diesel entry contributes one `1pct` (Germany 1928) and one `10pct` (Paris 1930) — the only `1pct` in the entire atlas. Trolleybus already had a `10pct` (US 1952); jitney has a `10pct` (US south/west 1915). Across **7 entries with diffusion data, the atlas now has 1 `1pct` and 3 `10pct` datapoints** (vs. v1's 0 `1pct` and 2 `10pct`).

**Coverage assessment:** **partial → improved**. The `1pct`/`10pct` middle-of-curve milestones are still underused but no longer empty. The diesel entry is the model the other variants should follow.

---

## Q13: What components and practices enabled buses to scale?

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(c.value, '$.name') AS component,
       json_extract(c.value, '$.type') AS type,
       json_extract(c.value, '$.role') AS role
FROM entries e, json_each(json_extract(e.data, '$.enabling_components')) c
ORDER BY e.id, type;
```

**Raw results (v1 totals + diesel additions):**

v1 covered ~22 distinct components across 6 entries. v2 adds **6 more** from the diesel entry:

```
v2 NEW (bus:motorized_diesel):
technology:    Compression-ignition diesel engine (linked to component:ICE)
technology:    Pre-chamber (indirect) fuel injection (Benz 1922–23)
technology:    High-pressure mechanical fuel injection pump (Bosch, productionised 1927)
infrastructure: Diesel fuel distribution network (middle-distillate refining)
standard:      Ultra-low-sulfur diesel (ULSD)         ← first standard-typed enabler in atlas
standard:      VöV-Standard-Bus (German unified design spec)  ← second
```

**Atlas-grounded answer:**
The atlas now distinguishes four populated classes of enabler (was three in v1; **`standard` was empty**). v2 fills in the `standard` enum with two examples.

**Recurring technologies across variants (unchanged from v1):**
* **Pneumatic tire** — listed as enabler for gasoline bus, trolleybus, implicitly battery-electric.
* **Internal combustion engine / electric traction motor** — variant-specific.

**v2 NEW recurring patterns visible only with diesel:**

* **Bosch high-pressure injection pump (technology, 1927).** Per the diesel entry: *"Robert Bosch's in-line PE injection pump, productionised from 1927, made compression-ignition engines mass-producible: it metered fuel into each cylinder at hundreds of bars of pressure with timing matched to the crank, replacing the cumbersome air-blast injection of the Diesel original. Every commercial diesel bus from the late 1920s onward used a Bosch (or Bosch-licensee) injection pump."* (Note: this element has `sources: []` — uncited.)
* **Diesel fuel distribution network (infrastructure).** Per the diesel entry: *"Diesel buses share a fuel chemistry with trucks, ships, locomotives and heating oil — a much larger and more stable middle-distillate market than gasoline. Existing oil-company refineries and depots could supply transit garages without bespoke buildout, which was a major cost advantage over both petrol-only fleets and (electric) trolleybus substations."* (sources: empty.)
* **ULSD fuel (standard, 2006).** Per Wikipedia (https://en.wikipedia.org/wiki/Ultra-low-sulfur_diesel): *"Beginning in 2006, EPA began to phase-in more stringent regulations to lower the amount of sulfur in diesel fuel to 15 ppm... Since December 1, 2010, all highway diesel fuel nationwide has been ULSD."* The first `standard` enabler in the entire atlas.
* **VöV-Standard-Bus (standard, 1969).** Per Wikipedia (https://en.wikipedia.org/wiki/Mercedes-Benz_O305): *"It was built as either a complete bus or a bus chassis and was the Mercedes-Benz adaptation of the unified German VöV-Standard-Bus design, that was produced by some different bus manufacturers including Büssing, Magirus-Deutz, MAN, Ikarus, Gräf/Steyr, Heuliez, Renault, and Pegaso."*

**Cross-variant insight (refined from v1):** infrastructure and practice enablers tend to be the binding constraints on scaling. v2 adds a fifth category — **standards (fuel specs, vehicle dimension specs)** — which become binding at the *interoperability* moment, not the *deployment* moment. The VöV standard turned a single-manufacturer product (O 305) into an industry-wide template; the ULSD standard re-enabled diesel for another decade by allowing aftertreatment hardware.

**Coverage assessment:** **complete → enriched**. The `standard` enum was unused in v1; v2 populates it twice. The Bosch injection pump is a high-leverage missing source (uncited but central to the answer).

---

## Q14: Show me a timeline of the key innovations within buses (across variants and stubs).

**SQL:**
```sql
SELECT e.id,
       json_extract(k.value, '$.year')         AS year,
       json_extract(k.value, '$.event')        AS event,
       json_extract(k.value, '$.event_type')   AS event_type,
       json_extract(k.value, '$.significance') AS significance
FROM entries e, json_each(json_extract(e.data, '$.key_dates')) k
ORDER BY year;
```

**Raw results — full sorted list, v2 (diesel additions in **bold**):**

| Year | Entry | Event | Type |
|---|---|---|---|
| 1662 | bus | Pascal's carrosses à cinq sols open in Paris | invention |
| 1662 | bus:horse_omnibus | Pascal's carrosses open (18 Mar; 4th route 24 Jun) | invention |
| 1677 | bus:horse_omnibus | Pascal's carrosses cease operation | regulatory |
| 1826 | bus | Baudry begins horse-omnibus service in Nantes | invention |
| 1826 | bus:horse_omnibus | Baudry opens the Nantes omnibus, 30 Sep | invention |
| 1829 | bus | Shillibeer launches London's first omnibus service | adoption |
| 1829 | bus:horse_omnibus | Shillibeer launches the London omnibus, 4 Jul | adoption |
| 1862 | component:ICE | Beau de Rochas patents 4-stroke cycle | patent |
| 1876 | bus:motorized_gasoline | Otto demonstrates 4-stroke engine | invention |
| 1876 | component:ICE | Otto builds first working 4-stroke engine, 9 May | invention |
| 1877 | component:ICE | Otto granted German patent | patent |
| 1881 | bus:trolleybus | Siemens demonstrates first overhead-wire tram in Paris | invention |
| 1882 | bus | Siemens demonstrates Elektromote in Berlin | invention |
| 1882 | bus:trolleybus | Elektromote runs in Halensee (29 Apr – 13 Jun) | invention |
| 1885 | bus:motorized_gasoline | Benz builds Patent-Motorwagen | invention |
| 1888 | component:pneumatic_tire | Dunlop tests pneumatic tire (28 Feb), patents (7 Dec) | patent |
| **1893** | **bus:motorized_diesel** | **Diesel patent + Krupp/Augsburg contract** | **patent** |
| 1895 | bus | Netphener Omnibusgesellschaft opens first ICE bus line | invention |
| 1895 | bus:motorized_gasoline | Netphener opens world's first scheduled motorbus, 18 Mar | invention |
| **1897** | **bus:motorized_diesel** | **Diesel Motor 250/400 successfully tested at MAN Augsburg, 17 Feb. 25 hp, 26.2% efficiency.** | **invention** |
| 1914 | bus:motorized_gasoline | Jitney movement begins in LA | adoption |
| 1914 | standalone:jitney_movement | L.P. Draper carries first paying jitney passenger | invention |
| 1915 | standalone:jitney_movement | Anti-jitney ordinances spread to 27 cities by July | regulatory |
| 1918 | standalone:jitney_movement | >90% of 1915-era jitney services have ceased | regulatory |
| **1923** | **bus:motorized_diesel** | **Benz OB 2 first commercial diesel road vehicle; Daimler 5C bus shown at Berlin IAA, October.** | **invention** |
| **1926** | **bus:motorized_diesel** | **MAN type NOB omnibus offered with 65 hp diesel — first commercially-available diesel bus chassis.** | **invention** |
| **1928** | **bus:motorized_diesel** | **Daimler-Benz N 56 — first series-production diesel bus.** | **scaling** |
| 1937 | component:articulated_bus | First articulated bus appears in Milan | invention |
| 1938 | component:articulated_bus | Twin Coach builds first North American articulated bus (Baltimore) | invention |
| **1938** | **bus:motorized_diesel** | **Yellow Coach Model 719 enters production with rear-mounted Detroit Diesel 6-71 engine, 165 hp.** | **scaling** |
| 1952 | bus:trolleybus | Peak of US trolleybus operation (~10%, 6500 vehicles) | scaling |
| 1968 | standalone:bus_rapid_transit | Curitiba Master Plan adopted | regulatory |
| **1969** | **bus:motorized_diesel** | **Mercedes-Benz O 305 enters production at Mannheim — VöV-Standard-Bus.** | **adoption** |
| **1970** | **bus:motorized_diesel** | **US Clean Air Act amendments empower EPA to regulate diesel emissions; first standards 1974.** | **regulatory** |
| 1971 | standalone:bus_rapid_transit | Jaime Lerner becomes mayor of Curitiba | adoption |
| 1974 | bus | Curitiba opens world's first BRT corridor | invention |
| 1974 | standalone:bus_rapid_transit | First 20 km of Curitiba's RIT opens | invention |
| **1992** | **bus:motorized_diesel** | **Euro I heavy-duty emissions standards take effect across the EU.** | **regulatory** |
| **2006** | **bus:motorized_diesel** | **ULSD fuel rolled out in the US (CA 1 Sep, nationwide 15 Oct).** | **regulatory** |
| 2009 | bus:battery_electric_modern | BYD K9 prototypes begin testing in Shenzhen | invention |
| 2010 | bus | First commercial BEV services launch (BYD K9 + Proterra) | scaling |
| 2010 | bus:battery_electric_modern | Foothill Transit puts 3 Proterra EcoRide BE35 in service, 3 Sep | adoption |
| 2011 | bus:battery_electric_modern | BYD supplies 200 K9 buses to Shenzhen Universiade | scaling |
| 2017 | bus:battery_electric_modern | Shenzhen completes full conversion (~16,000 vehicles) | scaling |
| **2018** | **bus:motorized_diesel** | **Madrid creates 4.7 km² Madrid Central low-emissions zone; Paris/London ULEZ follow.** | **regulatory** |

**Atlas-grounded answer:**
The 33 dated events of v1 are now **45 events** (+12 from diesel). v2's diesel additions reshape the eras:

1. **Pre-mechanical bus era (1662–1829).** Unchanged.
2. **Component readiness (1862–1888).** Unchanged.
3. **First mechanized buses (1881–1895).** Unchanged.
4. **Diesel propulsion R&D (1893–1897). v2 NEW.** Diesel patent (1893) and working engine (1897) sit between Otto's working engine (1876) and the first motorbus (1895), giving the period a different texture: while gasoline was reaching the road, diesel was still in the laboratory.
5. **Jitney interlude (1914–1918).** Unchanged.
6. **Diesel bus emergence (1923–1938). v2 NEW.** A coherent 15-year arc — Berlin IAA showing 1923, MAN NOB option 1926, Daimler N 56 series production 1928, Yellow Coach Model 719 in the US 1938 — that v1's atlas could not present at all.
7. **Articulated bus form factor (1937–1938).** Unchanged.
8. **Postwar transit-bus form (1952–1974).** Trolleybus peak (1952) → Curitiba BRT (1974) → diesel saturation (1969 Western Europe + N. America). v2 makes the simultaneous trolleybus retreat and diesel ascendancy visible on the same axis.
9. **Modern emissions regulation (1970–2018). v2 NEW.** US CAA 1970, Euro I 1992, ULSD 2006, urban diesel bans 2018 — a 48-year regulatory arc that closes the diesel window.
10. **Modern transformations (2009–2017).** BRT 1974, battery-electric 2010, Shenzhen 2017.

The atlas's `event_type` enum surfaces the texture: in v2 the diesel entry alone contributes 5 `regulatory`, 4 `invention`, 2 `scaling`, 1 `adoption`, 1 `patent`. The 1970–2018 regulatory cluster is now the densest regulatory span in the atlas (was the 1914–18 jitney cluster in v1).

**Coverage assessment:** **complete → much richer**. The timeline gains a coherent diesel arc from 1893 to 2018, doubling its reach into the late 20th century.

---

## Synthesis

### What worked well

* **The diesel entry is a model of what a fully-populated variant looks like.** Substantial `description`, three `description_sources`, seven innovators (with sources on six of them), three predecessors, six enabling components (including the atlas's first two `standard`-typed enablers), three failed alternatives (with two sourced), five funders, six regulatory moments, six geographic diffusion datapoints (covering the previously-empty `1pct` and adding two `10pct`s), and 11 key dates. It alone closes several v1 gaps.
* **The Locomotive Acts source backfill (1865 + 1896) closes one of v1's most-flagged citation gaps.** The UK regulatory regime is now fully sourced.
* **Cross-entry timeline (Q14) is now substantially richer.** 33 → 45 events; the late-20th-century regulatory arc is finally legible.
* **Computational lag analysis (Q11) is now a comparison, not a single number.** Gasoline path (~19 years engine→bus) vs. diesel path (~29 years engine→bus, but only 3 years truck→bus once it reached commerce) is a real cross-propulsion insight that v1 could not surface.
* **The Paris streetcar replacement narrative (Q7) is now sourced** via the STCRP funder element on the diesel entry — closes ~half of a v1-flagged gap.

### What was sparse / had gaps

* **`sqlite3` is still blocked despite settings.json explicitly allowing it.** The most important meta-finding of this run. Worth investigating before running a third test.
* **Multiple new diesel-entry array elements have `sources: []`** despite making verifiable, citation-worthy claims. The most consequential:
  - **Bosch high-pressure injection pump** (Q13 enabling component) — central to the answer, no source.
  - **Diesel fuel distribution network** (Q13 enabling component) — central to the cost-advantage argument, no source.
  - **Heavy-fuel-oil hot-bulb / semi-diesel bus engines** (Q5 failed alternative) — no source.
  - **Madrid Central low-emissions zone 2018** (Q4 regulatory moment) — no source on a verifiable city-policy date.
  - **Marshall Plan funder element** (Q10) — makes a quantitative claim ("Italian provinces, for example, applied an average of 52% of their Marshall Plan grants to transportation infrastructure") with no source.
  - **EU Clean Vehicles Directive 2019/1161** (Q4 regulatory moment, also in modern battery-electric entry) — no source.
  - **US municipal transit authorities + 1964 UMTA** (Q10 funder) — no source.
  - **Daimler-Benz internal R&D** (Q10 funder) — no source.
* **Legacy `failed_alternatives` for 1900s battery buses (trolleybus + battery-electric-modern entries) still have `sources: []` in v2.** v1 flagged these; not backfilled. The new diesel entry's London Electrobus Company element (with sources) partly compensates, but the legacy elements remain uncited.
* **Steam-bus predecessor element on motorized_gasoline still has `sources: []`** even though the same entry's `failed_alternatives` for the steam omnibus IS sourced. The cross-array audit trail works but element-level audit does not.
* **US streetcar dismantling (1930s–50s, GM/NCL) still missing.** Paris is now covered (v2); US is not.
* **No individual chassis/coachbuilder engineers named** even in the new diesel entry. The diesel entry names *teams* and *companies* (Yellow Coach / Detroit Diesel team, Mannheim diesel team) but no individuals. The "Inventor of the Detroit Diesel 6-71" remains absent.
* **Horse-omnibus saturation milestone still not coded.** Implicit in the 1911 London motorbus saturation, but not present in the horse-omnibus entry's diffusion array.

### What surprised

* **Diesel was a 30-year laboratory project.** Patent 1893, working engine 1897, first commercial road vehicle 1923, first commercial bus 1926. The 30-year gap between Diesel's patent and the OB 2 truck is unusually long — much longer than the 9-year Otto-to-Patent-Motorwagen path or the 10-year Patent-Motorwagen-to-Netphen path. The diesel entry attributes this to architectural difficulty (air-blast injection didn't work for road vehicles; pre-chamber design and Bosch injection pump were both required).
* **Once diesel reached the road in trucks, it took only 3 years to reach buses.** Truck 1923 → bus 1926. This is faster than the gasoline car-to-bus path (10 years) — because the diesel road-vehicle infrastructure (depots, mechanics, fuel) was already being built for trucks.
* **Germany had a 28-year diesel lead on the US.** First diesel bus chassis available 1926 (MAN NOB) vs. 1938 (Yellow Coach Model 719). v1's atlas couldn't compute this.
* **The atlas's first `standard`-typed enablers (ULSD and VöV-Standard-Bus) are both diesel.** The `standard` enum was unused before v2. Both standards came late in the diesel arc (1969 and 2006) and both extended its life by another decade.
* **The diesel-bus story is shaped differently from the gasoline-bus story** in funding pattern: gasoline was a one-step extension of an existing car business (Benz & Cie); diesel was a multi-decade industrial-consortium investment (Krupp + Augsburg) in propulsion technology *before* any vehicle existed. The funder type "private (industrial consortium)" is structurally distinct from "private (operating company)" — a distinction the atlas could surface but doesn't yet have a separate enum value for.
* **The 1907–1910 London Electrobus Company is a sharper failure case than v1 surfaced.** A serious 1900s commercial battery-electric bus operation that *didn't* fail purely on technology (eight units ran in Brighton for ten years) but on capital structure (London company wound up amid fraud accusations). The framing in the diesel entry — "they failed precisely because diesel was about to win" — is an inverted version of the trolleybus framing.

### Comparison vs. v1 — coverage by question

| Q | Topic | v1 coverage | v2 coverage | Change |
|---|---|---|---|---|
| Q1 | Inventor of the motorbus | complete | complete | unchanged (diesel adds parallel) |
| Q2 | Predecessors | complete | complete | improved (Locomotive Acts source backfilled) |
| Q3 | 1900–1930 city adoption | sparse (1) | partial (4) | **improved** (+3 datapoints from diesel) |
| Q4 | Cross-country regulation | complete | complete | **improved** (UK sources backfilled; full late-20thC emissions sequence added) |
| Q5 | Why electric lost in 1910s–20s | partial | partial | **improved** (London Electrobus added with 2 sources; legacy elements still uncited) |
| Q6 | Jitney war | complete | complete | unchanged |
| Q7 | Bus vs. streetcar | partial | partial | **improved** (Paris STCRP narrative added; US still missing) |
| Q8 | Underrecognized engineers | partial | partial | **improved** (+4 diesel-side underrecognized entities) |
| Q9 | US/UK/Germany diffusion | sparse (2) | partial (6) | **improved** (Germany 1923/28 + Paris 1930 + US 1938 added) |
| Q10 | Funders | complete | complete | **improved** (+5 diesel funders, distinct theory→prototype consortium pattern) |
| Q11 | Engine→bus lag | complete | enriched | **improved** (now a gasoline-vs-diesel comparison; 3 new computational anchors) |
| Q12 | Diffusion milestones | partial | partial | **improved** (atlas's first `1pct`; +2 `10pct`s; new saturation point) |
| Q13 | Scaling components | complete | enriched | **improved** (atlas's first 2 `standard`-typed enablers; Bosch pump; ULSD) |
| Q14 | Innovation timeline | complete | much richer | **improved** (33 → 45 events; coherent diesel arc 1893–2018) |

**Summary:** 0 questions got worse. 12 of 14 improved. 2 unchanged (Q1, Q6 — both already complete). The diesel addition is a uniformly net-positive change.

### Updated suggested atlas extensions

Re-ranked with v2 changes accounted for:

1. **Inline source backfill on the new diesel entry's empty `sources: []` arrays** (Bosch injection pump, fuel distribution, hot-bulb engines, Madrid Central, Marshall Plan, EU 2019/1161, US municipal transit, Daimler-Benz internal R&D). This is the single highest-leverage immediate task — the diesel entry is otherwise excellent.
2. **Inline source backfill on the legacy battery-electric `failed_alternatives` elements** in trolleybus and battery-electric-modern. v1 flagged this; not addressed.
3. **City-level diffusion entries for the 1900–1940 *gasoline* window** (Berlin, New York, Chicago, individual UK cities). Diesel is now well-covered for this window; gasoline-bus diffusion across cities still has only London 1911.
4. **US streetcar industry standalone or `transit:streetcar` category** with a regulatory_moment for the 1930s–50s motorbus replacement (and the GM/NCL controversy). Paris is covered (v2); US is the remaining hole.
5. **Individual chassis/drivetrain engineers** for the 1900–1960 period (named individuals at AEC, Leyland, ACF, Yellow Coach, GM Truck & Coach, Detroit Diesel). The diesel entry names companies and teams but not individuals.
6. **`bus:hybrid_electric`** variant for the 1990s–2010s — currently appears only as a predecessor to the modern battery-electric bus.
7. **`component:diesel_engine`** stub — diesel currently lives only inside `bus:motorized_diesel`. A stub would let other entries (trucks, locomotives, ships) reference it cleanly the way they reference `component:internal_combustion_engine`.
8. **Saturation milestone for horse omnibus** globally (the 1911 London date is implicit but not coded into the horse-omnibus entry's diffusion array).
9. **Add a `private` subtype distinction** between operating-company funding and industrial-consortium funding. The diesel entry exposed a structurally distinct funding pattern that the existing `Funder.type` enum cannot capture.

### Eval-precursor signal

Strong candidates for formalization with what to measure, refined for v2:

* **Q11 (lag computation)** — measure: does the agent correctly compute *both* gasoline (~19y engine→bus) *and* diesel (~29y engine→bus, ~3y truck→bus) lags from atlas key_dates? Tests cross-propulsion arithmetic on an enriched v2-grade dataset. A v1-trained eval would only test the gasoline path.
* **Q5 (counterfactual framing)** — measure: does the agent (a) distinguish battery-electric vs. trolleybus vs. wired-electric framings; (b) cite the v2 London Electrobus Company case study; (c) flag that the legacy `failed_alternatives` elements have `sources: []`? Tests careful reading + epistemic restraint.
* **Q7 (bus-vs-streetcar)** — measure: does the agent surface the Paris STCRP regulatory-replacement story (now sourced) AND honestly note the US streetcar narrative is still missing? Strong test of "use what's there, flag what isn't."
* **Q12 (diffusion milestones)** — measure: does the agent correctly enumerate the (now non-empty but still sparse) `1pct`/`10pct` data and report the absence of others? Tests epistemic restraint when atlas has *partial* rather than zero coverage.
* **Q4 (regulatory)** — measure: does the agent reconstruct the four regulatory regimes (France/UK/Germany/US) AND the late-20th-century emissions sequence (US CAA 1970/90, EU Euro I 1992, ULSD 2006, urban bans 2018) AND correctly flag which regulatory moments still have empty sources? Tests breadth + audit-trail awareness.
* **Sqlite3-availability precondition** — measure: can the agent verify `sqlite3 data/atlas.db ".tables"` succeeds before answering, and surface a clear error if it fails? Currently the SKILL.md assumes sqlite3 works and the v2 run shows it does not. **This should be a hard eval gate, not just a recommendation.**

The Q3/Q9/Q12 trio (epistemic-honesty bundle) is still strong but slightly weakened by v2 because there's now more data to honestly report. The Q5/Q7/Q12 trio is a stronger v2 epistemic-honesty bundle because each of these has *partial* v2 coverage where the right answer is "here's what the atlas has, here's what it still doesn't, here's the cross-array source you should follow."

A **new candidate** for formalization specifically suited to v2:
* **Q1 + Q11 cross-propulsion test** — given the gasoline and diesel propulsion lineages now both fully present, measure whether the agent correctly draws the parallel (theorist + sponsor + manufacturer pattern: Beau de Rochas/Otto/Benz vs. Diesel/Augsburg/MAN). This tests whether the agent uses the atlas's structure to surface cross-entry patterns rather than just answering the question in front of it.
