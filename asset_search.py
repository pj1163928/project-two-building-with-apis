"""Search ambientCG, Poly Haven and Openverse Audio for game assets.

Run with:  uv run asset_search.py
"""

import sys

from providers import PROVIDERS, ProviderError, ambientcg, openverse, polyhaven
from providers.formatting import duration, human_size

TYPE_CHOICES = [
    ("Any", None),
    ("Textures/materials", "textures"),
    ("HDRIs", "hdris"),
    ("Models", "models"),
]


# ---------------------------------------------------------------- prompts


def ask(prompt):
    """input() that treats Ctrl+C / Ctrl+Z as a request to quit."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0) from None


def ask_nonblank(prompt):
    while not (answer := ask(prompt)):
        print("  Please type something.")
    return answer


def ask_number(prompt, count, allow_blank=False):
    """Ask for a number from 1 to count. Returns None on a blank answer if allowed."""
    while True:
        answer = ask(prompt)
        if not answer and allow_blank:
            return None
        if answer.isdecimal() and 1 <= int(answer) <= count:
            return int(answer)
        print(f"  Please enter a number from 1 to {count}.")


def choose_provider():
    print("\nProviders:")
    for number, provider in enumerate(PROVIDERS, start=1):
        print(f"  {number}) {provider.NAME}")
    print("  q) Quit")
    while True:
        answer = ask("Choose a provider: ").lower()
        if answer in ("q", "quit"):
            return None
        if answer.isdecimal() and 1 <= int(answer) <= len(PROVIDERS):
            return PROVIDERS[int(answer) - 1]
        print(f"  Please enter a number from 1 to {len(PROVIDERS)}, or q to quit.")


def choose_type():
    print("Asset type:")
    for number, (label, _) in enumerate(TYPE_CHOICES, start=1):
        print(f"  {number}) {label}")
    choice = ask_number("Choose a type [Enter = Any]: ", len(TYPE_CHOICES), allow_blank=True)
    return TYPE_CHOICES[choice - 1][1] if choice else None


def ask_yes_no(prompt):
    while True:
        answer = ask(prompt).lower()
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer y or n.")


# ---------------------------------------------------------------- output


def clip(text, width):
    text = str(text)
    return text if len(text) <= width else text[: width - 1] + "…"


def print_results(rows):
    columns = [("#", 2), ("Name", 34), ("Type", 10), ("Info", 36), ("License", 12)]
    table = [
        [str(n), clip(r["name"], 34), clip(r["type"], 10), clip(r["info"], 36), r["license"]]
        for n, r in enumerate(rows, start=1)
    ]
    widths = [
        max(len(title), *(len(row[i]) for row in table)) for i, (title, _) in enumerate(columns)
    ]
    print()
    print(
        "  ".join(title.ljust(w) for (title, _), w in zip(columns, widths, strict=False)).rstrip()
    )
    print("  ".join("-" * w for w in widths))
    for row in table:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=False)).rstrip())


def print_field(label, value):
    if value not in (None, "", [], {}):
        print(f"  {label + ':':<15} {value}")


def show_ambientcg(d):
    dims = d["dimensions"]
    print_field("Type", d["type"])
    print_field("Maps", ", ".join(d["maps"]))
    if dims:
        # ambientCG doesn't document the unit, so print the numbers as given.
        print_field(
            "Dimensions",
            f"{dims.get('width')} x {dims.get('height')} x {dims.get('depth')} (W x H x D)",
        )
    print_field("Tags", ", ".join(d["tags"]))
    print_field("License", d["license"])
    print_field("Page", d["url"])
    print(f"\n  Downloads ({len(d['downloads'])}):")
    for dl in d["downloads"]:
        print(
            f"    {dl.get('attributes', '?'):<16} .{dl.get('extension', '?'):<5} "
            f"{human_size(dl.get('size')):>10}  {dl.get('url')}"
        )


def show_polyhaven(d):
    authors = ", ".join(f"{name} ({role})" for name, role in d["authors"].items())
    print_field("Type", d["type"])
    print_field("Max resolution", d["max_resolution"])
    print_field("Physical size", d["physical_size"])
    print_field("Authors", authors)
    print_field("Categories", ", ".join(d["categories"]))
    print_field("Tags", ", ".join(d["tags"]))
    print_field(
        "Downloads", f"{d['download_count']:,}" if d["download_count"] is not None else None
    )
    print_field("Description", d["description"])
    print_field("License", d["license"])
    print_field("Page", d["url"])

    def by_resolution(keys):
        return sorted(keys, key=lambda res: int(res[:-1]), reverse=True)

    if d["maps"]:
        print("\n  Map files, total size per format:")
        for res in by_resolution(d["maps"]):
            formats = ", ".join(
                f"{fmt} {human_size(size)}" for fmt, size in sorted(d["maps"][res].items())
            )
            print(f"    {res:>4}  {formats}")
    if d["bundles"]:
        print("\n  Bundles (file plus included textures):")
        for kind, sizes in sorted(d["bundles"].items()):
            parts = ", ".join(f"{res} {human_size(sizes[res])}" for res in by_resolution(sizes))
            print(f"    {kind:<6} {parts}")


def show_openverse(d):
    bit_rate = f"{d['bit_rate'] // 1000} kbps" if d["bit_rate"] else "unknown"
    sample_rate = f"{d['sample_rate']:,} Hz" if d["sample_rate"] else "unknown"
    print_field("Creator", d["creator"])
    print_field("Source", d["source"])
    print_field("Duration", duration(d["duration_ms"]))
    print_field("Bit rate", bit_rate)
    print_field("Sample rate", sample_rate)
    print_field("File", f"{d['filetype'] or '?'}, {human_size(d['filesize'])}")
    print_field("License", f"{d['license']}  {d['license_url'] or ''}".strip())
    print_field("Attribution", d["attribution"])
    print_field("Audio URL", d["audio_url"])
    print_field("Page", d["url"])
    if d["alt_files"]:
        print("\n  Other formats:")
        for alt in d["alt_files"]:
            rate = f"{alt['sample_rate']:,} Hz" if alt.get("sample_rate") else ""
            print(
                f"    {alt.get('filetype', '?'):<5} {human_size(alt.get('filesize')):>10}  {rate:<10} {alt.get('url')}"
            )


DETAIL_PRINTERS = {ambientcg: show_ambientcg, polyhaven: show_polyhaven, openverse: show_openverse}


def show_details(provider, asset_id):
    print(f"\nFetching details for '{asset_id}' from {provider.NAME}...")
    details = provider.get_details(asset_id)
    print(f"\n{details['name']}  [{details['id']}]")
    DETAIL_PRINTERS[provider](details)


# ---------------------------------------------------------------- flow


def run_search(provider):
    print(f"\n{provider.NAME}: search by phrase, or look up one asset by ID.")
    while (mode := ask("Search (s) or ID lookup (i)? [Enter = s]: ").lower()) not in ("", "s", "i"):
        print("  Please enter s or i.")
    if mode == "i":
        show_details(provider, ask_nonblank("Asset ID: "))
        return

    query = ask_nonblank("Search phrase: ")
    asset_type = choose_type() if provider.TYPE_FILTERS else None

    print(f"\nSearching {provider.NAME} for '{query}'...")
    rows = provider.search(query, asset_type)
    if not rows:
        print(f"No {provider.NAME} matches for '{query}'. Try a different or broader phrase.")
        return

    print_results(rows)
    choice = ask_number(
        f"\nShow details for # (1-{len(rows)}) [Enter = skip]: ", len(rows), allow_blank=True
    )
    if choice:
        show_details(provider, rows[choice - 1]["id"])


def main():
    # Asset titles can hold characters a Windows code page can't print (e.g.
    # U+2011 in Poly Haven descriptions); show "?" instead of crashing.
    sys.stdout.reconfigure(errors="replace")
    print("Game asset search: ambientCG, Poly Haven and Openverse Audio")
    while True:
        provider = choose_provider()
        if provider is None:
            break
        try:
            run_search(provider)
        except ProviderError as error:
            print(f"\nError: {error}")
        if not ask_yes_no("\nSearch again? [Y/n]: "):
            break
    print("Goodbye.")


if __name__ == "__main__":
    main()
