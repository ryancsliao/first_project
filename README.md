# pokedeal

Finds Pokemon card listings on eBay that are priced meaningfully below their
TCGPlayer market price.

It does **not** scrape eBay or TCGPlayer. It uses:

- [eBay's Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html)
  (official, read-only, application-level access) to search active listings.
- [pokemontcg.io](https://pokemontcg.io/) (a free, open Pokemon TCG database
  that mirrors TCGPlayer's published market prices per card/print) as the
  price baseline.

For each card on your watchlist, it fetches the TCGPlayer market price,
searches eBay for matching listings, filters out listings that would make
the comparison meaningless (graded cards, lots/bundles, proxies/customs,
digital codes), and reports any listing priced far enough below market to be
worth a look.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 1. eBay API credentials (required)

1. Create a free account at https://developer.ebay.com/ and create an
   application ("Create an App Key").
2. Grab the **Production** "Client ID" and "Client Secret" (App ID / Cert
   ID). No user login/OAuth consent flow is needed — this app only needs an
   *application* access token (client-credentials grant) to read public
   listing data.
3. Copy `.env.example` to `.env` and fill in `EBAY_CLIENT_ID` /
   `EBAY_CLIENT_SECRET`.

If you'd rather test against eBay's sandbox (fake data) before touching
production, set `EBAY_ENV=SANDBOX` and use your sandbox keys instead.

### 2. pokemontcg.io API key (optional but recommended)

Works without a key, but a free key from https://pokemontcg.io/ raises the
rate limit substantially. Add it as `POKEMONTCG_API_KEY` in `.env`.

### 3. Build your watchlist

```bash
cp watchlist.example.yaml watchlist.yaml
```

Edit `watchlist.yaml` with the cards you want to track. See the comments in
that file for all the fields (set, number, variant/finish, per-card discount
override, etc).

## Usage

```bash
# look up a card's current TCGPlayer market price (sanity-checks your
# pokemontcg.io setup, doesn't touch eBay or need eBay credentials)
pokedeal lookup "Charizard" --set "Base Set" --number 4

# scan your whole watchlist for listings at least 20% (default) below market
pokedeal scan --watchlist watchlist.yaml

# custom threshold + save results to CSV
pokedeal scan --watchlist watchlist.yaml --min-discount 30 --csv deals.csv
```

Without installing the package you can also run it as a module:
`python -m pokedeal.cli scan`.

## How "underpriced" is decided

For each watchlist entry:

1. Resolve the card via pokemontcg.io (`name` + optional `set` + `number`),
   and pick its TCGPlayer market price for the requested `variant` (finish),
   or the most common finish available if you didn't specify one.
2. Search eBay (Browse API) for `"<name> <set>"` (or your custom `query`),
   scoped to the Pokemon Individual Cards category by default.
3. Drop listings that look graded (PSA/BGS/CGC/etc + a grade), a
   lot/bundle/binder, or not a real single card (proxy, custom, digital
   code) — these would make a straight price comparison meaningless.
4. Compute `discount% = (market_price - (listing_price + shipping)) / market_price * 100`.
5. Keep listings at or above your `--min-discount` threshold (default 20%,
   overridable per-card in the watchlist).

## Known limitations

- **Matching is query-based, not exact.** eBay titles are free text; this
  tool relies on a reasonably targeted search query plus the exclusion
  filters above, not full NLP matching. Spot-check results before buying.
- **Shipping cost isn't always available** from the search endpoint; when
  eBay doesn't return it, total price falls back to item price alone and the
  table/CSV flags the row as a shipping estimate.
- **USD listings only** for now (a straight price comparison across
  currencies needs an FX conversion step this doesn't do yet).
- **Single page of results per card** (up to `max_results`, eBay's per-call
  max is 200) — no pagination loop yet.
- The eBay category ID (`EBAY_CATEGORY_ID` in `.env`) defaults to "Pokemon
  Individual Cards" (183454) on the US site; adjust if you're searching a
  different marketplace/category.

## Tests

```bash
pip install -e . pytest
pytest
```

All tests run against fake HTTP clients — no network access or API keys
needed.
