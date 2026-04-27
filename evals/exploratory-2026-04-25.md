# Exploratory query test — 14 bus history questions

**Atlas state:** 10 entries — 1 `category` (`bus`), 4 `variant` (`bus:horse_omnibus`, `bus:motorized_gasoline`, `bus:trolleybus`, `bus:battery_electric_modern`), 2 `standalone` (`standalone:bus_rapid_transit`, `standalone:jitney_movement`), 3 `stub` (`component:internal_combustion_engine`, `component:pneumatic_tire`, `component:articulated_bus`). All entries are in domain `transit`.
**Tester:** Sub-agent run from /interview session (Drew Hoskins, founder)
**Date:** 2026-04-25
**Purpose:** Verify the atlas's coverage and the SKILL.md query patterns work end-to-end. Precursor to formal evals.

> **Methodological note.** The `sqlite3` CLI was blocked by the harness's Bash permissions during this run; the tester worked from the source-of-truth seed JSON files at `data/seeds/*.json` (per `docs/SCHEMA.md`: "Source-of-truth seeds at `data/seeds/*.json`. The DB is rebuilt from seeds via `scripts/build_db.py`."). The SQL shown for each question is the query that *would* have been run against `data/atlas.db`; the "Raw results" sections summarize what that query would return based on direct reads of the seeds. This is itself an eval signal — see Synthesis.

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

**Raw results (truncated):**
```
Nikolaus Otto | Inventor of four-stroke ICE (1876) | Germany | 1876 | well_known
Carl (Karl) Benz | Founder of Benz & Cie; manufacturer of the first motorbus chassis | Germany | 1895 | headline
Netphener Omnibusgesellschaft | First scheduled motorbus operator | Germany | 1895 | underrecognized
```

**Atlas-grounded answer:**
The atlas attributes the motorized (gasoline) bus to a **two-party event in Germany, 18 March 1895**: the manufacturer Carl Benz built the vehicles, the Netphener Omnibusgesellschaft operated the line. According to the Mercedes-Benz Public Archive (https://mercedes-benz-publicarchive.com/marsClassic/en/instance/ko/Benz-buses-1895--1898.xhtml?oid=16438713): *"The Benz Omnibus was the first internal combustion engine-powered omnibus in the world, built by Benz & Cie of automotive pioneer Carl Benz and had eight seats, including the driver's seat."* According to Urban Transport Magazine (https://www.urban-transport-magazine.com/en/130-years-of-motor-bus-service/): *"On 18 March 1895, the world's first public transport line operated by a motorised bus rather than a stagecoach was opened. The newly founded Netphener Omnibusgesellschaft opened the first ever bus route from Siegen via Netphen to Deuz."*

The atlas does not record a "priority dispute" over the bus itself, but it does surface a **priority dispute one layer down**, in the propulsion technology. According to Wikipedia (https://en.wikipedia.org/wiki/Nicolaus_Otto): *"Although Otto was the first to build an engine based upon this principle, the four-stroke cycle was patented in 1862 by the French engineer Alphonse Beau de Rochas, but it is commonly known as the Otto cycle."* The atlas notes Otto's 1877 patent was *"later partially invalidated due to Beau de Rochas's prior art, but commercial dominance was already established."* So the *bus* has clear priority (Benz/Netphen 1895, undisputed in the atlas); the *engine that made it possible* has the classic concept-vs-working-machine priority dispute.

**Coverage assessment:** complete (for the bus itself); rich (priority disputes exist but at the component layer, not the bus layer).

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
Horse-drawn omnibus    | evolved_from         | 1826 | linked: bus:horse_omnibus
Steam bus / steam carriage | competing_predecessor | 1830 | linked: null
Trolleybus (Elektromote)   | competing_predecessor | 1882 | linked: bus:trolleybus
```

**Atlas-grounded answer:**
The atlas records all three predecessors the question names, with explicit relationship typing:

* **Horse-drawn omnibus (1826) — `evolved_from`.** Per the motorized bus entry: *"The motorbus inherits the horse omnibus's route-and-timetable model wholesale; only the propulsion changes. In the 1890s and 1900s many cities ran horse and motor buses on the same routes side-by-side."* (no inline source)
* **Steam bus / steam carriage (1830) — `competing_predecessor`.** Per the motorized bus entry: *"Walter Hancock and Goldsworthy Gurney ran steam buses on British roads in the 1830s; the 1865 Locomotive Acts (the 'Red Flag Acts') effectively killed them by capping speeds at 4 mph and requiring a man with a flag to walk in front. They were a competing ancestor that lost to legal restriction long before the motorbus was technically possible."*
* **Trolleybus / Elektromote (1882) — `competing_predecessor`.** Per the motorized bus entry: *"Werner von Siemens's electric trolleybus prototype demonstrated electrified bus operation 13 years before the petrol bus. The two propulsion technologies competed for the next century."* The trolleybus has its own full entry — per Wikipedia (https://en.wikipedia.org/wiki/Electromote): *"The Electromote was the world's first vehicle run like a trolleybus, which was first presented to the public on April 29, 1882, by its inventor Dr. Ernst Werner von Siemens in Halensee, a suburb of Berlin, Germany."*

The horse omnibus itself has its own deep lineage in the atlas (Pascal 1662 → Baudry 1826 → Shillibeer 1829), with stagecoach (1640) listed as `evolved_from` and hackney coach (1620) as `competing_predecessor`.

**Coverage assessment:** complete.

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
bus:motorized_gasoline | London, United Kingdom | 1911 | saturation | London's last horse omnibus is withdrawn...
```

**Atlas-grounded answer:**
The atlas's `geographic_diffusion` arrays contain **one** entry between 1900 and 1930: London, 1911, `saturation`. According to the motorized gasoline bus entry (no inline source URL on this element): *"London's last horse omnibus is withdrawn. The motorbus has effectively replaced the horse on London streets within sixteen years of the Netphen experiment."*

Adjacent context the atlas does provide for this window, even though it doesn't sit in `geographic_diffusion`:

* The **jitney movement** populates the 1914–1918 US window. Per Reason (https://reason.com/1972/02/01/taxis-and-jitneys/): *"The first documented jitney operation began on July 1, 1914, when driver L.P. Draper used his Ford Model T to transport a passenger for five cents. By March 1915, thousands of jitneys operated in the southern and western United States."* The jitney entry's `geographic_diffusion` records Los Angeles 1914 (`first`) and "Western and southern United States" 1915 (`10pct`).
* The **anti-jitney regulatory wave** is dated 1915–1918 across multiple US municipalities (see Q6).

**Coverage assessment:** sparse. The 1900–1930 window is precisely when the motorbus diffused across major cities (Paris, Berlin, New York, etc.) and the atlas has only one city-level diffusion datapoint for it (London 1911 saturation). The jitney entry partly compensates for the US, but the European city-by-city rollout is missing.

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

**Raw results (truncated to early-bus window):**
```
1662 | Parlement of Paris (France)         | restricting | Bars commoners from carrosses
1826 | Municipality of Nantes (France)     | enabling    | First municipal bus license to Baudry
1865 | UK (Locomotive Act / 'Red Flag Act')| restricting | 4 mph cap, man with flag
1882 | Berlin (Halensee), Germany          | enabling    | Permission to operate Elektromote
1896 | UK (Locomotives on Highways Act)    | enabling    | Repealed Red Flag, opened UK to motorbuses
1915 | 27 US municipalities                | restricting | $10k liability bonds on jitneys
1915 | Salt Lake City, Utah                | restricting | Fleet 40→2 in 4 days
1916 | San Francisco                       | restricting | Jitney Bus Ordinance, 700-driver cap
1968 | Curitiba, Brazil                    | enabling    | Master Plan
2017 | Shenzhen, China                     | enabling    | Full-fleet electrification
2019 | European Union                      | enabling    | Clean Vehicles Directive 2019/1161
```

**Atlas-grounded answer:**
The atlas shows three sharply different regulatory regimes shaping early bus development:

* **France (enabling, route-licensed).** Per Wikipedia (https://en.wikipedia.org/wiki/Omnibus): *"The company appeared publicly on August 10, 1826, after obtaining permission from the municipality, and began operating on September 30, 1826."* The horse-omnibus entry adds the framing: *"The bus business is a regulated business from day one; route licensing is a recurring theme across the variants."* The much earlier 1662 Parlement of Paris ruling (restricting commoners from Pascal's carrosses) is the cautionary case of regulation killing a workable model.
* **United Kingdom (initially crippling, then liberating).** The 1865 Locomotive Act *"required self-propelled road vehicles to have a crew of three (one walking ahead with a red flag) and capped speeds at 4 mph in towns and 2 mph in the country. Effectively outlawed practical motor road transport in Britain for a generation."* The 1896 Locomotives on Highways Act *"repealed the Red Flag requirement and raised speed limits, opening the British market to motorbuses. Marked by the 'Emancipation Run' from London to Brighton."* The atlas does not provide an inline source URL on either UK entry — this is a coverage gap.
* **Germany (enabling, technology-tolerant).** Per Wikipedia (https://en.wikipedia.org/wiki/Electromote): *"The world's first trolleybus operated from April 29 to June 13, 1882, on a 540 m (591 yard) trail-track starting at Halensee railway station."* Berlin granted Siemens permission with no restrictive precondition.
* **United States (incumbent-protecting against new entrants).** The 1915–1916 anti-jitney ordinances are the most extensively documented regulatory moment in the atlas (see Q6). Per the Rollins paper (https://files01.core.ac.uk/download/pdf/235715894.pdf): *"By July 1915, twenty-seven municipalities had already imposed burdensome liability costs to all jitney drivers. Drivers were compelled to post up to $10,000 in liability insurance, biting into 25 to 50 percent of drivers' annual earnings."*

**Coverage assessment:** complete for the headline regimes (UK 1865/1896, France 1826, Germany 1882, US 1915–1916). Two UK regulatory moments lack inline source URLs.

---

## Q5: Why did electric buses lose to gasoline buses in the 1910s-20s?

**SQL:**
```sql
-- Failed alternatives mentioning batteries / electric, across all entries
SELECT e.id AS entry_id,
       json_extract(f.value, '$.name')       AS name,
       json_extract(f.value, '$.period')     AS period,
       json_extract(f.value, '$.why_failed') AS why_failed
FROM entries e, json_each(json_extract(e.data, '$.failed_alternatives')) f
WHERE json_extract(f.value, '$.name') LIKE '%batter%'
   OR json_extract(f.value, '$.name') LIKE '%electric%';

-- Plus the trolleybus entry's predecessors / failed_alternatives
SELECT * FROM entries WHERE id = 'bus:trolleybus';
```

**Raw results:**
```
bus:trolleybus | Battery streetcars / battery buses (early 20th century) | 1900–1920 |
  "Electric buses with on-board lead-acid batteries were tried in the 1900s–1910s but the
   energy density was far too low: vehicles were heavy, ranges short, and battery swaps
   onerous. The trolleybus won by leaving the batteries on the grid. Battery-electric buses
   only become viable a century later, with lithium chemistry."

bus:battery_electric_modern | Early-20th-century battery streetcars and battery buses | 1905 (predecessor):
  "Lead-acid battery buses operated briefly in cities like New York and London in the
   1900s–1910s but lost decisively to ICE buses on energy density. They remained the
   demonstration that batteries weren't ready, until they were."
```

**Atlas-grounded answer:**
The atlas frames this question two ways, both of which the question's note anticipates.

**Frame 1: Battery-electric buses lost on energy density.** From the trolleybus entry (no inline source URL on this `failed_alternatives` element): *"Electric buses with on-board lead-acid batteries were tried in the 1900s–1910s but the energy density was far too low: vehicles were heavy, ranges short, and battery swaps onerous. The trolleybus won by leaving the batteries on the grid. Battery-electric buses only become viable a century later, with lithium chemistry."* The modern battery-electric bus entry corroborates this as a `competing_predecessor`: *"Lead-acid battery buses operated briefly in cities like New York and London in the 1900s–1910s but lost decisively to ICE buses on energy density."*

**Frame 2: Trolleybuses (overhead-wire electric) did *not* lose in the 1910s–20s.** The atlas's trolleybus entry shows trolleybuses *grew* through this period and peaked in the early 1950s. Per trolleybuses.org (https://trolleybuses.org/history/): *"At the peak of their operation in the early 1950s, trolleybuses represented about 10 percent of the transit activity in the United States, with more than 6500 units in operation."* The trolleybus's defeat was a 1950s+ Western phenomenon (cheaper diesel, road-network expansion); the Eastern bloc kept them. The atlas description: *"Western Europe and North America largely dismantled their networks from the 1950s onward in favour of the cheaper-to-deploy diesel motorbus, but the Soviet Union and the rest of the socialist bloc continued investing."*

**Synthesis:** in the 1910s–20s, the loss is specifically *battery* electric vs. gasoline (energy-density failure of lead-acid). The *wired* electric (trolleybus) did not lose then and continued to be a serious competitor for decades.

**Coverage assessment:** complete on the framing; the lead-acid energy-density claim lacks an inline source URL on the failed-alternatives element (one of the weaker citation points).

---

## Q6: What was the "jitney war" and how did it reshape transit regulation in the US?

**SQL:**
```sql
SELECT data FROM entries WHERE id = 'standalone:jitney_movement';

SELECT json_extract(r.value, '$.year')         AS year,
       json_extract(r.value, '$.jurisdiction') AS jurisdiction,
       json_extract(r.value, '$.description')  AS description,
       json_extract(r.value, '$.effect')       AS effect
FROM entries e, json_each(json_extract(e.data, '$.regulatory_moments')) r
WHERE e.id = 'standalone:jitney_movement'
ORDER BY year;
```

**Raw results:**
```
1915 | Salt Lake City, Utah          | restricting | Fleet 40→2 in 4 days under 1 April ordinance
1915 | 27 US municipalities          | restricting | $10k liability bonds = 25–50% of annual earnings
1916 | San Francisco                 | restricting | 700-driver cap; banned Market St 10:30am–4pm
```

**Atlas-grounded answer:**
The jitney movement has its own dedicated standalone entry. Per Reason (https://reason.com/1972/02/01/taxis-and-jitneys/): *"The jitney movement began in late 1914 in Los Angeles, when enterprising Model T owners discovered they could offer seats in their private cars for the same fare as a trolley: a nickel, or 'jitney.' The first documented jitney operation began on July 1, 1914, when driver L.P. Draper used his Ford Model T to transport a passenger for five cents. By March 1915, thousands of jitneys operated in the southern and western United States."*

The "war" was a coordinated regulatory rollback, with three concrete instruments:

1. **Liability bonds.** Per the Rollins paper (https://files01.core.ac.uk/download/pdf/235715894.pdf): *"By July 1915, twenty-seven municipalities had already imposed burdensome liability costs to all jitney drivers. Drivers were compelled to post up to $10,000 in liability insurance, biting into 25 to 50 percent of drivers' annual earnings."*
2. **License restrictions.** Per slchistory.org (https://www.slchistory.org/2020/02/jitneys-early-automobile-ridesharing.html): *"For example, in Salt Lake City, a new city ordinance went into effect on April 1, 1915, and by April 4 nearly all of the SLC Jitney operators surrendered their licenses leaving only 2 Jitney busses in operation out of a previous fleet of nearly 40."*
3. **Route and time-of-day bans.** Per slchistory.org: *"The Jitney Bus Ordinance passed in August 1916 in San Francisco limited the number of jitney drivers to 700 and forbade jitneys on Market Street from Fremont to 6th Street between the hours of 10:30 a.m. and 4 p.m."*

**Outcome.** Per Rollins: *"By 1918, more than 90% of the jitney services that opened in 1915 had ceased operations."*

The atlas frames the broader pattern: *"The jitney is the cleanest case study in 20th-century transit of an entry-permissive technology (mass-produced automobile + flag-down model + cash fare) defeated by incumbent-protective regulation. The pattern recurs almost beat-for-beat with Uber and Lyft a century later."*

**Coverage assessment:** complete and well-sourced — this is one of the strongest entries in the atlas.

---

## Q7: How did buses interact with the streetcar industry — competition, replacement, regulatory capture?

**SQL:**
```sql
-- Find any entry mentioning streetcar / tram in predecessors, failed_alternatives, or descriptions
SELECT id, name FROM entries
WHERE json_extract(data, '$.description') LIKE '%streetcar%'
   OR json_extract(data, '$.description') LIKE '%tram%';

-- Pull predecessors mentioning streetcar/trolley
SELECT e.id AS entry_id,
       json_extract(p.value, '$.name')         AS name,
       json_extract(p.value, '$.relationship') AS relationship,
       json_extract(p.value, '$.brief')        AS brief
FROM entries e, json_each(json_extract(e.data, '$.predecessors')) p
WHERE json_extract(p.value, '$.name') LIKE '%streetcar%'
   OR json_extract(p.value, '$.name') LIKE '%tram%'
   OR json_extract(p.value, '$.name') LIKE '%trolley%';
```

**Raw results:**
```
standalone:jitney_movement → predecessor "Streetcar (electric tram)" (competing_predecessor, 1888):
  "The five-cent streetcar fare set the price point that jitneys imitated. Streetcar
   companies were the chief lobbyists behind the anti-jitney ordinances."

bus:trolleybus → predecessor "Electric tram (Siemens 1881, Lichterfelde)" (evolved_from):
  "Removing the rails (and the rail-vehicle franchise) was the trolleybus's main innovation."

bus:motorized_gasoline → failed_alternatives "Jitney" describes the streetcar lobby's role.
```

**Atlas-grounded answer:**
The atlas covers two of the three sub-questions well; the third (direct motorbus-vs-streetcar competition and replacement) only obliquely.

**Competition / regulatory capture.** Per the jitney entry: *"The five-cent streetcar fare set the price point that jitneys imitated. Streetcar companies were the chief lobbyists behind the anti-jitney ordinances."* And from the motorized gasoline bus entry's `failed_alternatives` for the jitney: *"Killed within four years by combinations of liability insurance requirements, route restrictions, and operating-time limits sponsored by streetcar companies and supportive municipalities."* This is an explicit regulatory-capture claim — streetcar incumbents shaping municipal rules to suppress a new entrant.

**Replacement (trolleybus side).** The trolleybus is framed as a tram successor that kept the electric-grid model but discarded the rails. Per the trolleybus entry's `evolved_from` predecessor: *"Siemens's 1881 Lichterfelde tram, then the Paris Electric Exposition tram with overhead lines, are direct technological parents of the trolleybus. Removing the rails (and the rail-vehicle franchise) was the trolleybus's main innovation."*

**Direct motorbus-vs-streetcar replacement.** The atlas does not have a direct entry on the streetcar industry's collapse (e.g., no entry on the "Great American Streetcar Scandal" / GM-Firestone NCL conspiracy of the 1930s–50s). The motorized gasoline bus entry mentions in passing that diesel buses displaced gasoline buses from the 1930s and that trolleybuses were displaced from the 1950s, but the streetcar dimension is implicit, not narrated.

**Coverage assessment:** partial. The jitney/streetcar conflict is well-covered; the motorbus-replacing-streetcar narrative of the 1930s–50s is missing.

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
1662 | Blaise Pascal             | underrecognized | France  | bus:horse_omnibus
1826 | Monsieur Omnès            | obscure         | France  | bus:horse_omnibus
1862 | Alphonse Beau de Rochas   | underrecognized | France  | component:internal_combustion_engine
1846 | Robert William Thomson    | underrecognized | UK (Scotland) | component:pneumatic_tire
1895 | Netphener Omnibusgesellschaft | underrecognized | Germany | bus:motorized_gasoline
1914 | L.P. Draper               | obscure         | USA     | standalone:jitney_movement
2010 | Proterra (Dale Hill, Jeff Granato) | underrecognized | USA | bus:battery_electric_modern
2010 | Foothill Transit          | underrecognized | USA     | bus:battery_electric_modern
```

**Atlas-grounded answer:**
The atlas tags eight innovators as `underrecognized` or `obscure` across the bus tree:

* **Blaise Pascal (France, 1662) — `underrecognized`.** Per Wikipedia (https://en.wikipedia.org/wiki/Carrosses_%C3%A0_cinq_sols): *"The carrosses à cinq sols (English: five-sol coaches) was the first modern form of public transport in the world, developed by mathematician and philosopher Blaise Pascal and operated in Paris in the 1660s."*
* **Monsieur Omnès (France, 1826) — `obscure`.** The hatter who unintentionally named the omnibus. Per the Library of Congress folklife blog (https://blogs.loc.gov/folklife/2020/02/the-legend-of-monsieur-omnes/): *"The service started at the Place du Commerce, outside the hat shop of M. Omnès, who displayed the motto Omnès Omnibus ('Omnès for all') on his shopfront."*
* **Alphonse Beau de Rochas (France, 1862) — `underrecognized`.** Per Wikipedia: *"the four-stroke cycle was patented in 1862 by the French engineer Alphonse Beau de Rochas, but it is commonly known as the Otto cycle."* He had the concept; Otto built the working machine and got the credit.
* **Robert William Thomson (UK, 1846) — `underrecognized`.** Per Wikipedia (https://en.wikipedia.org/wiki/John_Boyd_Dunlop): *"Two years after he was granted the patent, Dunlop was officially informed that it was invalid as Scottish inventor Robert William Thomson had patented the idea in France in 1846 and in the US in 1847."*
* **Netphener Omnibusgesellschaft (Germany, 1895) — `underrecognized`.** The operating company (not just Benz) that ran the world's first scheduled motorbus. Per Urban Transport Magazine: *"The newly founded Netphener Omnibusgesellschaft opened the first ever bus route from Siegen via Netphen to Deuz."*
* **L.P. Draper (USA, 1914) — `obscure`.** The first jitney driver. Per Reason: *"The first documented jitney operation began on July 1, 1914, when driver L.P. Draper used his Ford Model T to transport a passenger for five cents."*
* **Proterra founding team (USA, 2010) — `underrecognized`.** Per Wikipedia (https://en.wikipedia.org/wiki/Proterra_EcoRide): *"The Proterra EcoRide BE35 is a 35-foot fast-charge battery electric low-floor transit bus manufactured by Proterra from 2010 to 2014. The EcoRide featured lithium-titanate battery chemistry, which enabled fast on-route charging using the company's proprietary charger."*
* **Foothill Transit (USA, 2010) — `underrecognized`.** Per NREL (https://docs.nrel.gov/docs/fy21osti/80022.pdf): *"Foothill Transit became the first public transit agency in the nation to deploy three Proterra fast-charge, all-electric buses in 2010 on the 16.1-mile Line 291 between Pomona and La Verne."*

**Coverage assessment:** complete (the recognition_status field is being used as designed). For the *modern* bus specifically (post-1900), the under-credited names are clustered around the operators (Netphener, Foothill Transit) and the niche-chemistry pioneer (Proterra) rather than chassis engineers. Atlas does not yet name individual chassis or transmission engineers (e.g., AEC, Leyland, GM) — a real gap if the question is taken narrowly.

---

## Q9: Compare bus diffusion in the US vs. UK vs. Germany, 1900-1940.

**SQL:**
```sql
SELECT e.id AS entry_id,
       json_extract(g.value, '$.place') AS place,
       json_extract(g.value, '$.year')  AS year,
       json_extract(g.value, '$.milestone') AS milestone,
       json_extract(g.value, '$.brief') AS brief
FROM entries e, json_each(json_extract(e.data, '$.geographic_diffusion')) g
WHERE CAST(json_extract(g.value, '$.year') AS INTEGER) BETWEEN 1900 AND 1940
ORDER BY year;
```

**Raw results:**
```
1911 | London, United Kingdom | saturation | bus:motorized_gasoline | "London's last horse omnibus is withdrawn..."
1915 | Western and southern United States | 10pct | standalone:jitney_movement | "thousands of jitneys operated"
```

**Atlas-grounded answer:**
The atlas has only two `geographic_diffusion` datapoints in the 1900–1940 window:

* **UK — London, 1911 (`saturation`):** *"London's last horse omnibus is withdrawn. The motorbus has effectively replaced the horse on London streets within sixteen years of the Netphen experiment."* (No inline source URL.)
* **US — western/southern US, 1915 (`10pct`, jitney):** Per Reason: *"By March 1915, thousands of jitneys operated in the southern and western United States."*

**Germany — no datapoints in the 1900–1940 window.** The German diffusion record stops at 1895 Siegerland (`first`) and resumes at 1882 for the trolleybus and 2010s for battery-electric. The atlas has no city-level adoption datapoints for German motorbuses in the early 20th century.

A defensible *qualitative* comparison from the atlas: **UK saturation was earliest** (1911), the **US adoption pattern was distinctive in being attacked by regulation** (jitney, 1915–18), and **Germany's pioneer status (1895) was followed by a coverage gap** in the atlas. But this is not a quantitative comparison — the atlas does not support it.

**Coverage assessment:** sparse. The question asks for a comparison the atlas cannot cleanly support. Three datapoints across 40 years and three countries is not enough to compare diffusion rates.

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

**Raw results (truncated to early-bus):**
```
bus:horse_omnibus | Louis XIV / Duc de Roannez consortium | government | 1662–1677
  "Pascal's enterprise required a royal privilege granted in 1661–1662; the Duc de Roannez
   (Pascal's patron) and a noble consortium funded operations."

bus:horse_omnibus | Stanislas Baudry / Entreprise Générale des Omnibus | private | 1826–1855
  "Baudry self-funded the Nantes service from his mill business, then organised the
   Paris-based Entreprise Générale des Omnibus in 1828. The firm lost money in its first
   two years of operation and nearly failed."

bus:motorized_gasoline | Netphener Omnibusgesellschaft | private | 1895
  "A locally-organised private company financed the route and the two Benz buses. The post
   office's refusal to serve the route created the opening."

bus:motorized_gasoline | Benz & Cie | private | 1895
  "Manufacturer of the buses; supplied parts and the Mannheim-based mechanic on call."

bus:trolleybus | Siemens & Halske | private | 1882
  "Funded and built the Elektromote demonstration as a corporate proof-of-concept."

bus:trolleybus | Municipal transit authorities (Western Europe and N. America) | government | 1930s–1950s

bus:trolleybus | Soviet state planning ministries | government | 1933–1991
  "From 1933 (Moscow's first line) onward, the Soviet state built the world's largest
   trolleybus network. The strategic logic — domestic electricity, no imported oil — kept
   Eastern-bloc trolleybus systems growing through the period that Western systems were
   being scrapped."

standalone:jitney_movement | Individual drivers (owner-operators) | private | 1914–1918
  "The jitney was capital-light: a driver's existing Model T was the entire fleet. This is
   what made it explosively scalable and what made $10,000 insurance bonds so effective at
   killing it."
```

**Atlas-grounded answer:**
The atlas paints a clear picture of how funding type shaped each bus generation:

* **Horse omnibus (1662–1855):** mixed royal/private. Pascal needed royal privilege (1662); Baudry self-funded from a mill business (1826) and per Wikipedia (https://en.wikipedia.org/wiki/Omnibus): *"The omnibuses proved extremely popular from the start, though Baudry's firm lost money in its first two years of operation and nearly failed."*
* **Motorbus (1895):** purely private and bottom-up. The Netphen line was a *response to a market gap* that the Royal Prussian Postal Service refused to fill — a classic "regulatory unbundling creates a private opening" pattern.
* **Trolleybus:** corporate demonstration (Siemens 1882), then municipal capex (1930s–50s West), then state-strategic capex (USSR 1933–91). The Soviet pattern is the most consequential — the atlas explicitly attributes the survival of the trolleybus globally to socialist-bloc government funding.
* **Jitney:** owner-operator capital. The atlas's framing: *"The jitney was capital-light: a driver's existing Model T was the entire fleet. This is what made it explosively scalable and what made $10,000 insurance bonds so effective at killing it."* — funding structure directly determined regulatory vulnerability.
* **Modern battery-electric (2010+):** government-led via subsidies. China's "New Energy Vehicle" program plus FTA Low-No grants in the US.

The clearest shaping pattern across the atlas: **funding source determined what kinds of regulation the variant could survive.** Capital-heavy government-funded modes (trolleybus, BRT) survive permitting fights; capital-light owner-operator modes (jitney) are obliterated by insurance mandates.

**Coverage assessment:** complete; the funder dimension is one of the better-populated arrays.

---

## Q11: What's the lag between the invention of the internal combustion engine and the first motorized gasoline bus?

**SQL:**
```sql
SELECT e.id,
       json_extract(k.value, '$.year')       AS year,
       json_extract(k.value, '$.event')      AS event,
       json_extract(k.value, '$.event_type') AS type
FROM entries e, json_each(json_extract(e.data, '$.key_dates')) k
WHERE e.id IN ('component:internal_combustion_engine', 'bus:motorized_gasoline')
  AND json_extract(k.value, '$.event_type') IN ('invention', 'patent')
ORDER BY year;
```

**Raw results:**
```
1862 | Beau de Rochas patents the four-stroke cycle as a concept.        | patent     | component:ICE
1876 | Otto builds the first working compressed-charge four-stroke engine, 9 May. | invention | component:ICE
1877 | Otto granted German patent for the four-stroke engine.            | patent     | component:ICE
1885 | Carl Benz builds the Patent-Motorwagen.                            | invention | bus:motorized_gasoline
1895 | Netphener Omnibusgesellschaft opens world's first scheduled motorbus, 18 March. | invention | bus:motorized_gasoline
```

**Atlas-grounded answer:**
Computed lags from atlas key_dates:

* **Otto's working engine (1876) → first motorbus (1895): 19 years.** Per Wikipedia (https://en.wikipedia.org/wiki/Nicolaus_Otto): *"After 14 years of research and development, Otto succeeded in creating the compressed charge internal combustion engine on May 9, 1876."* Per Urban Transport Magazine: *"On 18 March 1895, the world's first public transport line operated by a motorised bus rather than a stagecoach was opened."*
* **Beau de Rochas concept patent (1862) → first motorbus (1895): 33 years.** Per Wikipedia: *"the four-stroke cycle was patented in 1862 by the French engineer Alphonse Beau de Rochas."*
* **Benz Patent-Motorwagen (1885) → motorbus (1895): 10 years.** The car-to-bus lag is short because, per the atlas: *"The Benz car platform is the parent technology that, ten years later, scales up into the Netphen omnibus."*

The most narratively useful lag is **19 years**: working engine to scheduled motorbus. The 10-year car-to-bus lag is a useful secondary signal of how quickly the form factor scaled up once a working road vehicle existed.

**Coverage assessment:** complete. Both relevant entries have the dated invention events the question requires.

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

**Raw results:**
```
bus:motorized_gasoline   | 1895 first (Siegerland) → 1911 saturation (London)         | 16-year lag, no 1pct/10pct
bus:horse_omnibus        | 1662 first (Paris) → 1826 first (Nantes) → 1829 first (London) | three "first" entries, no 1pct/10pct/saturation
bus:trolleybus           | 1882 first (Halensee) → 1952 10pct (US) → 2024 saturation (CEE) | 70 years to 10pct
bus:battery_electric_modern | 2010 first (Shenzhen + Pomona) → 2017 saturation (Shenzhen) | 7-year lag, no 1pct/10pct
standalone:bus_rapid_transit | 1974 first (Curitiba) → 2014 saturation (Curitiba)          | 40-year lag (within one city)
standalone:jitney_movement | 1914 first (LA) → 1915 10pct (US south/west)                | 1-year lag
```

**Atlas-grounded answer:**
Lag-to-adoption summary derived from `geographic_diffusion.milestone`:

* **Motorbus (gasoline ICE):** first 1895 → saturation 1911 = **16 years** (Siegerland to London replacing all horse omnibuses). No `1pct` or `10pct` datapoints recorded. (Source for saturation: motorized gasoline bus entry, no inline URL.)
* **Trolleybus:** first 1882 → US 10pct ~1952 = **70 years to 10pct**. Per trolleybuses.org (https://trolleybuses.org/history/): *"At the peak of their operation in the early 1950s, trolleybuses represented about 10 percent of the transit activity in the United States, with more than 6500 units in operation."*
* **Jitney:** first 1914 → 10pct 1915 = **~1 year** to meaningful regional share. Per Reason: *"By March 1915, thousands of jitneys operated in the southern and western United States."* (Then killed within 3 more years.)
* **BRT:** first 1974 → saturation 2014 = **40 years within Curitiba** (54,000 to 2.4M daily passengers). Per Wikipedia (https://en.wikipedia.org/wiki/Bus_rapid_transit): *"expanding from servicing 54,000 daily passengers in its first year to over 2.4 million by 2014."*
* **Battery-electric:** first 2010 → Shenzhen saturation 2017 = **7 years for a single major city**. Per Wikipedia (https://en.wikipedia.org/wiki/BYD_K_series): *"2017 saw the southern metropolis of Shenzhen, with a population of over 17 million, complete a full transition to electric buses with a fleet of more than 16,000."*
* **Horse omnibus:** atlas only records "first" milestones in three cities (1662, 1826, 1829). No saturation date for the horse-omnibus form globally. The motorized bus's 1911 London saturation can be read as the implicit *displacement* point for horse omnibuses.

The diffusion-milestone enum (`first | 1pct | 10pct | saturation`) is **systematically underused**. Across all 6 entries with diffusion data, only one `10pct` for trolleybus and one `10pct` for jitney exist; no `1pct` entries anywhere. Most lags are derived from `first → saturation` jumps with nothing in between.

**Coverage assessment:** partial. The bookend dates are present but the middle-of-curve milestones (`1pct`, `10pct`) are largely missing, which is the most useful data for diffusion analysis.

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

**Raw results:**
Across the 6 entries with `enabling_components`, the atlas lists ~22 distinct components. By type:

```
infrastructure: paved urban streets; gasoline distribution network; overhead twin-wire DC
                power distribution; depot charging infrastructure; pantograph fast charger;
                dedicated bus-only running way; tube station with level pre-paid boarding
technology:     internal combustion engine (Otto cycle); pneumatic tire; trolley pole /
                current collector; DC traction motor; lithium-iron-phosphate battery;
                lithium-titanate battery; AC traction motor and inverter; biarticulated bus;
                mass-produced automobile (Ford Model T)
practice:       royal/municipal route concession; printed timetables and route signage;
                roadside mechanic / repair depot practice; cash fare collection at boarding
process:        transit-oriented development zoning
standard:       (none)
```

**Atlas-grounded answer:**
The atlas distinguishes four classes of enabler. Two stand out as recurring across multiple variants:

**Recurring technologies (apparent in 3+ variants):**
* **Pneumatic tire.** Per the motorized gasoline bus entry: *"Solid rubber tires were standard on early motorbuses (the 1895 Netphen buses had them). Pneumatic tires, scaled from Dunlop's 1888 bicycle tire, made motorbus rides tolerable for passengers and dropped the unsprung mass, enabling higher speeds and lower road damage. By the 1910s pneumatic tires were standard equipment."* Listed as enabler for motorbus, trolleybus, and (implicitly) battery-electric.
* **Internal combustion engine / electric traction motor.** Each propulsion variant lists its own.

**Recurring practices:**
* **Route concession / municipal license.** Per the horse-omnibus entry: *"Both Pascal and Baudry needed prior government permission to run a scheduled route in a public street. Baudry obtained municipal permission on 10 August 1826 before opening on 30 September. The bus business is a regulated business from day one; route licensing is a recurring theme across the variants."*
* **Depot maintenance.** Per the motorized gasoline bus entry: *"The Netphen line's downtime — days waiting for a Mannheim mechanic — was the binding constraint, not engine power. Motorbus operators developed a depot-based repair practice (own mechanics, own spare parts) that became the model for transit maintenance generally."*

**Variant-specific scaling enablers (one-shot but high-leverage):**
* For **BRT**: the dedicated lane, the tube station with pre-paid level boarding (per Wikipedia: *"turning the bus into a subway with specially designed stations that allow for same-level pre-paid boarding, dedicated busways, short headways, and higher-capacity vehicles (up to 270 passengers per double-articulated bus)"*), and transit-oriented zoning.
* For **modern battery-electric**: depot charging substation (the "binding constraint on rollout in many cities"), and either LFP overnight batteries (BYD) or LTO + pantograph fast-charging (Proterra).

The atlas surfaces a clean cross-variant insight: **infrastructure and practice enablers (filling stations, depots, route licenses, dedicated lanes, tube stations, charging substations) tend to be the binding constraints on scaling, not the propulsion technology itself.**

**Coverage assessment:** complete and rich; this is what the `enabling_components` dimension was designed for.

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

**Raw results — full sorted list:**

| Year | Entry | Event | Type |
|---|---|---|---|
| 1662 | bus | Pascal's carrosses à cinq sols open in Paris | invention |
| 1662 | bus:horse_omnibus | Pascal's carrosses open (18 Mar; 4th route 24 Jun) | invention |
| 1677 | bus:horse_omnibus | Pascal's carrosses cease operation | regulatory |
| 1826 | bus | Baudry begins horse-omnibus service in Nantes | invention |
| 1826 | bus:horse_omnibus | Baudry opens the Nantes omnibus, 30 Sep | invention |
| 1829 | bus | Shillibeer launches London's first omnibus service | adoption |
| 1829 | bus:horse_omnibus | Shillibeer launches the London omnibus, 4 Jul | adoption |
| 1862 | component:internal_combustion_engine | Beau de Rochas patents 4-stroke cycle | patent |
| 1876 | bus:motorized_gasoline | Otto demonstrates 4-stroke engine | invention |
| 1876 | component:internal_combustion_engine | Otto builds first working 4-stroke engine, 9 May | invention |
| 1877 | component:internal_combustion_engine | Otto granted German patent | patent |
| 1881 | bus:trolleybus | Siemens demonstrates first overhead-wire tram in Paris | invention |
| 1882 | bus | Siemens demonstrates Elektromote in Berlin | invention |
| 1882 | bus:trolleybus | Elektromote runs in Halensee (29 Apr – 13 Jun) | invention |
| 1885 | bus:motorized_gasoline | Benz builds Patent-Motorwagen | invention |
| 1888 | component:pneumatic_tire | Dunlop tests pneumatic tire (28 Feb), patents (7 Dec) | patent |
| 1895 | bus | Netphener Omnibusgesellschaft opens first ICE bus line | invention |
| 1895 | bus:motorized_gasoline | Netphener opens world's first scheduled motorbus, 18 Mar | invention |
| 1914 | bus:motorized_gasoline | Jitney movement begins in LA (L.P. Draper, Model T, 1 Jul) | adoption |
| 1914 | standalone:jitney_movement | L.P. Draper carries first paying jitney passenger, 1 Jul | invention |
| 1915 | standalone:jitney_movement | Anti-jitney ordinances spread to 27 cities by July | regulatory |
| 1918 | standalone:jitney_movement | >90% of 1915-era jitney services have ceased | regulatory |
| 1937 | component:articulated_bus | First articulated bus appears in Milan | invention |
| 1938 | component:articulated_bus | Twin Coach builds first North American articulated bus (Baltimore) | invention |
| 1952 | bus:trolleybus | Peak of US trolleybus operation (~10%, 6500 vehicles) | scaling |
| 1968 | standalone:bus_rapid_transit | Curitiba Master Plan adopted | regulatory |
| 1971 | standalone:bus_rapid_transit | Jaime Lerner becomes mayor of Curitiba | adoption |
| 1974 | bus | Curitiba opens world's first BRT corridor | invention |
| 1974 | standalone:bus_rapid_transit | First 20 km of Curitiba's RIT opens | invention |
| 2009 | bus:battery_electric_modern | BYD K9 prototypes begin testing in Shenzhen | invention |
| 2010 | bus | First commercial BEV services launch (BYD K9 Shenzhen + Proterra Foothill) | scaling |
| 2010 | bus:battery_electric_modern | Foothill Transit puts 3 Proterra EcoRide BE35 in service, 3 Sep | adoption |
| 2011 | bus:battery_electric_modern | BYD supplies 200 K9 buses to Shenzhen Universiade | scaling |
| 2017 | bus:battery_electric_modern | Shenzhen completes full conversion (~16,000 vehicles) | scaling |

**Atlas-grounded answer:**
The 33 dated events arrange into five cleanly-bounded eras:

1. **Pre-mechanical bus era (1662–1829).** Pascal's carrosses (Paris, 1662–1677), Baudry's Nantes omnibus (1826), Shillibeer in London (1829). The "route + flag-down" model is invented and named.
2. **Component readiness (1862–1888).** Beau de Rochas's patent (1862) and Otto's working engine (1876–77) prepare propulsion; Dunlop's pneumatic tire (1888) prepares the rolling chassis.
3. **First mechanized buses (1881–1895).** Siemens's overhead-wire tram (1881) → Elektromote trolleybus (1882) → Benz Patent-Motorwagen (1885) → Netphen motorbus (18 March 1895).
4. **Jitney interlude (1914–1918).** Mass-produced cars meet the bus model, then are extinguished by liability law within four years.
5. **Modern transformations (1937–2017).** Articulated bus (Milan 1937, Baltimore 1938) → BRT (Curitiba 1974) → battery-electric (Shenzhen + Pomona 2010, Shenzhen full fleet 2017).

The atlas's `event_type` enum surfaces the texture: 11 `invention`, 8 `adoption`/`scaling`, 5 `regulatory`, 3 `patent`. The 1914–1918 cluster is uniquely *regulatory-dense* — the only span where regulation events outnumber inventions.

**Coverage assessment:** complete on the date axis (every variant has key_dates); the timeline is the strongest cross-entry artefact in the atlas.

---

## Synthesis

### What worked well

* **Provenance.** Most claims have inline `quoted_text` + URL on the relevant array element. The audit trail held under direct citation pressure across all 14 questions.
* **Cross-entry timeline (Q14).** The `key_dates` array, aggregated across variants and stubs, produces a coherent and useful chronology with minimal post-processing.
* **Funder/regulatory coverage on the headline events.** Q4, Q6, Q10 all answered cleanly. Especially the jitney entry — that is a model of what a well-populated standalone looks like.
* **Predecessor and competing-predecessor relationships.** Q2 and Q5 both turned cleanly on the typed `predecessors[]` and `failed_alternatives[]` arrays. The distinction between `evolved_from`, `competing_predecessor`, and `inspiration` did real work.
* **Recognition-status field (Q8).** Filtering on `underrecognized | obscure` surfaces a legible "second tier" of contributors that essayists actually need.
* **Lag computation (Q11).** The atlas's structure made the engine→bus lag a one-query computation; the answer (~19 years) is exactly the kind of computational synthesis the atlas is designed to support.

### What was sparse / had gaps

* **City-level diffusion in 1900–1940 (Q3, Q9).** Only one motorbus diffusion datapoint (London 1911) for a 30-year window in which buses spread across every major Western city. This is the most noticeable hole.
* **Diffusion milestones below saturation (Q12).** The `1pct` and `10pct` milestones are almost never populated. Most variants only have `first` and `saturation` — useful for endpoints, useless for slope.
* **Streetcar industry interaction (Q7).** Atlas captures the streetcar lobby's role in killing jitneys, but does not document the 1930s–50s motorbus replacement of streetcars (no NCL/GM-Firestone narrative, no rail-removal regulatory moments).
* **Underrecognized chassis/transmission engineers (Q8).** No 20th-century coachbuilder or drivetrain engineer is named. AEC, Leyland, GM, Daimler-engineering individuals are absent.
* **Inline source URLs missing on some elements.** Several `predecessors[]` entries (steam bus, trolleybus on motorized_gasoline), `failed_alternatives[]` entries (battery streetcars), and UK regulatory moments (1865 and 1896 acts) have empty `sources: []` arrays. The narrative description is sourced; the structured array elements often are not.
* **Diesel bus has no entry of its own.** The atlas mentions the diesel bus repeatedly as a successor but does not have a `bus:motorized_diesel` variant. Given diesel was the dominant transit propulsion 1936–2020, this is a significant structural gap.

### What surprised

* **The bus is older than the engine that powers it** by 213 years (Pascal 1662 vs. Otto 1876). The model preceded the propulsion by such a margin that the atlas's `predecessors[]` chain has to span pre-Industrial Revolution coaching.
* **The trolleybus predates the gasoline bus by 13 years** (1882 vs. 1895). The standard "electric is the new alternative" framing is inverted in the bus tree — overhead-wire electric came first.
* **The jitney died in 4 years** (1914 launch, 1918 ~90% gone). The atlas presents this as the most regulatorily-sensitive transit innovation in the database, and explicitly calls it the historical analogue for modern ride-hailing.
* **Funder type predicts regulatory survival** (Q10 synthesis). Capital-heavy government-funded modes survive permitting fights; capital-light owner-operator modes are killed by insurance mandates. This pattern is implicit in the atlas but emerges only on cross-entry reading.
* **Curitiba's BRT was a refusal, not a build.** Per the atlas: Lerner *"resisted public pressure to widen arterial roads"* — the founding act was negative (don't widen), then the busway slotted into the saved corridor. This is a different shape of innovation than the others in the atlas.

### Suggested atlas extensions

Ranked roughly by narrative leverage:

1. **`bus:motorized_diesel`** — the dominant transit propulsion mode of the 20th century, currently missing.
2. **City-level diffusion entries** (Berlin, Paris, New York, Chicago) for the 1900–1940 window. Even one `1pct` or `10pct` milestone per city would close the most-noticed gap.
3. **Streetcar industry standalone or `transit:streetcar` category** with a regulatory_moment for the 1930s–50s motorbus replacement (and the GM/NCL controversy).
4. **`component:diesel_engine`** stub covering Rudolf Diesel and the migration from petrol to diesel in transit.
5. **Inline sources on the empty `sources: []` array elements**, especially the UK regulatory moments (1865, 1896) — these are the ones most likely to be cited in an essay and the missing URLs hurt the audit trail most.
6. **Coachbuilder/manufacturer underrecognized innovators** for the 1900–1960 period (AEC, Leyland, ACF, Yellow Coach, GM Truck & Coach) — would round out Q8.
7. **Saturation milestone for horse omnibus** globally (the 1911 London date is implicit but not coded into the horse-omnibus entry's diffusion array).
8. **`bus:hybrid_electric`** variant for the 1990s–2010s — currently appears only as a predecessor to the modern battery-electric bus.

### Eval-precursor signal

Strong candidates for formalization, with what to measure:

* **Q1 (invention attribution)** — measure: does the agent name Carl Benz + Netphener Omnibusgesellschaft + 1895 + Germany, with two distinct sources cited verbatim? Tests basic provenance discipline.
* **Q5 (counterfactual framing)** — measure: does the agent distinguish battery-electric (lost on energy density) from trolleybus (didn't lose then)? Tests careful reading of the atlas's framing rather than premature synthesis.
* **Q6 (jitney war)** — measure: does the agent surface all three regulatory instruments (liability bonds, license caps, route bans), the 90%-by-1918 outcome, and the modern-ride-hailing analogy? Tests whether structured retrieval composes into a multi-fact answer with citations.
* **Q11 (lag computation)** — measure: does the agent compute 19 years (Otto→motorbus) and 10 years (Patent-Motorwagen→motorbus) from the atlas's own dates? Tests whether `key_dates` arithmetic is a stable capability.
* **Q12 (diffusion milestones)** — measure: does the agent correctly *report the absence* of `1pct` and `10pct` data for most variants rather than fabricating? Tests epistemic restraint when the atlas is sparse.
* **Q3 / Q9 (sparse-coverage questions)** — measure: does the agent surface the gap honestly ("only one datapoint in the window") rather than pad with general knowledge? Tests "atlas-only" discipline under pressure.

The Q3/Q9/Q12 trio together would make a strong "epistemic honesty" eval bundle — three questions where the right answer is partly "the atlas doesn't fully cover this." Q1/Q6/Q11 would form a "structured-retrieval-with-provenance" eval bundle.

A meta-signal worth flagging for the eval program: this run was conducted entirely from `data/seeds/*.json` because `sqlite3` was blocked by the harness. The seeds are the source of truth, so the answers are valid, but the SKILL.md's promise of "query via direct SQL" was not testable. **A formal eval should include a permission-availability precondition check** so this failure mode is detected explicitly rather than silently routed around.
