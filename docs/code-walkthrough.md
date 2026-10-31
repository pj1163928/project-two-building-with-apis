# Code walkthrough: how the asset search makes, reads and displays API requests

This walkthrough follows one search from the keyboard to the API and back
to the console. To run the script, see "How to run" in the
[README](../README.md).

> Line links point at the code as of 2026-10-30. If the files change, the
> function names below are the reliable way to find each piece.

## The three layers

The code is split into three layers, and each one has a single job:

```
asset_search.py           ← talks to the user (prompts, tables, detail views)
providers/ambientcg.py    ← knows each API: URL, parameters, what the JSON looks like
providers/polyhaven.py
providers/openverse.py
providers/http.py         ← the only place a request is actually sent
```

Data flows down as a request and comes back up as plain Python dicts. The
sections below follow one real search, Poly Haven → `brick` → details for
#3, all the way through.

## 1. Startup and picking a provider: `asset_search.py`

[main()](../asset_search.py#L204) runs a loop: pick a provider, run a
search, then ask "Search again?".

The provider menu, [choose_provider()](../asset_search.py#L47), loops over
`PROVIDERS`, a list defined in
[providers/\_\_init\_\_.py](../providers/__init__.py#L13):

```python
PROVIDERS = [ambientcg, polyhaven, openverse]
```

Those are the **modules themselves**, not strings. Typing `2` returns the
`polyhaven` module. From then on the script calls `provider.search(...)`
and `provider.get_details(...)` without caring which provider it is.

This works because every provider module has the same pieces: `NAME`,
`TYPE_FILTERS`, `search()` and `get_details()`. Any module with those
pieces can be added to `PROVIDERS`.

## 2. Collecting input

[run_search()](../asset_search.py#L181) asks its questions through small
helper functions:

- [ask_nonblank()](../asset_search.py#L30) repeats the question until the
  user types something.
- [ask_number()](../asset_search.py#L36) repeats it until the user enters a
  number in range.
- [ask()](../asset_search.py#L21) turns Ctrl+C into a clean exit instead
  of a traceback.

The asset-type question only appears when `provider.TYPE_FILTERS` exists.
Openverse sets it to `None`, so the question is skipped for audio. The
answer is stored as a neutral word (`"textures"`, `"hdris"` or
`"models"`), and each provider translates it into its own API's
vocabulary. For example, ambientCG maps `"textures"` to `"material"` in
[ambientcg.py](../providers/ambientcg.py).

Then [run_search()](../asset_search.py#L193) hands off to the provider:

```python
rows = provider.search(query, asset_type)
```

## 3. Building the request: `providers/polyhaven.py`

[search()](../providers/polyhaven.py#L39) builds the query parameters as a
dict:

```python
params = {"q": "brick", "limit": 5}        # plus "t": "textures" if a type was picked
data = get_json("https://api.polyhaven.com/search", params, provider="Poly Haven")
```

`requests` turns that dict into the URL
`https://api.polyhaven.com/search?q=brick&limit=5`.

## 4. Sending the request: `providers/http.py`

Every request in the project goes through
[get_json()](../providers/http.py#L14):

```python
response = requests.get(url, params=params,
                        headers={"User-Agent": "AssetLibrary-CIDM3312/0.1"},
                        timeout=10)
```

- **User-Agent:** tells the server who is calling. Poly Haven's terms
  require one.
- **timeout=10:** stops waiting after 10 seconds.

Next, `get_json()` checks the result in three stages:

1. **Did a response arrive at all?** A timeout or connection failure
   raises `ProviderError` with a friendly message
   ([lines 27–37](../providers/http.py#L27-L37)).
2. **Was the HTTP status OK?** 429 (rate limited), 404 (not found), 5xx
   (server error) and other 4xx codes each raise their own message
   ([lines 40–58](../providers/http.py#L40-L58)).
3. **Is the body JSON?** [`response.json()`](../providers/http.py#L61)
   parses the text into Python dicts and lists. If the server sent HTML
   instead, that also becomes a `ProviderError`.

So `get_json()` has only two possible outcomes: it returns the parsed
data, or it raises a `ProviderError`. It never returns half a result.

## 5. Reading the JSON and making the rows

Back in `polyhaven.search()`, `data` now looks like this:

```python
{"keywordMatches": 123, "results": [{"slug": "patterned_brick_wall_03", "score": 0.63}, ...]}
```

Poly Haven needs two extra steps here:

- **The empty check** ([line 48](../providers/polyhaven.py#L48)): Poly
  Haven's search is "semantic" and always returns something, even for
  `zzqqxx`. When `keywordMatches` is 0, the code returns `[]`.
- **A second request per result**
  ([line 54](../providers/polyhaven.py#L54)): `/search` only returns IDs
  ("slugs"). To get names and sizes, the code calls `/info/{slug}` once for
  each of the 5 results.

Each result is then reduced to the same five keys every provider uses:

```python
{"id": "red_bricks_02", "name": "Red Bricks 02", "type": "texture",
 "info": "max 8192x8192, 2.5 x 2.5 m", "license": "CC0"}
```

Some raw values are converted along the way:

- **Type:** `/info` gives the type as a number, and `TYPE_NAMES` maps `1`
  to `"texture"`.
- **Physical size:** `dimensions` comes in millimetres, so
  [_physical_size()](../providers/polyhaven.py#L31) converts
  `[2500, 2500]` to `"2.5 x 2.5 m"`.

The other two providers do the same job more simply:

- **ambientCG** ([search](../providers/ambientcg.py#L30)) makes one
  request. It asks for extra fields with `include=title,type,maps,...`,
  because without `include` ambientCG returns bare IDs.
- **Openverse** ([search](../providers/openverse.py#L27)) makes one
  request with `page_size=5`. It turns `duration` (in milliseconds) into
  `m:ss`, and turns `license: "by"` plus `license_version: "4.0"` into
  `"CC BY 4.0"`.

## 6. Printing the table

The rows go back to `run_search()`. If the list is empty, it prints "No
Poly Haven matches...". Otherwise
[print_results()](../asset_search.py#L86) draws the table:

- It measures the longest value in each column, so the columns line up.
- [clip()](../asset_search.py#L81) shortens long names with `…`.

Because all three providers return the same five keys, this one function
prints every provider's table.

## 7. The details view

When the user picks `3`, the script calls
[show_details()](../asset_search.py#L172), which calls
`provider.get_details("red_bricks_02")`.

Poly Haven's [get_details()](../providers/polyhaven.py#L95) makes two
requests:

- `/info/red_bricks_02` for the name, authors, tags and download count.
- `/files/red_bricks_02`, which returns a large nested tree: map →
  resolution → format → `{size, url}`.

[_summarize_files()](../providers/polyhaven.py#L68) walks that tree and
adds up the sizes into two groups:

- **`maps`:** loose image files, totalled by resolution and format, e.g.
  `{"8k": {"jpg": 250_000_000, "png": ...}}`.
- **`bundles`:** any entry that carries an `include` list (blend, gltf,
  fbx and so on). Its size is the bundle file plus every texture it
  includes.

Details look different for each provider, so the script picks the
matching print function with a lookup table:

```python
DETAIL_PRINTERS = {ambientcg: show_ambientcg, polyhaven: show_polyhaven, openverse: show_openverse}
DETAIL_PRINTERS[provider](details)
```

[show_polyhaven()](../asset_search.py#L121) prints each field with
[print_field()](../asset_search.py#L100), which skips empty values. It
then lists the per-resolution totals, using
[human_size()](../providers/formatting.py#L4) to turn `626378` into
`611.7 KB`.

## 8. When something fails

If any request fails at any step (search, `/info` or `/files`),
`get_json()` raises a `ProviderError`. Nothing in between catches it, so
it travels all the way up to the `try` block in
[main()](../asset_search.py#L213-L216):

```python
try:
    run_search(provider)
except ProviderError as error:
    print(f"\nError: {error}")
```

The user sees one clean `Error:` line, then "Search again?". This single
`try` covers every failure case, so the provider code never needs its own
error handling.

There is one special case. ambientCG answers an unknown ID with **200 OK
and an empty list** instead of a 404. So
[ambientcg.get_details()](../providers/ambientcg.py#L44-L45) raises its
own `ProviderError` when it gets an empty list.

## Summary of the full trip

```
user types "brick"
  → asset_search.run_search()         collects input
  → polyhaven.search()                builds params {q, t, limit}
  → http.get_json()                   requests.get + status checks + .json()
  ← Python dict from the API JSON
  → polyhaven.search()                empty check, /info per result, 5-key rows
  ← list of rows
  → asset_search.print_results()      aligned table
user picks #3
  → polyhaven.get_details()           /info + /files → summarized dict
  → asset_search.show_polyhaven()     formatted fields and size totals
```

## Watching it live

To see the raw API data before the providers reshape it, set a breakpoint
on the `requests.get(...)` call in [providers/http.py](../providers/http.py#L21)
and run the script with the VS Code debugger. Inspect `url` and `params`,
then step over the call and look at `response.json()`.
