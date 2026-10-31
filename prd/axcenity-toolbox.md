# PRD — Axcenity Toolbox

**Date:** 2026-10-30
**Course:** CIDM 3312 Project 2, "Building With APIs"
**Source:** the agreed design from the `/grill-me` session (29 questions plus
one UI prototype), recorded in the handoff. The chosen Discover prototype is
the visual reference for every page.

**Priority tags:** every user story carries a build tier.

- **[T1] Essential:** covers every graded requirement. The project isn't
  done until all of these work.
- **[T2] Signature:** the features that make the Toolbox its own. Built
  after Tier 1.
- **[T3] Stretch:** listed under Out of Scope. Built only if time remains.

## Problem Statement

People making games with the Axcenity engine need free assets: textures,
HDRI skies, 3D models and sounds. Good CC0 and Creative Commons assets
exist, but they're spread across separate sites (ambientCG, Poly Haven,
Openverse), each with its own search, file formats and license wording.

Once an asset is found, there's nowhere to keep it alongside a note saying
whether it was tested, whether it worked, or which project it's for. The
links go stale, and the license and attribution details get lost. Putting
together a kit of assets for one project means a pile of browser tabs and
a hand-written list. Nothing hands that list to the engine in a form it
can load. A game maker also can't see what other Axcenity users have put
together for similar projects.

## Solution

Axcenity Toolbox is a website styled like the Axcenity editor. It is an
asset catalog and pack creator for the engine.

- **Discover:** a user picks an asset type and searches. Results from the
  matching free providers appear side by side, and a provider that's down
  shows a clear message without breaking the rest of the page.
- **Library:** one click saves an asset to a private library. The Toolbox
  keeps its own copy of the asset's details, so the library still works
  when a provider is offline. The user adds notes, a 1–5 rating and a
  status (To review, Testing, Approved, Rejected), and can search, filter,
  sort and page through everything they've saved.
- **Packs:** the user groups saved assets into tagged packs, which are kits
  for a project. For each item they choose the file variant (for example
  2K JPG) and where it should land in the engine. The site suggests other
  assets that fit the pack's tags.
- **Sharing:** packs are private until the owner makes them public. Public
  packs appear in a gallery on the main page. Anyone can view and export
  them, and signed-in users can save single items or copy the whole pack.
  Private notes, ratings and statuses never appear in a shared pack.
- **Export:** a pack exports as a versioned JSON manifest the engine can
  load. It lists every file's download URL, the import path, the license,
  and a credits list for assets that need attribution.
- **API:** the Toolbox has its own REST API for scripts. It covers listing,
  creating, updating and deleting library entries, and reading and
  exporting packs, with the same access rules as the website.

## User Stories

### Accounts and access

1. As a visitor, I want to sign up with a username and password, so that I can start my own asset library. **[T1]**
2. As a member, I want to sign in and sign out, so that only I can manage my library and packs. **[T1]**
3. As a visitor who opens a members-only page, I want to be sent to sign in and then returned to that page, so that I don't lose my place. **[T1]**
4. As a member, I want my library to be private, so that my notes, ratings and statuses are seen by me alone. **[T1]**
5. As a member, I want a link to another user's library item to show "not found", so that nobody can learn what other people have saved. **[T1]**
6. As a member, I want an API token page on my profile, so that I can use the Toolbox API from my own scripts. **[T1]**

### Discover

7. As a member, I want to choose one of four asset types (textures, HDRIs, models, sounds) from tiles, so that I only see the kind of asset I need. **[T1]**
8. As a member, I want a command-bar search that I can focus by pressing `/`, so that I can search without reaching for the mouse. **[T1]**
9. As a member, I want textures, HDRIs and models to come from both ambientCG and Poly Haven, and sounds from Openverse, so that each type searches the providers that actually have it. **[T1]**
10. As a member, I want each provider's results in their own shelf that loads separately, so that a slow provider doesn't hold up the others. **[T1]**
11. As a member, I want a failed provider's shelf to show what went wrong and a Retry button while the other shelf keeps working, so that one outage doesn't stop my search. **[T1]**
12. As a member, I want up to 12 results per provider, each with a thumbnail, title, author and license, so that I can judge an asset before saving it. **[T1]**
13. As a member, I want a "Save to library" button on each result that turns into "In library", so that saving takes one click and I can see it worked. **[T1]**
14. As a member, I want results I've already saved to show "In library", so that I don't save the same asset twice. **[T1]**
15. As a member, I want a broken thumbnail to be replaced by an icon for its type, so that the page never shows broken images. **[T1]**
16. As a member, I want each shelf to credit its provider ("Powered by Poly Haven", "Made with Openverse", "Assets from ambientCG · CC0"), so that I know where assets come from. **[T1]**
17. As a member, I want a search I repeat within the hour to come back quickly, and a failed search to be tried fresh on Retry, so that the site is fast without hiding a recovered provider. **[T1]**

### Library

18. As a member, I want a saved asset's details (title, author, license, attribution, files) stored by the Toolbox, so that my library still works when a provider is down. **[T1]**
19. As a member, I want my library shown as a card grid with thumbnail, type, title, status and rating, so that I can scan what I've collected. **[T1]**
20. As a member, I want to search my library by title, tags and my own notes, so that I can find an asset by anything I remember about it. **[T1]**
21. As a member, I want to filter my library by type, provider, status and minimum rating, so that I can narrow it to what I need right now. **[T1]**
22. As a member, I want to sort my library by newest saved (the default), oldest, title A–Z, or rating high to low, so that the most useful assets come first. **[T1]**
23. As a member, I want my library split into pages of 12, so that large libraries stay quick to browse. **[T1]**
24. As a member, I want the results to refresh without a full page reload while the address bar keeps my search, filters, sort and page, so that I can bookmark a view and use the Back button. **[T1]**
25. As a member, I want clicking a card to open a slide-over drawer with the asset's details, license, attribution, source link, file variants, and the packs it's in, so that I can review it without leaving the grid. **[T1]**
26. As a member, I want to set an asset's status (To review, Testing, Approved, Rejected) in the drawer, and have it save at once, so that I can track my testing. **[T1]**
27. As a member, I want to give an asset an optional 1–5 star rating that saves at once, so that I can mark my favourites. **[T1]**
28. As a member, I want my notes to save on their own shortly after I stop typing, so that I never lose a note by forgetting to press Save. **[T1]**
29. As a member, I want the card behind the drawer to update when I change status or rating, so that the grid always matches what I just did. **[T1]**
30. As a member, I want the drawer's link to open as a full page when visited directly, so that I can share or bookmark a single asset. **[T1]**
31. As a member, I want deleting a saved asset to first show which packs it will be removed from, so that I don't break a pack by accident. **[T1]**
32. As a member, I want an "Add to pack" dropdown on each library card, so that I can put assets into packs while browsing my library. **[T1]**
33. As a member, I want empty results and an empty library to tell me what to do next, so that I'm never staring at a blank page. **[T1]**

### Packs (owner)

34. As a member, I want to create a pack with a title, a description of its intended use, and tags, so that I can gather a kit for one project. **[T1]**
35. As a pack owner, I want to type tags as comma-separated text and have them tidied (lowercase, single spaces, simple plurals merged, pure numbers dropped), so that "Rocks" and "rock" count as the same tag. **[T1]**
36. As a pack owner, I want new packs to be private, with a switch to make them public or private again, so that I share only when I'm ready. **[T1]**
37. As a pack owner, I want to edit my pack's title, description and tags, or delete the pack, so that it stays accurate. **[T1]**
38. As a pack owner, I want an "Add from my library" search that filters as I type, so that I can fill a pack quickly. **[T1]**
39. As a pack owner, I want to pick the file variant for each item, defaulting to a 2K JPG (or MP3 for sounds) when one exists, so that the export gets the files I actually want. **[T1]**
40. As a pack owner, I want to set an import path for each item, with a sensible default when I leave it blank, so that the engine puts the files where my project expects them. **[T1]**
41. As a pack owner, I want to remove an item from a pack without removing it from my library, so that I can rework a pack freely. **[T1]**
42. As a pack owner, I want each change in the pack builder to save on its own, so that there's no Save button to forget. **[T1]**
43. As a pack owner, I want the same asset to have a different variant and import path in each pack, so that two projects can use it differently. **[T1]**
44. As a pack owner, I want my private notes, ratings and statuses never to appear through a pack, so that sharing a pack never shares my private thoughts. **[T1]**
45. As a pack owner, I want a "Suggested for this pack" list of known assets ranked by how many tags they share with the pack, leaving out items already in it, so that I find assets I'd have missed. **[T2]**
46. As a pack owner, I want adding a suggestion that isn't in my library to save it there as To review, so that every pack item stays something I can track. **[T2]**
47. As a pack owner, I want a "Find more from providers" button that searches using my pack's tags, so that I can go beyond what the Toolbox already knows. **[T2]**

### Main page and public packs

48. As a visitor, I want the main page to explain the site in four steps (01 Discover · 02 Save · 03 Pack · 04 Export) with Sign up and Sign in buttons, so that I understand it before creating an account. **[T1]**
49. As anyone, I want a gallery of public packs, each card showing a mosaic of its first 4 thumbnails, title, owner, tags and a summary such as "3 textures · 1 HDRI · 2 sounds", so that I can see what others have built. **[T1]**
50. As anyone, I want to search the gallery by title and tags, filter it to packs containing a type, sort it by newest or most items, and page through it 12 at a time, so that I can find a relevant pack. **[T1]**
51. As anyone, I want a public pack's page to list its items with licenses and attribution, so that I can decide whether to use it. **[T1]**
52. As a member viewing someone else's public pack, I want it to be read-only for me, so that only the owner can change it. **[T1]**
53. As anyone viewing a public pack (and as the owner of a private one), I want to export it as a manifest file, so that I can load it into the engine. **[T1]**
54. As a visitor, I want an animated hero of asset thumbnails from public packs, orbiting on rings coloured by type, where clicking one opens its pack, so that the main page shows real work at a glance. **[T2]**
55. As a member viewing a public pack, I want to save single items to my library, so that I can take just the parts I need. **[T2]**
56. As a member viewing a public pack, I want a "Copy pack" button that makes a private copy for me and adds any missing assets to my library as To review, so that I can start from someone else's kit. **[T2]**

### Export manifest

57. As an engine user, I want the manifest to state its format name and version, so that the engine can tell whether it can read the file. **[T1]**
58. As an engine user, I want each item to list its chosen variant's files with URLs, filenames and sizes, so that the engine can download exactly those files. **[T1]**
59. As an engine user, I want each item's license, author and attribution, plus one credits list for every asset that isn't CC0, so that I can credit creators correctly in my game. **[T1]**
60. As an engine user, I want an item with no import path to get a predictable default folder, so that every file has somewhere to go. **[T1]**

### API

61. As an API user, I want to list my library with the same search, filters, sorts and pages as the website, so that scripts see the same results I do. **[T1]**
62. As an API user, I want to save an asset by sending just its provider and ID (plus optional notes, rating and status), so that the server fills in the rest. **[T1]**
63. As an API user, I want saving an asset I already have to fail with "Already in your library.", so that my script knows nothing changed. **[T1]**
64. As an API user, I want a provider failure during a save to return a clear "bad gateway" error with a friendly message, so that my script can tell the provider is at fault and not my request. **[T1]**
65. As an API user, I want to read one library entry and update its notes, rating and status, so that I can manage my library from scripts. **[T1]**
66. As an API user, I want to delete a library entry, with documentation saying it's also removed from my packs, so that the result is never a surprise. **[T1]**
67. As an API user, I want to sign requests with my API token, or use my browser session, so that I can call the API from scripts or from the site. **[T1]**
68. As an API user, I want requests without sign-in to be refused and other users' entries to return "not found", so that the API follows the same rules as the website. **[T1]**
69. As an API user, I want to list public packs plus my own, with an option to list only mine, so that I can find packs to export. **[T1]**
70. As an API user, I want to read a pack and fetch its export, but not create or edit packs, so that pack editing stays on the website. **[T1]**
71. As anyone reading a public pack through the API, I want to see only pack and asset data, never the owner's notes, rating or status, so that the API can't leak private data. **[T1]**

### Look and feel

72. As a member, I want the site laid out like the Axcenity editor (a title bar, an activity bar, a collapsible side panel, and a status bar), so that it feels part of the same toolset. **[T1]**
73. As a member, I want the status bar to show each provider's status and my saved count, so that I can see at a glance whether search will work. **[T1]**
74. As a member, I want the interface in black, white and grey with colour used only for asset type, so that colour always tells me something. **[T1]**
75. As a member, I want the engine's wordmark, icon tile, favicon and fonts used throughout, so that the Toolbox is clearly the engine's companion site. **[T1]**
76. As a member, I want the logo kept off provider thumbnails, so that nobody thinks the Toolbox made or endorses those assets. **[T1]**
77. As a member, I want polished motion (logo wipe-in and shine, a logo loader instead of spinners, a cursor spotlight on cards, cards that blur in, and smooth transitions when content swaps), so that the site feels modern. **[T2]**
78. As a member, I want a right-edge scroll ruler with a section index on the main page and Discover, so that I can jump between sections. **[T2]**
79. As someone sensitive to motion, I want animations turned off when my system asks for reduced motion, so that the site is comfortable to use. **[T2]**

### Maintainer and grader

80. As a grader, I want one command that loads demo users, ~40 real assets across all four types, about 6 themed public packs, and library entries with varied statuses and ratings, offline and safe to run repeatedly, so that I can try every feature without live APIs. **[T1]**
81. As a grader, I want the README to explain setup, running, testing and the demo sign-in details, so that I can check the project quickly. **[T1]**
82. As a maintainer, I want the test suite to make no live API calls, so that tests are fast and pass offline. **[T1]**
83. As a maintainer, I want tests that fake each provider failure (timeout, connection error, rate limit, a server error with an HTML body, not found, and no matches), so that every error message is proven to work. **[T1]**
84. As a maintainer, I want tests that prove the access rules on both the website and the API, so that privacy can't silently break. **[T1]**
85. As a maintainer, I want the code linted and formatted by Ruff, so that it stays consistent. **[T1]**
86. As a maintainer, I want the existing console script to keep working unchanged, so that the earlier deliverable isn't broken. **[T1]**

### Requirement traceability

| Graded requirement | User stories |
|---|---|
| Stack: Django, DRF, SQLite, uv, Ruff, Tailwind + DaisyUI, HTMX, Pytest | 24, 28, 42 (HTMX); 61–71 (DRF); 72–75 (Tailwind + DaisyUI); 82–85 (Pytest, Ruff); Tooling decisions below (uv, SQLite) |
| One cohesive purpose | Problem Statement and Solution; 34–60 tie Discover, Library and Packs together |
| Users find items through an external API | 7–17 |
| Saved items survive the API being down | 13, 18, 62 |
| Users add and edit their own info | 26–28, 34–43, 65 |
| Browse saved items with search, filter, sort and pagination on local data | 19–24, 61 (also 50 for the public gallery) |
| Sign-in required; access rules on both site and API | 1–6, 44, 52, 67–71, 84 |
| The app's own API lists, creates, updates and deletes saved entries | 61–66 |
| Useful messages when the provider fails | 11, 17, 64, 83 |

## Implementation Decisions

### Apps and responsibilities

- **config:** project settings and root URLs.
- **providers** (existing package): provider clients. Gains the new record
  functions described below.
- **catalog:** the Asset, Tag and SavedAsset models, Discover, the library
  pages and the library API.
- **packs:** the Pack and PackItem models, the public gallery, the pack
  builder, suggestions, copying, export and the pack API.
- **accounts:** sign-up, sign-in and sign-out, the profile and the API
  token page.
- Shared templates: one base layout plus partials for HTMX fragments.
  Shared static files hold the branding, fonts and styles.
- Tests live in one top-level test folder with one shared conftest.

### Data model

- **Asset:** a shared cache of provider data, unique on
  (provider, external_id).
  - Fields: kind (texture, hdri, model or sound), title, author, thumbnail
    URL, tags (many-to-many to Tag), license, license URL, attribution,
    source URL, and fetched_at.
  - `variants` is a JSON list. Each variant has a label, a list of files
    (URL, filename, size) and a total size.
  - It's created by calling `fetch_record()` when an asset is first saved
    by anyone, and reused afterwards.
  - Users never delete Asset rows.
- **SavedAsset:** links a user to an Asset.
  - Fields: notes, rating (optional, 1–5), status (To review by default,
    Testing, Approved, Rejected), and a saved timestamp for sorting.
  - Unique per (user, asset).
- **Pack:** owner, title, slug, description ("intended use"), tags
  (many-to-many to Tag), `is_public` (default False), `copied_from` (a
  nullable link to the original Pack), and created/updated timestamps.
- **PackItem:** links a Pack to one of the owner's SavedAssets.
  - Fields: `preferred_variant`, `import_path`, `position`.
  - Variant and import path live here, not on SavedAsset, so the same
    asset can differ per pack and private fields can never leak through a
    pack.
  - The default variant is a 2K JPG (or MP3 for sounds) when one exists,
    otherwise the first listed variant.
- **Tag:** a unique, normalized name. Every tag, from providers or from
  pack owners, passes through `normalize_tag()`, which:
  - lowercases, trims and collapses whitespace
  - drops tags that are only numbers
  - strips a simple plural "s", except for words ending in "ss"
- **Shared and per-user records:** Asset is shared by all users, while
  SavedAsset belongs to one user.
  - Asset records are reused for every user. The first save by anyone
    creates the row, and every later save, by any user, reuses it.
  - SavedAsset records are unique per (user, asset).
  - Deleting a SavedAsset must never delete the shared Asset.
  - A PackItem can only point to a SavedAsset owned by the pack's owner.
- **Deleting a SavedAsset** cascades to its PackItems. There's no soft
  delete.
- **Thumbnails:** only the provider's URL is stored, and pages link to it
  directly. Thumbnails are never downloaded or copied, because Poly
  Haven's renders aren't CC0.

### Providers

- Each provider module gains an `AssetRecord` dataclass,
  `search_records(query, kind, limit=12)` and `fetch_record(external_id)`.
  These sit next to the existing `search()` and `get_details()`, which
  stay unchanged so the console script keeps working.
- Type-to-provider mapping:

  | Type | Providers | ambientCG filter | Poly Haven filter |
  |---|---|---|---|
  | Textures | ambientCG + Poly Haven | `material` | `textures` |
  | HDRIs | ambientCG + Poly Haven | `hdri` | `hdris` |
  | Models | ambientCG + Poly Haven | `3d-model` | `models` |
  | Sounds | Openverse Audio | — | — |

- Poly Haven's new code must keep the file download URLs that the current
  details function throws away.
- Every request still goes through the shared `get_json()` helper. Every
  failure surfaces as a `ProviderError` with a message that's safe to show
  users.
- Uneven result counts are normal (ambientCG returned one model for
  "wood"). The UI shows what each provider returns.
- **Caching** uses Django's local-memory cache:
  - successful search results per (provider, kind, normalized query) for
    1 hour
  - Poly Haven asset info for 12 hours
  - failures are never cached, so Retry always makes a fresh request

### Pages and interactions

- **Discover**
  - Four type tiles plus a command-bar search; `/` focuses it.
  - Each provider shelf is its own HTMX request fired on page load.
  - A failed shelf shows a DaisyUI alert with the `ProviderError` message
    and a Retry button that re-requests only that shelf.
  - 12 results per provider, with no paging.
  - "Save to library" swaps itself for an "In library" badge. Results
    already in the user's library render as "In library".
- **Library**
  - A private card grid, with its filters in the collapsible side panel.
  - One shared `filter_library(user, params)` function handles search
    (title, tags, notes), filters (type, provider, status, minimum
    rating), sorts (newest saved by default, oldest, title A–Z, rating
    high to low) and pagination (12 per page). The page and the API both
    use it.
  - HTMX swaps the results, and `hx-push-url` keeps every view
    bookmarkable.
  - **Drawer:** a slide-over at `/library/<id>/`.
    - Status and stars save immediately; notes save after a debounce.
    - It lists the packs the asset is in, and has Delete.
    - When the request isn't from HTMX (checked through `request.htmx`),
      the same view returns a full page.
    - The card behind the drawer updates through out-of-band swaps.
  - **Delete:** an HTMX confirm dialog lists the packs the item will be
    removed from.
  - **Add to pack:** each card has a dropdown that calls the shared
    `add_to_pack(pack, saved_asset)` function.
- **Pack builder** (owner only)
  - Pack details: title, description, comma-separated tags, and the
    public/private switch.
  - Each item has a variant dropdown, an import path field and Remove.
    Each control saves on change through HTMX.
  - "Add from my library" searches as you type and calls `add_to_pack()`.
  - **[T2] Suggested for this pack:** local Assets ranked by tag overlap
    (an annotated count of shared tags), excluding assets already in the
    pack. Adding one that isn't in the library first creates a SavedAsset
    with status To review.
  - **[T2] Find more from providers:** opens Discover with a search built
    from the pack's tags.
- **Public pack page**
  - Readable and exportable by anyone, including signed-out visitors.
  - Shows only PackItem and Asset data.
  - **[T2] Save single items:** signed-in members can save one item to
    their library.
  - **[T2] Copy pack** (website only), in one database transaction:
    - creates a private pack titled "<original title> (copy)" with
      `copied_from` set
    - adds missing assets to the copier's library as To review
    - leaves existing SavedAssets untouched
    - copies each item's variant and import path
- **Main page** (`/`)
  - **[T2] Orbit hero:** about 18 random thumbnails from assets in public
    packs, on orbit rings coloured by type. Each one links to its pack.
    With fewer than 6 such assets, type-icon tiles show instead.
  - Signed-out visitors also see the four steps and the Sign up and Sign
    in buttons.
  - **Public gallery:** served by `filter_public_packs()`.
    - search by title and tags
    - filter to packs containing a type
    - sort by newest or most items
    - 12 per page
    - each card has a cover mosaic (the first 4 thumbnails), title, owner,
      tags and a count by type
  - The side panel starts collapsed on this page.

### Authentication

- Django's built-in `LoginView` and `LogoutView`, plus a sign-up page
  built on `UserCreationForm`.
- DRF uses `SessionAuthentication` and `TokenAuthentication` (the
  `rest_framework.authtoken` app).
- The profile has an API token page where the member can see their token.
- **CSRF:**
  - Website forms, and the HTMX requests the pages send, use Django's CSRF
    protection.
  - API write requests (POST, PUT, PATCH, DELETE) that use a browser
    session must pass CSRF validation.
  - API requests that use a token send it in the `Authorization: Token
    <key>` header instead, and don't need a CSRF token.

### API

| Method and URL | Who | Behaviour |
|---|---|---|
| `GET /api/library/` | owner | Lists the caller's entries through `filter_library`, with the same parameters and pagination as the page. |
| `POST /api/library/` | member | Body: provider, external_id, plus optional notes, rating, status. Reuses the local Asset or calls `fetch_record()`. |
| `GET / PATCH / PUT /api/library/{id}/` | owner | Reads or updates notes, rating, status. |
| `DELETE /api/library/{id}/` | owner | Deletes the entry, which also removes it from the owner's packs (documented). |
| `GET /api/packs/` | anyone | Lists public packs, plus the caller's own packs when signed in. `?mine=1` lists only the caller's. |
| `GET /api/packs/{id}/` | anyone for public packs; owner for private | Read-only pack detail. |
| `GET /api/packs/{id}/export/` | anyone for public packs; owner for private | The export manifest. |

- **Create errors:**
  - A `ProviderError` returns **502** with
    `{"detail": <friendly message>}`.
  - A duplicate returns **400** with "Already in your library."
- Packs can't be created, edited or deleted through the API, and copying a
  pack is website-only.
- Separate serializers:
  - **Owner serializer** for library entries: includes notes, rating and
    status.
  - **Public serializer** for packs and exports: PackItem and Asset fields
    only.

### Acceptance criteria: access rules

These rules apply to the website **and** the API, and each one has a test.

| Action | Signed-out visitor | Another member | Owner |
|---|---|---|---|
| View or change a library entry | Website: sent to sign in. API: refused (401/403). | **404** | Allowed |
| List the library | Website: sent to sign in. API: refused. | Sees only their own | Sees only their own |
| View or export a **private** pack | **404** | **404** | Allowed |
| View or export a **public** pack | Allowed | Allowed | Allowed |
| Edit a pack, or open its builder | Sent to sign in | **404** | Allowed |
| Save an item from, or copy, a public pack | Sent to sign in | Allowed | Allowed |
| Create or edit packs through the API | Not available | Not available | Not available |

- No public view, public serializer or export ever includes a
  SavedAsset's notes, rating or status.
- A member can only add their own SavedAssets to their own packs.

### Acceptance criteria: export manifest

The shape is agreed as **Option A, verbatim**. A golden-file test locks it,
so any change to the shape fails the tests.

**Top-level fields**

| Field | Value |
|---|---|
| `format` | Always `"axcenity-pack"` |
| `version` | Always `1` |
| `exported_at` | When the export was generated (ISO 8601 timestamp) |
| `pack` | An object: `title`, `slug`, `author` (the owner's username), `description`, `tags`, `source_url` (the pack's page on the Toolbox) |
| `items` | A list, one entry per PackItem, in `position` order |
| `credits` | The attribution text of every item whose license isn't CC0 |

**Each item**

| Field | Value |
|---|---|
| `name` | The asset's title |
| `kind` | texture, hdri, model or sound |
| `provider`, `external_id` | Where the asset came from |
| `variant` | The chosen variant's label |
| `files` | The chosen variant's files, each with `url`, `filename`, `size` |
| `total_size` | The chosen variant's total size |
| `license`, `license_url` | The asset's license |
| `author`, `attribution` | Credit details |
| `source_url` | The asset's page on the provider's site |
| `import_path` | The owner's path, or `<kind>s/<external_id>/` when blank |

### Visual design

- **Shell** (based on the VSCode-style editor):
  - a title bar with the wordmark and "TOOLBOX"
  - an activity bar with the app icon tile (Home) at the top, then
    Discover, Library, Packs, Account and Settings
  - a collapsible side panel
  - a monochrome status bar showing provider status and the saved count
- **Colour:** the chrome is monochrome, and primary buttons are white with
  dark text. Colour only ever means asset type: textures `#F2A15A`, HDRIs
  `#6C8CFF`, models `#4CC38A`, sounds `#A48AFF` (four of the editor's
  accents).
- **Palette:** a custom DaisyUI theme named `axcenity`, taken from the
  editor's dark theme: app `#171717`, panel `#1E1E1E`, surface `#242424`,
  border `#303030`, text `#E8E8EA`.
- **Fonts:**
  - Plus Jakarta Sans ExtraBold for headings. It's a best guess at the
    wordmark's font, set in one display-font CSS variable so it's easy to
    swap.
  - Inter for body text.
  - JetBrains Mono for uppercase micro-labels.
- **Branding:**
  - **[T1]** The logo files are copied from the engine's branding assets.
    Static uses: the wordmark in the title bar, the icon tile, the favicon
    (the 32 px PNG), the "In library" badge mark, a ghost mark for empty
    states, and a giant cropped wordmark in the footer.
  - **[T2]** The wordmark wipes in and gets a periodic shine sweep, the
    tile cuts in on load, a giant parallax watermark sits behind the
    content, and the mark with a light sweep is the loader instead of
    spinners.
  - The logo is never placed on provider thumbnails.
- **[T2] Motion:**
  - a cursor spotlight on cards and tiles
  - staggered blur-up entry for cards
  - View Transitions on HTMX swaps
  - a right-edge scroll ruler plus a section index on the main page and
    Discover
  - all done in CSS plus a little plain JavaScript, with
    `prefers-reduced-motion` respected
- **Inspiration:** getartcraft.com supplies patterns (orbiting thumbnails,
  the right-edge ruler, mono micro-labels). The design stays its own and
  copies nothing directly.

### Tooling

- **uv only** (no pip or Node). SQLite is the database.
- **Dependencies:** django, djangorestframework, django-tailwind-cli (the
  standalone Tailwind CLI with DaisyUI), django-htmx.
- **Dev dependencies:** ruff (lint and format, configured in the project
  file), pytest, pytest-django, responses, pytest-cov.

### Testing

- **Provider failure tests (story 83)** cover three levels:
  - **Provider client tests** use `responses` to fake each failure and
    check that it gives a friendly `ProviderError`:
    - a timeout
    - a connection error
    - a 429
    - Openverse's 500 with an HTML body
    - Poly Haven's 404
    - `keywordMatches == 0`, which counts as no results, not an error
  - **Application tests** replace `search_records` and `fetch_record`
    with `monkeypatch`. They check that each failure message reaches the
    page or the API unchanged.
  - **HTMX shelf tests** make one provider fail while the other succeeds
    on the same search. The failed shelf shows its alert and Retry, and
    the other shelf still shows its results.
- A fixture clears the cache before each test.
- No test makes a live API call.
- Required test areas:
  - `normalize_tag`
  - `filter_library` and `filter_public_packs`
  - `add_to_pack`
  - delete cascades
  - the access-rules table, on the site and the API
  - API status codes (400, 502, 404)
  - the manifest golden file
  - **[T2]** copy pack, including its transaction
  - **[T2]** suggestion ranking

### Demo data

- A management command, `seed_demo`, loads a committed snapshot of about
  40 real assets across the four types. A one-time capture script produced
  the snapshot.
- It creates 3 demo users, about 6 themed public packs (for example
  "Medieval Village", "Sci-fi Corridor", "Forest Ambience"), and library
  entries with varied statuses and ratings.
- It's safe to run repeatedly and works offline.
- The demo credentials are documented in the README. They're obviously
  demo values, not real-looking secrets.

### Build order

1. **Tier 1, essential:**
   1. Scaffold plus the branded base layout (palette, fonts, logos, no
      motion yet)
   2. Providers: `AssetRecord` plus error tests
   3. Models plus `normalize_tag`
   4. Accounts and the token page
   5. Discover: provider shelves and error handling
   6. Discover: caching and status reporting
   7. Library filters, drawer and delete
   8. API plus permission tests
   9. Packs: builder, "Add to pack", public/private, export
   10. Main-page gallery plus `seed_demo` and README (the final Tier 1
       milestone)
2. **Tier 2, signature:**
   1. Suggestions plus "Find more from providers"
   2. Copy pack and per-item save
   3. Orbit hero plus scroll ruler
   4. Branding motion
3. **Tier 3, stretch:** see Out of Scope.

## Out of Scope

- **Tier 3 stretch items:** a "Popular assets" row, "Load more" on
  Discover, a light theme, and a sample Rust or Lua manifest loader in the
  docs. They're built only if Tier 1 and Tier 2 are finished.
- Downloading, hosting or proxying asset files or thumbnails. The Toolbox
  stores and links to provider URLs only.
- Creating, editing, deleting or copying packs through the API.
- Users deleting shared Asset records, and soft delete or undo for
  anything.
- Providers beyond ambientCG, Poly Haven and Openverse (for example
  Freesound, Sketchfab or Wikimedia Commons), and any provider that needs
  an API key.
- Paging inside Discover shelves.
- Several people editing one pack, and comments, likes or following.
- Password reset, email verification and social sign-in.
- Production deployment and hosting.
- Any change to how the existing console script behaves.
- The engine-side loader itself (apart from the Tier 3 sample).

## Further Notes

- **Defaults where the design was silent.** The agent picked these to fill
  gaps in the design; confirm them during review.
  - Discover's search is open to signed-out visitors, but "Save to library"
    asks them to sign in.
  - Pack owners can delete their packs (story 37).
  - Private packs return 404 to everyone but the owner, matching the
    library rule.
  - When no 2K JPG or MP3 exists, the default variant is the first one
    listed.
  - A signed-out API request is refused with DRF's default status for the
    configured authentication (401 or 403).
- **Provider quirks to plan around:**
  - Openverse is sometimes slow (30–60 s uncached) and returns 500 HTML
    pages, so its 10 s timeout and error message will be seen in real
    use.
  - Poly Haven's semantic search never comes back empty; zero
    `keywordMatches` means no results.
  - Poly Haven requires an identifying User-Agent. The current one names
    the console script, and it could be renamed for the Toolbox.
- **django-tailwind-cli:** check its current docs for how to enable
  DaisyUI before scaffolding; the setting has changed between versions.
- **Branding sources:** the logos, fonts and palette come from the
  Axcenity engine repository. Its branding README says the identity is
  black, white and grey only, which is why the chrome is monochrome.
- **Next step:** after review, `/prd-to-plan` turns this PRD into a plan
  with the same name, with phases that follow the tiers.
