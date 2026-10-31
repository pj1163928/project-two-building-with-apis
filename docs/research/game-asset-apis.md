# Free APIs for an Open Game-Asset Library (CC0 / CC-BY)

**Date:** 2026-10-30. Every source below was accessed on 2026-10-30, and every "live test" was run that day with unauthenticated `curl` requests (no keys, no accounts, and a descriptive `User-Agent` such as `CIDM3312-student-research/0.1`).
**Context:** CIDM3312 Project Two, "Building with APIs." The project is a Django app that collects publicly usable game assets (textures, sounds, 3D models, HDRIs, plus 2D art and music if possible) and shows correct license and attribution for each one.

## TL;DR

**You can start with no signup at all.** Use **Poly Haven** for HDRIs, textures and models, and **ambientCG** for PBR materials and HDRIs. Both are 100% CC0, need no key, return JSON with thumbnails and direct download URLs, and are safe to cache in a local database. That covers textures, HDRIs and a starter set of 3D models from day one.

- **Sounds:** start with **Openverse** audio (no key, but anonymous use is capped at 20 requests/min and 200/day). It returns per-item `license`, `creator` and a ready-made `attribution` string, and much of its audio comes from Freesound. When you need more volume or filtering, add **Freesound APIv2** with a free account and API key. A token is enough for search and MP3/OGG previews. Original-quality downloads need OAuth2.
- **More 3D models:** add **Smithsonian 3D** (`3d-api.si.edu`). It needs no key, serves Open Access GLB files, and the objects are museum scans, not game props.
- **Sketchfab** search also needs no auth and returns per-model license, author and thumbnails. Its files, however, can only be downloaded by a logged-in Sketchfab user through OAuth2, so treat Sketchfab as "search and link out" unless you build OAuth login.
- **Wikimedia Commons** is a strong optional source for sounds, images and STL models. It needs no key and returns per-file license metadata, but you must send a descriptive User-Agent.
- **OpenGameArt.org and Kenney.nl have no API**, so you can only link to them by hand.
- **Pixabay** is not Creative Commons (it uses its own license) and needs a key. **Jamendo**'s API is free only for non-commercial use and needs a client_id.

## Comparison table

| Provider | Asset types | License of assets | Auth | Rate limits (documented / observed) | Per-asset license in API? | Signup |
|---|---|---|---|---|---|---|
| **Poly Haven** | HDRIs (997), textures (869), models (521)* | CC0 (all) | None | No numeric limit in ToS; unique Referer/User-Agent required | Implicit (everything is CC0); `authors` per asset | **None** |
| **ambientCG** | PBR materials (2,037), HDRIs (435), 3D models (34), decals, terrains etc. (2,928 total)* | CC0 (all) | None (optional Patreon bearer token for early access) | Not documented | Implicit (everything is CC0) | **None** |
| **Openverse** | Images (photos/illustrations) and audio (music, sound effects); "over 800 million" works | Mixed CC + PDM; filterable | None (anon) or OAuth2 client credentials | Anon: 20/min burst, 200/day (observed headers); page_size ≤ 20, depth ≤ 240 results (anon) | **Yes**: `license`, `license_version`, `license_url`, `creator`, `attribution` | None for anon; registering needs name, description and email (verified) |
| **Freesound APIv2** | Sound effects / audio | CC0, CC BY, CC BY-NC (and legacy Sampling+) | API key (token) for search/previews; OAuth2 for original downloads | 60/min and 2,000/day; 30/min and 500/day for downloads | **Yes**: `license`, `username` | Freesound account, then apply for a key |
| **Sketchfab Data API v3** | 3D models; "over 1 million free models" (CC) | Per model: CC BY, BY-SA, BY-ND, BY-NC, BY-NC-SA, BY-NC-ND, CC0 (plus paid store licenses) | None for search/detail; **OAuth2 user login for downloads** | Not found in docs | **Yes**: `license` {uid, label}; `user` | Sketchfab account (18+) for downloads/app |
| **Smithsonian 3D API** | 3D models (GLB/OBJ/PLY/STL etc.), 41,324 file rows* | Smithsonian Open Access (CC0 per Smithsonian; see notes) | **None** (observed) | Not documented | No license field; docs say all files are Open Access | **None** |
| **Smithsonian Open Access API** | 11M+ collection records (objects, images, 3D) | CC0 for Open Access items | api.data.gov key | 1,000 req/hour (api.data.gov default) | Not verified (see open questions) | Email, first and last name |
| **Wikimedia Commons (MediaWiki Action API)** | Images, audio, video, STL 3D (150M+ files total) | Mixed (CC0, CC BY, CC BY-SA, PD, GFDL...) | None for reads | 10 req/min unidentified; **200 req/min** with compliant User-Agent | **Yes** via `extmetadata` (`LicenseShortName`, `LicenseUrl`, `Artist`, `AttributionRequired`) | **None** (descriptive User-Agent required) |
| **Internet Archive** | Audio, music, video, etc. | Mixed; per-item `licenseurl` when set | None for reads | No numbers; honor 429/Retry-After | Partially (`licenseurl` metadata field, not always present) | None |
| **Jamendo API v3** | CC music | CC licenses per track (many NC/ND) | `client_id` | Not numerically documented | **Yes**: `license_ccurl` | Devportal account; API free only for non-commercial use |
| **ccMixter Query API** | CC music / remixes | Mixed CC (many NC) | None (observed) | Not documented | **Yes**: `license_url`, `license_name` | None |
| **Pixabay API** | Images, videos (API docs list no audio) | **Pixabay Content License (not CC)** | API key | 100 req / 60 s per key; must cache 24 h | No (single site license) | Pixabay account |
| **OpenGameArt.org** | 2D/3D art, sounds, music | CC0, CC-BY, CC-BY-SA, OGA-BY, GPL... | **No API** | n/a | n/a | n/a |
| **Kenney.nl** | 2D/3D game asset packs, audio | CC0 | **No API** | n/a | n/a | n/a |
| **NASA 3D Resources** | 3D models, textures (GitHub repo) | NASA media guidelines (not CC; "without copyright") | No API (GitHub only) | n/a | n/a | n/a |

\* Counts come from live API responses on 2026-10-30, not from an official statement.

---

## 1. Poly Haven: HDRIs, textures, models (CC0)

**Asset types and size.** The `/types` endpoint returns `["hdris","textures","models"]`. Live counts from `/assets?type=…` were 997 HDRIs, 869 textures and 521 models. These are observed values, not official ones ([api.polyhaven.com/types](https://api.polyhaven.com/types)).

**License.** "Our assets are all licensed as CC0, which is effectively Public Domain" and "You do not need to give credit" ([polyhaven.com/license](https://polyhaven.com/license)). Because everything is CC0, responses carry no per-asset license field. They do carry `authors` (for example `{"Andreas Mischok":"All"}`), which is useful for courtesy credit. Note that the site's own logos, renders and text are *not* CC0, and "Web scraping or data mining also requires express permission" (paraphrase of the license page). The API is the sanctioned route.

**API style.** Base URL `https://api.polyhaven.com`, JSON, with an OpenAPI spec at [api.polyhaven.com/api-docs/swagger.json](https://api.polyhaven.com/api-docs/swagger.json) ([GitHub README](https://github.com/Poly-Haven/Public-API)). Endpoints from the spec:
- `GET /types`, `GET /assets?type=&categories=&category=&collection=&attributes=`: the full list as one JSON object keyed by asset ID (no pagination; about 2.4 MB for all assets).
- `GET /search?q=&t=&limit=&min=&hybrid=`: "Hybrid semantic + keyword search."
- `GET /info/{id}`, `GET /files/{id}`: file tree with `url`, `size` and `md5` per resolution and format (e.g. `hdri.8k.hdr.url`).
- `GET /author/{id}`, `GET /taxonomy`, `GET /categories/{type}` (legacy).
- Each asset in `/assets` includes `thumbnail_url` (e.g. `https://cdn.polyhaven.com/asset_img/thumbs/blue_floor_tiles_01.png?width=256&height=256&format=webp&v=…`).

**Auth and signup.** None. ToS 2.3: "Poly Haven will never require payment, a license, or a key in order to access the API" ([ToS.md](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md)).

**Limits.** The ToS gives no numeric rate limit. It prohibits activity that "disrupts, interferes with, or degrades the performance of the API" (2.6). Responses send `Cache-Control: max-age=43200` (12 h) (observed header).

**API terms.** ([ToS.md](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md))
- 2.1: free "for any purpose, including commercial use."
- 2.4: "all API calls must be made with a unique "Referer" header or user-agent that matches your software name."
- 2.5: if you surface content through the live API, "you must make it clear to your users where that content comes from." A label naming Poly Haven or a "Powered by Poly Haven" credit is enough. It must not imply endorsement. The clause does not apply to downloaded or self-hosted CC0 files.
- The API is "as available" with no uptime guarantee (4.2).
- The response header `Terms-Of-Service` points to the same ToS (observed).

**Django fit.** Excellent. Set `requests.get(..., headers={"User-Agent": "AssetLibrary-CIDM3312/1.0"})`. A management command can pull `/assets?type=hdris` and the other types in one call each and upsert into a local `Asset` model, refreshing every 12 h or more. Store `thumbnail_url`, then fetch `/files/{id}` lazily on the detail page. Show a "Powered by Poly Haven" credit wherever the content appears.

**Live test (OK).** `GET /types` returned 200 with `["hdris","textures","models"]`. `GET /info/abandoned_greenhouse` returned 200 with `{"type":0,"name":"Abandoned Greenhouse","authors":{"Andreas Mischok":"All"},"max_resolution":[20650,10325],...}`. `GET /files/abandoned_greenhouse` returned 200 with `{"hdri":{"8k":{"hdr":{"url":"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/8k/abandoned_greenhouse_8k.hdr","size":105685456,"md5":"…"}}}}`. `GET /search?q=wooden%20crate&limit=2` returned 200 with `{"total":1237,"results":[{"slug":"wooden_crate_01","score":0.7541},…]}`.

## 2. ambientCG: PBR materials, HDRIs (CC0)

**Asset types and size.** The v3 `type` filter accepts `material`, `hdri`, `substance`, `decal`, `atlas`, `3d-model`, `plain-image`, `brush`, `terrain` and `hdri-element` ([v3 /assets docs](https://docs.ambientcg.com/api/v3/assets/)). Live `totalResults` was 2,928 overall, with 2,037 materials, 435 HDRIs and 34 3D models (observed).

**License.** "All ambientCG assets are under the Creative Commons CC0 1.0 Universal License," which covers both the files and the preview renders. "You don't need to give credit" ([docs.ambientcg.com/license](https://docs.ambientcg.com/license/)). No per-asset license field is needed. Short links take the form `ambientcg.com/a/<id>`.

**API style.** ([API home](https://docs.ambientcg.com/api/), [v3](https://docs.ambientcg.com/api/v3/))
- Versions v1, v2 and v3 are all documented. Use **v3**: `https://ambientCG.com/api/v3/<endpoint>`, GET only, with endpoints `/assets`, `/categories`, `/collections` and `/rss`.
- `/assets` parameters: `q` (AND keywords), `type`, `technique`, `sort` (`popular`, `latest`, `downloads`, `oldest`, `random`, `alphabet`), `id`, `date`, `limit` (1–500, default 100), `offset`, and `include` (`title`, `url`, `tags`, `thumbnails`, `previews`, `downloads`, `maps`, `dimensions`, …) ([v3 /assets](https://docs.ambientcg.com/api/v3/assets/)).
- Responses include `totalResults`, `nextPageHttp` and `previousPageHttp` for pagination.
- Without `include=` you get bare IDs only.

**Auth.** Optional. Patreon supporters can send a bearer token for early access and exclusive files. Nothing is required for public assets ([v3](https://docs.ambientcg.com/api/v3/)).

**Limits and terms.** No rate limits or API terms are documented. The docs warn that the site is run by one person and the API "is therefore potentially not as reliable or stable as needed for an 'enterprise-level' application" ([API home](https://docs.ambientcg.com/api/)). Be gentle: cache aggressively and don't proxy large ZIPs (they range from 7 MB to 300 MB or more).

**Django fit.** Excellent. Paginate with `limit=500&offset=…&include=title,url,tags,thumbnails,downloads`, store the thumbnails (64–2048 px PNG/JPG URLs) and download links (`https://ambientcg.com/get?file=Fabric086_1K-JPG.zip`), and link users straight to those download URLs.

**Live test (OK).** `GET /api/v3/assets?type=material&q=brick&limit=1&include=title,url,tags,thumbnails,downloads,previews` returned 200 with `{"totalResults":31,"nextPageHttp":"…offset=1…","assets":[{"id":"Ground111","title":"Ground 111","url":"https://ambientcg.com/a/Ground111","tags":[…],"thumbnails":{"256-PNG":"https://acg-media.struffelproductions.com/…/Ground111.png",…}}]}`. The v2 `full_json` endpoint also still responds (200) with `downloadFolders…downloads[].downloadLink`, `size` and `attribute` (for example "1K-JPG").

## 3. Openverse: CC image and audio aggregator (WordPress)

**Asset types and size.** Images and audio. Per the "Made with Openverse" page, the API gives access to "over 800 million openly licensed images and audio tracks" ([docs.openverse.org](https://docs.openverse.org/api/reference/made_with_ov.html)). Audio categories are `audiobook`, `music`, `news`, `podcast`, `pronunciation` and `sound_effect`. Live `/v1/audio/stats/` listed the sources Jamendo (644,709), Wikimedia Commons (3,986,828) and Freesound (591,898) ([OpenAPI schema](https://api.openverse.org/v1/schema/)).

**License.** Mixed. Filter with `license=by,by-nc,by-nc-nd,by-nc-sa,by-nd,by-sa,cc0,nc-sampling+,pdm,sampling+` or `license_type=all,all-cc,commercial,modification` ([schema](https://api.openverse.org/v1/schema/)). **License info is returned per item**: `license`, `license_version`, `license_url`, `creator`, `foreign_landing_url`, `source`, and a pre-composed `attribution` string. Openverse "does not verify its licensing status or make any representations or warranties," so users must confirm rights themselves (ToS clause 3, [terms](https://docs.openverse.org/terms_of_service.html)).

**API style.** Base `https://api.openverse.org/v1/`, JSON. Endpoints include `/images/`, `/audio/`, `/{type}/{id}/`, `/{id}/related/`, `/{id}/thumb/`, `/audio/{id}/waveform/`, `/{type}/stats/`, `/auth_tokens/register/`, `/auth_tokens/token/` and `/rate_limit/` ([schema](https://api.openverse.org/v1/schema/)). Search takes `q`, `source`, `license`, `license_type`, `category`, `extension`, `page` and `page_size`. Responses include `result_count`, `page_count` and `results`. The docs describe the search as for finding "the top 10,000 most relevant results, not for exhaustive search or bulk download."

**Auth and signup.** Anonymous access works, and openverse.org itself "operates using anonymous requests." Registered apps (`POST /auth_tokens/register/` with `name`, `description` and `email`) get a `client_id`/`client_secret` for the OAuth2 client-credentials flow. They must verify the email, or they stay at anonymous limits. Registered users get "slightly higher limits" ([schema, auth tag](https://api.openverse.org/v1/schema/)).

**Limits (observed).** Response headers showed `x-ratelimit-limit-anon_burst: 20/min` and `x-ratelimit-limit-anon_sustained: 200/day`. Anonymous `page_size=50` was rejected with `"page_size may not exceed 20 for anonymous requests"`, and page 21 with `"pagination depth may not exceed 240 for anonymous requests"`.

**API terms.** ([terms](https://docs.openverse.org/terms_of_service.html))
- "You must not scrape the content in the Openverse catalog."
- You must follow the documented rate limits and must not get around them with multiple machines.
- You must attribute CC works properly.
- Products must say they were made with Openverse and are not endorsed by it.
- Openverse "reserves the right to charge fees for commercial uses."

**Django fit.** Good for search-on-demand. Use an anonymous server-side `requests` call and cache results per query (for example with Django's cache framework) to stay under 200/day. Store only what users save to their library, which fits the no-scraping rule. The `attribution` string can be rendered as-is. Audio `url` is often a Freesound CDN preview MP3, a no-key way to get Freesound sounds with license data. 200/day is tight for a demo with several users, so registering (free, email only) is worthwhile.

**Live test (OK).** `GET /v1/audio/?q=footsteps&page_size=1&license=cc0,by` returned 200 with `{"result_count":240,"results":[{"title":"Footsteps, Stones, A.wav","creator":"InspectorJ","license":"by","license_version":"4.0","attribution":"\"Footsteps, Stones, A.wav\" by InspectorJ is licensed under CC BY 4.0. …","source":"freesound","url":"https://cdn.freesound.org/previews/345/345560_5121236-hq.mp3","filetype":"mp3","duration":18944}]}`. `GET /v1/images/?q=texture%20brick&license=cc0` returned 200 with a `thumbnail` at `https://api.openverse.org/v1/images/<id>/thumb/`.

## 4. Freesound APIv2: sounds

**Asset types and size.** Audio clips. The FAQ gives no official count ([FAQ](https://freesound.org/help/faq/)). Openverse indexes about 592k Freesound items (see above). That figure is Openverse's, not Freesound's.

**License.** Uploaders choose "zero (cc0)," "attribution (by)," or "attribution noncommercial (by-nc)." A 4th license, Sampling+, is being phased out ([FAQ](https://freesound.org/help/faq/)). **Per sound**, the `license` field gives "The Creative Commons license under which the sound is available to you," with values such as "Attribution," "Attribution NonCommercial" and "Creative Commons 0." `username` is returned too ([resources](https://freesound.org/docs/api/resources_apiv2.html)). Filter out NC sounds if the library promises commercial-safe assets.

**API style.** ([overview](https://freesound.org/docs/api/overview.html), [resources](https://freesound.org/docs/api/resources_apiv2.html))
- Base `https://freesound.org/apiv2`, JSON by default.
- Search is `GET /apiv2/search/` with `query`, `filter` (field:value, e.g. `license:"Creative Commons 0"`), `sort`, `fields`, `page`, and `page_size` (default 15, max 150). Responses include `count`, `next`, `previous` and `results`.
- Sound detail is `/apiv2/sounds/<id>/`, with `previews` (`preview-hq-mp3` etc.), `images` (waveform and spectrogram), `download`, and `url` (the Freesound page).

**Auth and signup.**
- A token (API key) is enough for basic calls, including previews: `?token=YOUR_API_KEY`.
- OAuth2 is required for "Download Sound (original quality)," upload, describe and pending uploads.
- Keys are requested at `https://freesound.org/apiv2/apply` ([overview](https://freesound.org/docs/api/overview.html)), which redirects to login, so **a Freesound account is required** (observed 302 to `/home/login/?next=/apiv2/apply/`).

**Limits.** "60 requests per minute and 2000 requests per day." Downloads, uploads and similar actions are limited to 30/min and 500/day. Going over returns a 429 ([overview](https://freesound.org/docs/api/overview.html)).

**API terms.** ([API ToS](https://freesound.org/help/tos_api/))
- "Terms for commercial use of the API will be negotiated on a case by case basis" (§3). A student project is non-commercial.
- Make only "limited intermediate copies of Content only as necessary" and "Do not make full copies of the database" (§1b).
- Don't allow access to or linking of the API or Content "from any location or source other than your Application" (§4a).
- No scraping (§4f).
- One key per application, kept secret (§2).
- Present Content according to its license (§1c).

**Django fit.** Good. Keep the token in an environment variable or settings, never in templates or JS. Call search server-side and embed `preview-hq-mp3` in an `<audio>` tag. Save metadata only for sounds a user adds to the library; don't mirror the catalog. Original downloads need an OAuth2 flow, so link out to the sound's Freesound page instead.

**Live test (partial).** `GET /apiv2/search/text/?query=door` with no token returned **401** with `{"detail":"Authentication credentials were not provided."}`, which confirms a key is required. A preview file on `cdn.freesound.org` (taken from the Openverse result) returned 200 to `HEAD`.

## 5. Sketchfab Data API v3: 3D models

**Asset types and size.** 3D models. "Sketchfab provides a library of over 1 million free models, available under Creative Commons licenses." API downloads come as glTF, GLB and USDZ, not as source formats such as FBX or OBJ ([Download API](https://sketchfab.com/developers/download-api)).

**License.** Per model. The search `license` filter accepts `by`, `by-sa`, `by-nd`, `by-nc`, `by-nc-sa`, `by-nc-nd`, `cc0`, `ed` and `st` ([swagger.json](https://docs.sketchfab.com/data-api/v3/swagger.json)). `ed` and `st` appear to be Sketchfab Store licenses, which is unverified. `GET /v3/licenses` returns each license's `label`, `fullName`, `requirements` and CC `url` (live). Each search result includes `license: {uid, label}` and a `user` object.

**API style.** Base `https://api.sketchfab.com/v3/` ([overview](https://sketchfab.com/developers/data-api/v3), [docs](https://docs.sketchfab.com/data-api/v3/index.html)).
- `GET /v3/search?type=models&q=&downloadable=true&license=cc0&count=` uses cursor pagination (`next`, `cursors`).
- `GET /v3/models` filters by `downloadable`, `tags`, `categories`, `max_face_count` and more.
- Thumbnails come back in `thumbnails.images[]` (multiple sizes).
- Downloads use `GET /v3/models/{uid}/download` ([swagger](https://docs.sketchfab.com/data-api/v3/swagger.json)).

**Auth.** "Some endpoints are public, while others require authentication with OAuth or your API Token" ([overview](https://sketchfab.com/developers/data-api/v3)). Search, detail and licenses work anonymously (live). **Downloads**: "Downloading models requires users to be authenticated with a Sketchfab account," and end users "must be able to log in with their Sketchfab account inside your application." Apps without end-user login must contact Sketchfab ([guidelines](https://sketchfab.com/developers/download-api/guidelines)). The download call uses an OAuth Bearer token and returns temporary `gltf` and `usdz` URLs with `expires: 300` that "you should not cache" ([downloading models](https://sketchfab.com/developers/download-api/downloading-models)).

**Limits.** No rate limits found in the docs, and none appeared in response headers.

**Terms.** ([guidelines](https://sketchfab.com/developers/download-api/guidelines))
- "Your app should clearly display the license of the model as well as author attribution," typically the creator's username and a link to the model.
- "Your app must clearly mention that downloadable models are provided by Sketchfab."
- The API Agreement at [sketchfab.com/developers/terms](https://sketchfab.com/developers/terms) could not be fetched directly (empty or blocked response). A search-index summary of it mentions an 18+ age requirement and credential confidentiality. **Unverified.**

**Django fit.** Good for discovery: an anonymous server-side search with `downloadable=true&license=cc0` (or `by`, `by-sa`), storing `uid`, `name`, `license.label`, `user.username`, `viewerUrl` and a thumbnail. Don't store download URLs (they expire in 300 s). Either link out to `viewerUrl` for download, or implement Sketchfab OAuth2 login, which is a big chunk of extra work.

**Live test (OK).** `GET /v3/search?type=models&downloadable=true&q=crate&count=1` returned 200 with `{"cursors":…,"next":…,"results":[{"uid":"e1a6…","name":"Crate box","license":{"label":"CC Attribution"},"isDownloadable":true,"thumbnails":{"images":[{"url":"https://media.sketchfab.com/…jpeg","width":1920}]}}]}`. With `license=cc0` the results were Smithsonian models ("CC0 Public Domain"). `GET /v3/models/abc/download` without auth returned **401**.

## 6. Smithsonian: 3D API and Open Access API

**6a. Smithsonian 3D API (`3d-api.si.edu`).**
- **Endpoint.** `GET https://3d-api.si.edu/api/v1.0/content/file/search` with `q`, `rows`, `start`, `file_type` (`jpg`, `glb`, `ply`, `zip`), `file_quality` (`Low`, `Medium`, `High`, `Thumb`, `Full_resolution`, `Water_tight`, …) and `model_type` (`glb`, `ply`, `obj`, `gltf`, `f3z`, `blend`, `stl`) ([3D API docs](https://3d-api.si.edu/api-docs/); parameters read from the docs page's bundled data).
- **License.** The docs state: "All files referenced in these response streams are released as part of the Smithsonian's Open Access Initiative." **No per-record license field** is returned.
- **Auth.** None needed (observed).
- **Live test (OK).** `GET …/content/file/search?q=chair&rows=1` returned 200 with `{"rows":[{"title":"Side Chair","content":{"usage":"Web3D","quality":"Thumb","uri":"https://3d-api.si.edu/content/document/3d_package:ff60…/chair-(england),-1750-60-20k-512-thumb.glb","file_type":"glb","draco_compressed":true}}],"rowCount":47}`. `q=*` gave `rowCount` 41,324 file rows (several rows per model, one per quality level).
- **Fit.** Good for a "museum and scan" 3D category. GLBs are Draco-compressed, so a web viewer like `<model-viewer>` handles them. These are scanned artifacts, not game-ready low-poly props. The same models also appear on Sketchfab under the "Smithsonian" user as CC0 (live search above).

**6b. Smithsonian Open Access API (`api.si.edu/openaccess`).**
- **Endpoints.** `GET /api/v1.0/search?q=&start=&rows=&sort=&type=&row_group=`, `/content/:id`, `/category/:cat/search`, `/stats` ("stats for CC0 objects/media") and `/terms/:category`.
- **Key.** "The Open Access API requires an API key… register with https://api.data.gov/signup/" ([apidoc project/data](https://edan.si.edu/openaccess/apidocs/)). The repository has "over 11 million objects, artifacts and specimens" ([edan.si.edu/openaccess/docs](https://edan.si.edu/openaccess/docs/)).
- **Signup.** The Smithsonian signup form asks for email, first name, last name and website (observed form fields at [edan.si.edu/openaccess/signup/form](https://edan.si.edu/openaccess/signup/form)).
- **Limits.** api.data.gov's default is "1,000 requests per hour," and DEMO_KEY is 30/hour and 50/day per IP ([api.data.gov manual](https://api.data.gov/docs/developer-manual/)).
- **Live test.** Without a key: **403** `{"error":{"code":"API_KEY_MISSING",…}}`. DEMO_KEY was deliberately not used.
- **Fit.** Mostly useful for photos and metadata. For 3D, the keyless 3D API is simpler.

## 7. Wikimedia Commons (MediaWiki Action API)

**Asset types and size.** Images, audio, video and some 3D (STL). The live `siteinfo` statistics reported `"images":150145471` files ([live](https://commons.wikimedia.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json)). A `filemime:application/sla` search returned 11,815 STL files. `model/gltf-binary` returned 0.

**License.** Varies per file. Reusers should credit the creator and identify the license, linking to it where the license requires, since each file "may have different requirements" ([Reusing content](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)). **Per-file license is in the API**: `prop=imageinfo&iiprop=url|extmetadata|mime|size` returns `extmetadata.LicenseShortName`, `LicenseUrl`, `Artist` (HTML), `AttributionRequired` and `UsageTerms` (live). `iiextmetadatafilter` limits the keys, and `iiurlwidth` gives a scaled thumbnail URL (max 50 per request) ([API:Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo)).

**API style.** `https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrsearch=filetype:audio footsteps&prop=imageinfo…`. Pagination uses the `continue` object.

**Auth.** None for reads.

**Limits and rules.**
- A User-Agent is required on all requests. The format is `<client name>/<version> (<contact information>) <library>/<version>`. Generic agents like `python-requests` may be blocked, and a missing or generic UA gets a 403 ([User-Agent Policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)).
- New 2026 global limits: 10 req/min for unidentified clients and **200 req/min** for unauthenticated clients with a compliant User-Agent. They apply "across all sites… including requests to the Action API" and are "new in 2026 and are subject to experimentation and change" ([Rate limits](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits)).
- Make requests in series, not in parallel ([API:Etiquette](https://www.mediawiki.org/wiki/API:Etiquette)).

**Django fit.** Good. Set `User-Agent: AssetLibrary-CIDM3312/1.0 (your-contact) python-requests/2.x`. Sanitize the HTML in `Artist` (e.g. with `bleach`) before rendering. Embedding file URLs directly is "possible but not recommended" (paraphrase of [Reusing content](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)).

**Live test (OK).** The audio search returned 200 with `{"title":"File:Creepy footsteps and screaming and growl.wav","imageinfo":[{"url":"https://upload.wikimedia.org/…wav","mime":"audio/wav","extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},"AttributionRequired":{"value":"true"},"LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0"},"Artist":{"value":"<a href=…>Edisonisthebest</a>"}}}]}`. An empty User-Agent returned **403**.

## 8. Internet Archive (CC audio)

**API style.**
- The Metadata Read API is `GET https://archive.org/metadata/{identifier}`, returning `metadata`, a `files[]` array (name, format, size, md5), `server` and `dir` ([md-read](https://archive.org/developers/md-read.html)).
- The Scrape API (`/services/search/v1/scrape?q=&fields=&count=`) is mentioned in [aboutsearch](https://archive.org/help/aboutsearch.htm), which notes a 10,000-result limit for sorted paged advancedsearch results.

**License.** Per item via the `licenseurl` metadata field when the uploader set one (live). It is not guaranteed on every item. Mixed CC0, PDM, CC-BY, NC and so on.

**Auth and limits.** Reads need no auth (live). For bots: "All automated requests to archive.org must include a descriptive User-Agent header." Honor 429 and `Retry-After`, add delays, and cache responses ([bots](https://archive.org/developers/bots.html)). No numeric limits are given.

**Live test (mixed).** `GET /services/search/v1/scrape?q=mediatype:audio AND licenseurl:*creativecommons*&fields=identifier,title,licenseurl` returned 200 with `{"items":[{"identifier":"0-0-rainy-day-dub-september-5th-2006","licenseurl":"http://creativecommons.org/publicdomain/zero/1.0/",…}]}`. `GET /metadata/Free_20s_Jazz_Collection/metadata` returned 200 with `licenseurl`. `advancedsearch.php` returned `{"error":"[BACKEND_ERROR] Invalid or no response from Elasticsearch"}` at test time.

**Fit.** Possible but noisy: inconsistent metadata, large items, and few game-oriented assets. Optional.

## 9. Jamendo API v3 (CC music; bonus)

- **Base and auth.** `https://api.jamendo.com/v3.0/…`. JSON or XML. `client_id` is required. Get one by creating an app on devportal.jamendo.com and accepting the API terms ([docs](https://developer.jamendo.com/v3.0/docs), [tracks](https://developer.jamendo.com/v3.0/tracks)).
- **Tracks.** `/tracks` takes `limit` (max 200), `offset`, `search`, `tags`, `fuzzytags`, the filters `ccsa`, `ccnd` and `ccnc`, and `include=licenses`. Responses carry **`license_ccurl` per track**, `audio` (stream), `audiodownload`, `audiodownload_allowed` and `image`.
- **Terms** ([API terms](https://devportal.jamendo.com/api_terms_of_use)).
  - "The API may be used freely for non-commercial uses."
  - Credit both "the JAMENDO Members as the creators" and "JAMENDO as the provider," with backlinks.
  - "Applications must not be specifically designed to cache the content nor offering an offline access."
  - No numeric quota is stated.
- **Live test.** Without a valid client_id: 200 with `{"headers":{"status":"failed","code":5,"error_message":"Jamendo Api Invalid Client Id Error…"}}`.
- **Fit.** Usable for a "music" section in a student (non-commercial) project. Filter `ccnc=false&ccnd=false` for reusable tracks. Its tracks are also reachable via Openverse audio (`source=jamendo`).

## 10. ccMixter Query API (CC music; bonus)

- **API.** `https://ccmixter.org/api/query?f=json&tags=&lic=&limit=&offset=`, where `lic` takes `by`, `nc`, `sa`, `nod`, `byncsa`, `byncnd`, `s`, `splus`, `ncsplus` or `pd` ([query-api](https://ccmixter.org/query-api)). Auth and rate limits are not stated. Terms of Use are linked but were not reviewed.
- **Live test (OK, no auth).** 200 with `[{"upload_name":"Graciously Remote","user_name":"speck","license_url":"https://creativecommons.org/licenses/by-nc/4.0/","license_name":"Attribution Noncommercial (4.0)","file_page_url":"https://ccmixter.org/files/speck/71317",…}]`. Many tracks are NC.

## 11. Pixabay API (not CC; bonus for 2D)

- **Key and limits.** A `key` is required, and you must log in to see it. Default limit is "up to 100 requests per 60 seconds" per key. "Requests must be cached for 24 hours." "Permanent hotlinking of images… is not allowed," so download images to your server. "Show your users where the images and videos are from." Endpoints are `/api/` (images) and `/api/videos/`, with at most 500 results per query and `per_page` from 3 to 200 ([API docs](https://pixabay.com/api/docs/)).
- **License.** The **Pixabay Content License, not Creative Commons**. It allows free use without attribution, but you may not "sell or distribute Content… on a Standalone basis" ([license summary](https://pixabay.com/service/license-summary/)). That conflicts with an app whose purpose is redistributing assets, so mark it clearly as non-CC or skip it.
- **Live test.** Without a key: **400** `[ERROR 400] Invalid or missing API key`.

## 12. OpenGameArt.org (no API)

- `https://opengameart.org/api` and `/api/v1` return **404** (observed), and the FAQ never mentions an API ([FAQ](https://opengameart.org/content/faq)). An RSS feed exists at `https://opengameart.org/rss.xml` (200, observed). Its `robots.txt` lists many crawlers by name.
- The FAQ lists CC0, CC-BY 3.0/4.0, CC-BY-SA 3.0/4.0, OGA-BY 3.0/4.0 (a CC-BY variant without the DRM restriction) and GPL licenses.
- **Fit.** No supported programmatic access. At most, let users submit OGA links by hand with license metadata they enter themselves. Don't scrape.

## 13. Kenney.nl (no API)

- Assets are CC0: "all game assets on the asset pages are public domain licensed (CC0)" and "Attribution is not required." The only restriction mentioned: "Do not use our logo" ([support](https://kenney.nl/support)).
- No API: the support page doesn't mention one, and `kenney.nl/api` returns 404 (observed). Bulk access is a paid "All-in-1" bundle.
- **Fit.** Manual curation and links only.

## 14. NASA 3D Resources (no API; not CC)

- A GitHub repo: "a growing collection of 3D models, textures, and images from inside NASA," described as "free and without copyright," pointing to NASA usage guidelines ([GitHub](https://github.com/nasa/NASA-3D-Resources)).
- NASA content "generally [is] not subject to copyright in the United States," but logos and insignia are protected and use must not imply endorsement ([NASA guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)).
- No asset API. Access would go through GitHub's API, which has its own limits. Optional and low priority.

---

## Recommended combination

| Need | Primary (no signup) | Add later (needs key/account) | Why |
|---|---|---|---|
| **Textures / PBR materials** | **ambientCG** (2,037 materials) + **Poly Haven** textures (869) | n/a | Both CC0, no key, thumbnails plus direct download URLs, safe to cache in the DB |
| **HDRIs** | **Poly Haven** (997) + **ambientCG** (435) | n/a | Same as above. Poly Haven has rich attributes (time of day, weather) for filtering |
| **3D models** | **Poly Haven** models (521) + **Smithsonian 3D API** (GLB, Open Access) + **Sketchfab search** (link out) | Sketchfab OAuth2, only if in-app downloads are needed | Poly Haven gives game-ready CC0 models. Sketchfab gives scale and returns license and author per model |
| **Sounds** | **Openverse audio** (`category=sound_effect`, `license=cc0,by`) | **Freesound APIv2** token (free account) | Openverse returns a ready attribution string with no key but only 200 req/day. Freesound gives 2,000/day and richer filters |
| **Music (bonus)** | Openverse audio (`category=music`), ccMixter | Jamendo `client_id` (non-commercial API) | All return per-track license. Filter out NC/ND |
| **2D / sprites (bonus)** | Openverse images, Wikimedia Commons | n/a | Per-item license metadata. OpenGameArt and Kenney have no API, so link to them by hand |

**Getting-started order:** Poly Haven, then ambientCG, then Openverse, then Smithsonian 3D. All four work with plain `requests.get` and a custom User-Agent, so the project can be demoed before any keys exist. Then add Freesound once you have created an account and requested a key. Store it in `.env` or settings, never in templates or JS. Wikimedia Commons is a no-key bonus.

**Suggested Django data model.** A single `Asset` table with these fields:
- `provider`, `external_id`
- `asset_type`
- `title`, `author`, `author_url`
- `license_code`, `license_url`
- `attribution_text`
- `source_page_url`, `thumbnail_url`, `download_url`
- `fetched_at`

Use bulk sync management commands for Poly Haven and ambientCG; neither forbids caching. Fetch Openverse, Freesound and Jamendo lazily and save only what users add, to respect their no-scraping and no-full-copy terms. Show provider credits where their terms require it: "Powered by Poly Haven," "Made with Openverse," and "provided by Sketchfab."

## Open questions / unverified

1. **Sketchfab API Agreement** ([sketchfab.com/developers/terms](https://sketchfab.com/developers/terms)) returned an empty page to both WebFetch and curl. Its clauses (18+ age requirement, credential confidentiality, termination) come only from a search-engine summary and are **unverified**. The Developer Guidelines page ([sketchfab.com/developers/guidelines](https://sketchfab.com/developers/guidelines)) also returned empty. Rate limits are undocumented. The meaning of the `ed` and `st` license slugs is inferred, not confirmed.
2. **Smithsonian.** [si.edu/openaccess](https://www.si.edu/openaccess) and [si.edu/termsofuse](https://www.si.edu/termsofuse) returned 403, so the official CC0 item counts and the general terms of use were not verified. The 3D API has no rate-limit documentation and no per-record license field. The name of the per-record CC0/usage field in the Open Access API was not confirmed (it requires a key).
3. **ambientCG.** No documented rate limits, API terms, or hotlinking rules for `ambientcg.com/get?file=…` downloads. The status of v2 compared with v3 (deprecated or not) is not stated.
4. **Freesound.** No official catalog size. The docs don't explicitly say whether `download` in the sound instance works with a token (the overview says original-quality download requires OAuth2).
5. **Openverse.** The documented numeric rate limits for registered (authenticated) clients weren't found. The anonymous 20/min and 200/day figures and the page-size and depth caps come from live response headers and errors, not from written docs.
6. **Wikimedia.** The 2026 rate limits are marked "subject to experimentation and change."
7. **Internet Archive.** General terms of use were not reviewed. `advancedsearch.php` was erroring at test time. The Scrape API's documented parameters weren't fully read.
8. **Jamendo.** No numeric quota is published, and the commonly cited monthly request quota could not be confirmed. ccMixter's Terms of Use and rate limits were not reviewed.
9. **OpenGameArt.** Confirming the absence of an API rests on 404s and the FAQ's silence. No official statement says "there is no API."
10. All asset counts marked * are live API totals on 2026-10-30, not official figures.

## Sources

All accessed 2026-10-30.

**Poly Haven**
- API base: https://api.polyhaven.com (live: `/types`, `/assets`, `/info/{id}`, `/files/{id}`, `/search`)
- OpenAPI spec: https://api.polyhaven.com/api-docs/swagger.json
- Public API README: https://github.com/Poly-Haven/Public-API
- API Terms of Service: https://github.com/Poly-Haven/Public-API/blob/master/ToS.md
- License: https://polyhaven.com/license

**ambientCG**
- API docs home: https://docs.ambientcg.com/api/
- v3 docs: https://docs.ambientcg.com/api/v3/
- v3 /assets: https://docs.ambientcg.com/api/v3/assets/
- License: https://docs.ambientcg.com/license/

**Openverse**
- OpenAPI schema: https://api.openverse.org/v1/schema/
- API docs: https://api.openverse.org/v1/
- Terms of service: https://docs.openverse.org/terms_of_service.html
- Made with Openverse: https://docs.openverse.org/api/reference/made_with_ov.html

**Freesound**
- API overview: https://freesound.org/docs/api/overview.html
- APIv2 resources: https://freesound.org/docs/api/resources_apiv2.html
- API terms of use: https://freesound.org/help/tos_api/
- FAQ: https://freesound.org/help/faq/

**Sketchfab**
- Data API v3 overview: https://sketchfab.com/developers/data-api/v3
- Full docs and swagger: https://docs.sketchfab.com/data-api/v3/index.html, https://docs.sketchfab.com/data-api/v3/swagger.json
- Download API: https://sketchfab.com/developers/download-api
- Integration guidelines: https://sketchfab.com/developers/download-api/guidelines
- Downloading models: https://sketchfab.com/developers/download-api/downloading-models
- API Agreement (not directly readable): https://sketchfab.com/developers/terms

**Smithsonian**
- 3D API docs: https://3d-api.si.edu/api-docs/
- Open Access API docs: https://edan.si.edu/openaccess/apidocs/
- Open Access repository docs: https://edan.si.edu/openaccess/docs/
- Signup form: https://edan.si.edu/openaccess/signup/form
- api.data.gov developer manual: https://api.data.gov/docs/developer-manual/

**Wikimedia**
- User-Agent Policy: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
- Rate limits: https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits
- API:Etiquette: https://www.mediawiki.org/wiki/API:Etiquette
- API:Imageinfo: https://www.mediawiki.org/wiki/API:Imageinfo
- Reusing Commons content: https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia

**Internet Archive**
- Metadata Read API: https://archive.org/developers/md-read.html
- Developer index: https://archive.org/developers/index-apis.html
- Bots guidance: https://archive.org/developers/bots.html
- About search: https://archive.org/help/aboutsearch.htm

**Jamendo**
- API docs: https://developer.jamendo.com/v3.0/docs
- Tracks: https://developer.jamendo.com/v3.0/tracks
- API terms: https://devportal.jamendo.com/api_terms_of_use

**Other providers**
- ccMixter Query API: https://ccmixter.org/query-api
- Pixabay API docs: https://pixabay.com/api/docs/
- Pixabay license summary: https://pixabay.com/service/license-summary/
- OpenGameArt FAQ: https://opengameart.org/content/faq
- Kenney support: https://kenney.nl/support
- NASA 3D Resources: https://github.com/nasa/NASA-3D-Resources
- NASA media guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/
