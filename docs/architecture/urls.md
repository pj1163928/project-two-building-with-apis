# URLs

Every route, who may use it, and what an HTMX request gets back.
`config/urls.py` mounts `accounts.urls` at `/accounts/` and `catalog.urls`
and `packs.urls` at the root. Every write is POST with CSRF.

## Path conventions

- The owner's pack pages use the pk (`/packs/<id>/edit/`); a pack's own
  page uses its slug (`/packs/<slug>/`), unique site-wide and never changed
  by a rename.
- `new`, `picker` and `link` are pages under `/packs/`, so no pack gets
  those slugs (`RESERVED_SLUGS`; a pack titled "New" is `new-2`).
- An unlisted pack is read only through `/packs/link/<token>/…`. Its
  replies carry `X-Robots-Tag: noindex, nofollow`.

## catalog

| Name | Path | Access |
|---|---|---|
| `catalog:discover` | `/discover/?type=&q=&license=&commercial=1` | Everyone. `license` repeats; both filters optional |
| `catalog:discover_shelf` | `/discover/<kind>/<provider>/?q=&page=&license=&commercial=` | Everyone. HTMX fragment; `page` 1 to 20 |
| `catalog:discover_asset` | `/discover/asset/<provider>/<external_id>/` | Everyone. Drawer for HTMX, page otherwise; never writes |
| `catalog:library` | `/library/?q=&type=&provider=&status=&tag=&min_rating=&sort=&page=` | Members. Controls' HTMX gets the results fragment |
| `catalog:save` | `/library/save/` | Members; POST. HTMX fragment |
| `catalog:entry` | `/library/<id>/` | Own entries only (**404** otherwise). Library's HTMX gets the drawer, anything else the page |
| `catalog:update` | `/library/<id>/update/` | Own entries only; POST. Saves whichever of `status`, `rating`, `notes`, `status_reason` is posted |
| `catalog:remove` | `/library/<id>/remove/` | Own entries only. GET is the confirm (dialog for HTMX, page otherwise); POST removes (HTMX gets the results fragment) |
| `catalog:api_library` | `/api/library/` | API, token or session (**401** otherwise). GET lists, POST saves |
| `catalog:api_entry` | `/api/library/<id>/` | API, own entries only. GET, PATCH, PUT, DELETE |

## packs: member pages (owner only, **404** otherwise)

| Name | Path | Access |
|---|---|---|
| `packs:list` | `/packs/?layout=grid\|list` | Members: their own packs; `layout` remembered in the session |
| `packs:create` | `/packs/new/` | Members; POST creates a private pack and opens its builder |
| `packs:builder` | `/packs/<id>/edit/` | Owner |
| `packs:details`, `packs:visibility`, `packs:delete` | `/packs/<id>/details/`, `…/visibility/`, `…/delete/` | Owner; POST. Details saves whichever of `title`, `description`, `tags` is posted; visibility takes `private`, `unlisted`, `public` |
| `packs:library_search` | `/packs/<id>/library/?q=` | Owner; Add from my library fragment (other requests go to the builder) |
| `packs:add_item` | `/packs/<id>/items/` | Owner; POST `entry` (their own, **404** otherwise) |
| `packs:suggestions` | `/packs/<id>/suggestions/` | Owner; Suggested for this pack fragment |
| `packs:suggestion_add` | `/packs/<id>/suggestions/add/` | Owner; POST `asset` (a stored Asset id, **404** when unknown). Never calls a provider |
| `packs:item_update`, `packs:item_move`, `packs:item_remove` | `/packs/<id>/items/<item>/`, `…/move/`, `…/remove/` | Owner; POST. Update saves `preferred_variant` or `import_path`; move takes `direction` `up`/`down` |
| `packs:items_reorder`, `packs:items_sort` | `/packs/<id>/items/order/`, `…/items/sort/` | Owner; POST. `order` is every item id once, comma-separated (anything else **400**, nothing changed); sort takes `type`, `title`, `provider`, `license` |
| `packs:rotate_link` | `/packs/<id>/link/` | Owner; POST. New share token; every older link is a **404** |
| `packs:picker` | `/packs/picker/?entry=<id>` or `?provider=&external_id=` | Members; Add to pack list of their own packs |
| `packs:picker_add` | `/packs/<id>/add/` | Owner; POST `entry`, or `provider` and `external_id` |

## packs: readers

"As `packs:public`" means: everyone for a public pack, the owner only for
a private or unlisted one, **404** otherwise. "As `packs:shared`" means:
anyone holding an unlisted pack's link; a public pack's link redirects to
its page; a replaced, private or unknown token is a **404**.

| Name | Path | Access |
|---|---|---|
| `packs:home` | `/?q=&type=&sort=&page=` | Everyone: main page and public gallery. Gallery HTMX gets the results fragment |
| `packs:public` | `/packs/<slug>/` | As above. Read-only; the owner also gets Edit in builder |
| `packs:export` | `/packs/<slug>/export/` | As `packs:public`. GET: `<slug>.axcenity-pack.json` download |
| `packs:shared`, `packs:shared_export` | `/packs/link/<token>/`, `…/export/` | As `packs:shared` |
| `packs:files`, `packs:shared_files` | `/packs/<slug>/files/`, `/packs/link/<token>/files/` | As `packs:public` / `packs:shared`. GET: the JSON list Download files zips (`?item=<id>`; another pack's item **404**) |
| `packs:save_item`, `packs:shared_save_item` | `/packs/<slug>/items/<item>/save/`, `/packs/link/<token>/items/<item>/save/` | Members who can read the pack (visitors go to sign-in and back); POST. HTMX gets the item's "In your library" slot |
| `packs:copy`, `packs:shared_copy` | `/packs/<slug>/copy/`, `/packs/link/<token>/copy/` | As `packs:save_item`. Private copy, then its builder. Website only |
| `packs:attribution` | `/attribution/` | Everyone: the license guide |
| `packs:attribution_packs` | `/attribution/packs/` | Members: their own packs' licenses |
| `packs:attribution_pack`, `packs:shared_attribution` | `/attribution/packs/<slug>/`, `/packs/link/<token>/attribution/` | As `packs:public` / `packs:shared` |
| `packs:attribution_assets` | `/attribution/assets/?q=&license=&credit=&page=` | Members: own library by license; `license` repeats (a `LICENSES` key), `credit` is `required`/`listed`/`optional`; unknown values ignored |
| `packs:attribution_asset` | `/attribution/assets/<id>/` | Own entries only |
| `packs:api_packs` | `/api/packs/?mine=&page=` | API, anyone: public plus the caller's own, 12 a page. `?mine=1` needs sign-in (**401**). Writes **405** |
| `packs:api_pack`, `packs:api_pack_export` | `/api/packs/<id>/`, `…/export/` | API: anyone for public, owner for private (**404** otherwise). Writes **405** |

## accounts

| Name | Path | Access |
|---|---|---|
| `accounts:signup` | `/accounts/signup/` | Everyone (members are sent home) |
| `accounts:login` | `/accounts/login/` | Everyone |
| `accounts:logout` | `/accounts/logout/` | POST only |
| `accounts:profile`, `accounts:settings` | `/accounts/profile/`, `/accounts/settings/` | Members |
| `accounts:theme` | `/accounts/theme/` | Everyone; POST `choice` (`system`, `light`, `dark`, **400** otherwise) into the `ax-theme` cookie for a year. HTMX gets 204; others go back to a same-site Referer, else home |
| `accounts:download_preferences` | `/accounts/settings/downloads/` | Members; POST whichever download defaults are posted (HTMX gets the status line) |
| `accounts:token` | `/accounts/token/` | Members; creates the token on first visit; never cached |
| `accounts:rotate_token` | `/accounts/token/rotate/` | Members; POST. `rotate_token()`; the old key is a **401** at once; back to the token page with a one-time message |
