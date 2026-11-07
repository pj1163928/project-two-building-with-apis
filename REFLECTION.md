# Reflection

## 1. My research decisions

I chose three API providers that I thought were useful and necessary in
their own right: ambientCG, Poly Haven and Openverse.

Overall, ambientCG and Poly Haven were no-brainers to me, as they are free,
need no API key, and are all CC0 (public domain), meaning all assets can be
used in whatever way.

Where I knew it was going to get complicated was with audio. The two
providers that Claude recommended to me were Openverse and Freesound.
Openverse did not require an API key, while Freesound needed a free account
and an API key. Openverse also allowed more anonymous use than Freesound,
and featured a wider array of media beyond sound that can be used later.

All providers were chosen for their ease of use and availability, as well
as for not needing an API key or credentials, which makes site security
much less of a hassle.

## 2. Prototype decisions

One of the only prototype decisions I really made was deciding how to
display the assets. Claude had made three primary layouts: gallery shelves,
search previews and split editor. I preferred the gallery shelves, as they
seemed to make the most sense for all device types.

This decision is probably the most influential, as Claude made many of the
design decisions from this UI decision. The Discover, Home, Library and
Packs pages all use this layout to display content.

## 3. Tracing an API update

A user sends a `PATCH` request, and Django routes it through
[config/urls.py](config/urls.py) and [catalog/urls.py](catalog/urls.py) to
`LibraryEntryAPI` ([catalog/api.py:94-118](catalog/api.py#L94-L118)). The
view then finds the requested library entry, and the serializer,
`LibraryEntrySerializer`
([catalog/serializers.py:47-124](catalog/serializers.py#L47-L124)), checks
that the new information given is valid. If everything checks out, it saves
using `SavedAsset.save_review()`
([catalog/models.py:359-376](catalog/models.py#L359-L376)), which saves only
the changed fields, and returns `200 OK` with the updated information.

Django identifies each user through token or session authentication
([config/settings.py:104-111](config/settings.py#L104-L111)). Users must be
logged in, and can only update their own entries through
`SavedAssetQuerySet.for_user()`
([catalog/models.py:204-206](catalog/models.py#L204-L206)). Automated tests
in [tests/test_api_library.py](tests/test_api_library.py) verify that
updates work, invalid changes are rejected, and users cannot modify someone
else's entry.

## 4. Tracing and verifying data

In this case I will explain the library functionality. When the user opens
`/library/`, Django sends the request to `LibraryView`
([catalog/views.py:232-270](catalog/views.py#L232-L270)), which retrieves
their saved assets using `filter_library()`
([catalog/library.py:354-400](catalog/library.py#L354-L400)). The
application searches asset titles, notes and tags
([catalog/models.py:257-269](catalog/models.py#L257-L269)), and applies
filters for type, provider, status, tags and ratings
([catalog/library.py:384-393](catalog/library.py#L384-L393)). Users can only
see their own saved assets.

Results are sorted using `sorted_by()`
([catalog/models.py:303-307](catalog/models.py#L303-L307)) and divided into
pages using `Paginator` ([catalog/library.py:399](catalog/library.py#L399)).
Each page displays up to 12 assets. These examples demonstrate searching,
filtering, sorting and pagination, and how they all work together to
display the correct library entries.

## 5. AI pushback

One of my biggest concerns that I addressed with AI was its HTMX handling.
In the beginning of my project I had a top bar, which I liked and agreed on
with Claude. Claude, however, misread the PRD and plan structure and how it
should handle page navigation: when a button was clicked, it would
completely reload the page. This looked rather choppy and unprofessional,
and it took me some time to figure out. When I realized that it was not
properly using HTMX, I mentioned it to Claude and the issue was resolved.

I also had several issues with Claude's interpretation of collections and
the saving of assets. I had intended one true location, "Packs", for saving
assets. Claude took this as both collections and packs; to me this was
confusing and really added more layers to something I felt should be easy.

### Sources

- [PROMPTS.md lines 1660-1662](PROMPTS.md#L1660-L1662): my decision to
  change the collections and packs
- [PROMPTS.md lines 2503-2517](PROMPTS.md#L2503-L2517): troubleshooting and
  determining the cause of an HTMX issue
