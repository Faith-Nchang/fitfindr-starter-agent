# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does


FitFindr is a command-line agent for thrift shopping. You describe what you want in plain language, such as "vintage graphic tee under $30" or "90s track jacket in size M", and it pulls the keywords, size and price limit out of your sentence. It searches a file of 40 secondhand listings, picks the best match, and suggests outfits using pieces from your wardrobe (or general advice if your wardrobe is empty). It then writes a short caption you could post about the find. If nothing matches, it stops early and tells you which part of the search to change instead of making up an outfit.



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches `data/listings.json` for items matching a keyword description, optionally narrowed by size and a price ceiling. It does not call the model.
- **Inputs:** `description` (str, keywords such as "vintage graphic tee"); `size` (str or None, None skips size filtering); `max_price` (float or None, inclusive, None skips price filtering).
- **Returns:** A list of at most `config.SEARCH_RESULT_LIMIT` (10) listing dicts, best match first. Each dict has `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list of str), `size` (str), `condition` (str), `price` (float), `colors` (list of str), `brand` (str or None) and `platform` (str). Results are ranked by how many description keywords appear in the title, tags, category and description, and anything with zero keyword matches is dropped.
  - *Keyword rule:* the description is lowercased and split into words on anything that isn't a letter or digit. Filler words like "a", "the", "in", "under", "size" and "for" are ignored, so they never count as matches. Each remaining word scores one point per listing if it appears as a whole word in that listing's title, category, style tags or description (a plural counts as a match for the singular and the other way round, so "jeans" finds "jean"). Listings tied on score keep the order they have in the data file.
  - *Size match rule:* the size is compared case-insensitively against whole tokens of the listing's size, split on `/`, spaces and parentheses, so `M` matches `M`, `S/M` and `M/L` but not `XL`, `US 9` or `W30`. A listing whose size is `One Size` also matches any size.
- **When it has nothing:** An empty list `[]`. Not `None`, and no exception.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the found item, naming pieces the user already owns when the wardrobe has any.
- **Inputs:** `new_item` (dict, a listing dict as returned by `search_listings`); `wardrobe` (dict with an `items` key holding a list of wardrobe item dicts, each with `id`, `name`, `category`, `colors`, `style_tags` and `notes`).
- **Returns:** A non-empty string of outfit suggestions. With a populated wardrobe it names specific wardrobe pieces; with an empty one it gives general styling advice for the item.
- **When it has nothing:** An empty wardrobe (`{"items": []}`) is not an error. The tool returns general styling advice instead of `""` or an exception. It never returns an empty string.

### `create_fit_card`

- **What it does:** Writes a short social-media caption for the find, based on the item and the outfit idea.
- **Inputs:** `outfit` (str, the string returned by `suggest_outfit`); `new_item` (dict, the same listing dict).
- **Returns:** A string of two to four sentences that reads like a real post, mentions the item, its price and its platform once each, and is specific about the vibe. Wording varies from run to run.
- **When it has nothing:** If `outfit` is empty or only whitespace, it returns a descriptive message string saying there is no outfit to write a caption for. It does not raise and does not call the model.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what the user could change (loosen the price ceiling, drop the size, or use fewer or different keywords), leave `session["fit_card"]` as `None`, and return the session without calling `suggest_outfit`. Otherwise, put the first result in `session["selected_item"]` and go on to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** With regex, in `agent.py::parse_query`, with no model call. A phrase like "under $30", "below 30", "max $30" or a bare "$30" gives `max_price`; the single word after "size" gives `size`; whatever is left, with those phrases removed, is the `description`. A size or price that isn't in the query becomes `None`, so that filter is skipped.

**What moves through the session:** Each step writes its result into the session and the next step reads it back out, never passing a value straight from one call to the next. In order: `query` → `parsed` (description, size, max_price) → `search_results` → `selected_item` (the first result) → `outfit_suggestion` (made from `selected_item` and `wardrobe`) → `fit_card` (made from `outfit_suggestion` and `selected_item`). `error` stays `None` unless the search is empty, and then `outfit_suggestion` and `fit_card` stay `None`.

**Empty-search message:** when the branch fires, `agent.py::_no_results_message` searches again with only the keywords. If that finds something, the message names the size or price filter that removed everything; if not, it says the keywords matched nothing and suggests a plainer item word.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'
  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1: Y2K Streetwear**
Pair the baby tee with your **baggy straight-leg jeans** to balance the fitted top with loose denim. Add the **chunky white sneakers** for a retro footwear choice, and layer the **black cropped zip hoodie** over your shoulders or wear it unzipped. Accessorize with the **black crossbody bag**.

**Outfit 2: Contrast Grunge**
Tuck the baby tee into your **wide-leg khaki trousers** for an earthy, 2000s contrast. Slip on your **black combat boots** to ground the pastel print, and throw on the **vintage black denim jacket** for a textured, edgy outer layer.

  Fit card: scored this cute little butterfly baby tee on depop for $18 and I am obsessed. gives major 2000s mall rat energy, especially styled with baggy jeans or toned down with some chunky combat boots. such an easy throw-on piece for spring!

$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the listings matches 'designer ballgown'. Try fewer or different keywords — a plain item word like 'jacket' or 'tee' works better than a long description. `python app.py listings` shows what's in the data.
```

**State check:** I wrapped `suggest_outfit` to record the item it received and compared it with `session["selected_item"]` after the run. It was the same object (`lst_002`). On the empty query, `session["fit_card"]` and `session["outfit_suggestion"]` stayed `None` and `suggest_outfit` was never called.

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(r['id'], r['title'], r['size'], r['price']) for r in search_listings('graphic tee', max_price=30)])"
[('lst_002', 'Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 'L', 24.0), ('lst_017', 'Mesh Long-Sleeve Top — Black', 'S/M', 15.0), ('lst_033', 'Vintage Band Tee — Faded Grey', 'L', 19.0), ('lst_011', 'Low-Rise Cargo Pants — Khaki', 'W29', 27.0), ('lst_012', 'Oversized Crewneck Sweatshirt — Vintage Navy', 'XL (fits oversized)', 20.0), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 'L', 26.0)]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
**Outfit 1: 90s Grunge**
Pair the graphic tee with your **baggy straight-leg jeans, dark wash**. Layer your **vintage black denim jacket** on top. Anchor the look with your **black combat boots** and wear the **black crossbody bag**.

**Outfit 2: Streetwear Contrast**
Tuck the graphic tee into your **wide-leg khaki trousers**. Cinch the waist with the **brown leather belt**. Throw your **oversized grey crewneck sweatshirt** over your shoulders and finish with your **chunky white sneakers** and **black crossbody bag**.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[5]))"
Found this 2003 tour bootleg style graphic tee on depop for $24 and I'm obsessed. Giving major effortless Y2K concert vibes. Just gonna throw it on with some beat-up jeans and white sneakers and call it a day.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I gave Claude Code my Tool Inventory spec and asked it to build `search_listings`, `suggest_outfit` and `create_fit_card` in `tools.py`.
- *What came back:* The first version of `tools.py` didn't parse. A scripted edit turned `\n` inside the prompt strings into real line breaks, so Python raised a `SyntaxError` (unterminated string literal). Once that was fixed, the tools worked, but the code matched keywords as whole words and tolerated plurals ("jeans" finds "jean"), which my spec didn't say.
- *What I changed:* The broken prompt strings were fixed by hand-editing each one and then re-checking that the file parses. I tested each tool from the terminal before moving on. I also updated the keyword rule in my Tool Inventory to say whole-word matching with plurals, so the spec describes the code that exists.

**Moment 2**

- *What I asked for:* I asked Claude Code to wire the planning loop in `agent.py::run_agent` following my branch rule, and I ran the empty-search path to see what message it produced.
- *What came back:* The loop branched correctly and `suggest_outfit` was never called on an empty search. But when only a size had emptied the search (`graphic tee size XXS`), the message said "other sizes or prices do exist", which mentioned a price filter the query never had.
- *What I changed:* The message in `agent.py::_no_results_message` now names only the filters that were in the query ("Nothing matched 'graphic tee' with size XXS, but it does exist without that filter"). I re-ran the query to check.

**Where the AI did not write my work:** I wrote criteria 3, 4 and 5 and every "why this target" line in `criteria.md` myself. I asked Claude to say how it would test each criterion using only its sentence. It said criterion 4 ("clearly refers to the selected item or the outfit") couldn't be turned into a test.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Stretch Features (unit 4)


1. **A second tool moved onto MCP: `create_fit_card`.** It's registered in `mcp_server.py` next to `search_listings`, and `run_agent()` calls it with `call_tool`. I'm moving it before the "before" run, so both run logs measure the same system.

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | FAIL | FAIL | PASS | PASS | FAIL | MISSED (2/5) |
| 2. Impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item is the item passed to suggest_outfit | 5 of 5 | PASS | PASS | FAIL | PASS | PASS | MISSED (4/5) |
| 4. Fit card refers to the selected item | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Nothing returned is over the max price | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Run: `python run_eval.py --label before` (results in `results/run_2026-10-13_2231_before.md` and `.json`), cache off, 5 tries per scenario. Scored with `score_eval.py`, whose pass rules are written in its docstring. A criterion 1, 3 or 4 try that failed because the model returned 503 UNAVAILABLE is marked "(outage)" in the scorer: all four FAILs in the table (criterion 1 tries 1, 2 and 5; criterion 3 try 3) were outages, not the agent choosing wrongly. The diagnosis is in the next section.

**Real output from one try per criterion**, pasted as text.

**Criterion 1, try 3 (PASS)** — `agent.py::run_agent`, session at the end of the run:

```
error:             None
selected_item:     Y2K Baby Tee — Butterfly Print ($18, depop)
outfit_suggestion: **Outfit 1: Y2K Streetwear**
Pair the baby tee with your **baggy straight-leg jeans (dark wash)** to balance the fitted top. Layer the **black cropped zip hoodie** over top, leaving it unzipped to show the butterfly print. Finish with your **chunky white sneakers** and the **black crossbody bag**. 
…
fit_card:          scored this little butterfly print Y2K baby tee on depop for $18 and I’m literally obsessed. giving major 2000s mall rat energy, especially styled with baggy denim or contrasted with big khaki trousers. absolute steal.
```

**Criterion 1, try 1 (FAIL)** — same function, the run that ended in the model-unavailable handler (`agent.py::_model_failure_message`):

```
I found 'Y2K Baby Tee — Butterfly Print' ($18) but couldn't reach the model that writes the outfit and caption. Wait a minute and run the same query again. If it keeps failing, check your internet connection and GEMINI_API_KEY in .env.
  (detail: Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}})
```

**Criterion 2, try 1 (PASS)** — `agent.py::run_agent` / `agent.py::_no_results_message`:

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[3] branch: search came back empty
      →    stopping before suggest_outfit

error: Nothing in the listings matches 'designer ballgown'. Try fewer or different keywords — a plain item word like 'jacket' or 'tee' works better than a long description. `python app.py listings` shows what's in the data.
outfit_suggestion: None
fit_card:          None
```

**Criterion 3, try 1 (PASS)** — trace from `agent.py::run_agent`; the item chosen in step 3 is the item that goes into `suggest_outfit` in step 4:

```
[1] parse_query
      in:  90s track jacket in size M
      out: description='90s track jacket in', size='M', max_price=None
[2] search_listings (via MCP)
      in:  description='90s track jacket in', size='M', max_price=None
      out: 5 items: 90s Track Jacket — Navy/White Stripe, 90s Leather Bomber — Black, 90s Silk Slip Dress — Floral, Midi Length … +2 more
[3] select item
      out: 90s Track Jacket — Navy/White Stripe ($45.0, poshmark)
      →    first search result
[4] suggest_outfit
      in:  item='90s Track Jacket — Navy/White Stripe', wardrobe_items=10
      out: **Outfit 1: Sporty Streetwear** Pair the 90s Track Jacket with your white ribbed tank top tucked into the bagg…
[5] create_fit_card (via MCP)
      in:  item='90s Track Jacket — Navy/White Stripe', outfit='**Outfit 1: Sporty Streetwear**\nPair the…'
      out: Found this vintage 90s track jacket on Poshmark for $45 and I am never taking it off. It gives major off-duty …
```

**Criterion 4, try 1 (PASS)** — fit card from `tools.py::create_fit_card` (called via MCP from `mcp_server.py::create_fit_card`) for 90s Silk Slip Dress — Floral, Midi Length:

```
scored this 90s floral silk slip dress on depop for $30 and honestly haven’t stopped thinking about it since. dying to layer it under an oversized crewneck with combat boots for that effortless grunge look, or keep it simple with a vintage denim jacket and sneakers for running errands. total 90s rom-com dream.
```

**Criterion 5, try 1 (PASS)** — `search_listings` results (`tools.py::search_listings`, called via MCP) for "denim jacket under $50"; every price is at or under 50:

```
  Denim Jacket — Light Wash, Cropped — $42
  Vintage Levi's 501 Jeans — Medium Wash — $38
  90s Track Jacket — Navy/White Stripe — $45
  High-Waisted Denim Shorts — Cutoff — $24
  Shacket — Olive Canvas — $33
  Straight Leg Black Jeans — Faded — $30
  Denim Vest — Medium Wash, Studded — $27
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'denim jacket under $50' --trace`

```
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 7 items: Denim Jacket — Light Wash, Cropped, Vintage Levi's 501 Jeans — Medium Wash, 90s Track Jacket — Navy/White Stripe … +4 more
[3] select item
      out: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
      →    first search result
[4] suggest_outfit
      in:  item='Denim Jacket — Light Wash, Cropped', wardrobe_items=10
      out: **Double Denim Streetwear** Pair the light wash cropped denim jacket with your white ribbed tank top and baggy…
[5] create_fit_card (via MCP)
      in:  item='Denim Jacket — Light Wash, Cropped', outfit='**Double Denim Streetwear**\nPair the lig…'
      out: Scored this cropped light wash denim jacket on Poshmark for $42 and I’m officially obsessed. It’s giving major…
```

**Empty search** — `python app.py ask 'designer ballgown size XXS under $5' --trace`. Three steps instead of five: it stops at the branch and never reaches `suggest_outfit`.

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[3] branch: search came back empty
      →    stopping before suggest_outfit
```

**Failure messages** (each triggered on purpose):

- *Empty search:* `Nothing in the listings matches 'designer ballgown'. Try fewer or different keywords — a plain item word like 'jacket' or 'tee' works better than a long description. python app.py listings shows what's in the data.`
- *Empty wardrobe* (`--empty-wardrobe`): returns general styling advice and a fit card, no crash and no empty string.
- *Model unavailable* (bad `GEMINI_API_KEY`, set as an environment variable for the run rather than editing `.env`): `I found '90s Silk Slip Dress — Floral, Midi Length' ($30) but couldn't reach the model that writes the outfit and caption. Your API key was rejected. Check GEMINI_API_KEY in your .env file, then run the same query again.` A real 503 "high demand" from the model service produced the same handler with the advice to wait a minute and re-run.

**On the MCP move:** `search_listings` and (stretch) `create_fit_card` are registered in `mcp_server.py`, and `run_agent()` calls both with `mcp_client.call_tool`. `suggest_outfit` is still a direct call. Three things behaved differently after the move:

1. A tool that fails inside the server no longer raises its own exception in the agent. The client wrapped it in "unhandled errors in a TaskGroup" and hid the real message, so `mcp_client.py` now unwraps it and `run_agent()` catches `MCPError` as well as `ModelUnavailable`.
2. The server subprocess doesn't inherit environment variables, so `run_eval.py` turning the cache off in its own process never reached the server and fit cards would have come back from cache. The client now passes the environment and the cache setting through. Without that, five tries of criterion 4 would have been one caption five times.
3. Each MCP call starts a fresh server process, so every search and caption call is slower than a direct call.

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
