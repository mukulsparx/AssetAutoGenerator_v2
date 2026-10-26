# A3 - Asset taxonomy and category rules for Asset Auto Generator v3

Author: research agent A3. Date: 2026-10-21. Scope: the product taxonomy of 8 retailers, about 100 leaf categories in 15 families, a mapping onto the current v2 `rules.toml`, a proposed v3 `rules.toml` skeleton, a fallback detection design, and the 15 categories most likely to ship "unexpected references".

Read-only inputs: v2 `rules.toml`, SPEC.md section 5 only, the app repo (`assetsAPI.js`, `assetClassification.js`, `assetWriteAPI.js`, `wallBinding.js`), the upserter (`upsert-core.cjs`), memory notes. Nothing under `G:\Shared drives` was modified. livingspaces.com was never fetched (search snippets and other sources only).

Confidence tags used throughout: **[H]** fetched or read from source this session; **[M]** search snippet, seller documentation or two agreeing sources; **[L]** general knowledge or a single third-party source; **[UNVERIFIED]** not checked, treat as a to-do.

---

## 0. TL;DR

1. **v2 covers about a third of what the retailers sell.** It has 18 categories. Chandeliers, pendants, sconces, ceiling fans, TVs, plants, vases, candles, curtains, bedding, baskets, mattresses, cribs, kids furniture, appliances, bath fixtures, pet and fitness items all fall to `other` (Smart Mesh, 2,500 quads, no postprocess). [H: emulated against about 130 probe titles]
2. **First-match substring routing mis-routes common titles.** Examples (all reproduced with a Python emulation of the v2 rules): "Sofa Table" goes to `sofa`; "Lamp Table" goes to `lamp`; "Cedar Blanket Chest" and "Blanket Ladder" go to `pillow`; an indoor "Daybed" goes to `outdoor_daybed`; "Headboard", "Bed Skirt", "Bed Tray" and "Dog Bed" go to `bed` (and get a mattress added); "Foot Stool" goes to `dining_chair`; "Console Table" goes to `cabinet` with `close_back`; any title containing "framed", "print", or "art deco" goes to the 6-quad `art` builder, including furniture; every desk goes to `dining_table`; "Kids Table and Chairs Set" goes to `accent_chair`. v3 needs head-noun routing (Section 5), not first substring.
3. **v3 shape: 100 leaves + `other`, in 15 families.** Each leaf carries `host`, `resizable`, `builder`, `views`, `scale`, `postprocess`, `family`, flags. Global defaults live in `[defaults]` and `[family.*]`, so a leaf only states its deviations.
4. **New builders are needed for the flat/hollow/soft long tail:** `box` (TV, appliance, mattress, book), `lathe` (vase, candle, bowl, planter, shade, round clock), `drape` (curtain, throw, bedding), `slab` (shelf, canvas, mirror glass, frame), `cushion` (pillow, bean bag, pet bed), `cross_cards` (faux stems), `hybrid` (Tripo body + procedural glass top / shade / mattress / cord / pot), `skip` (route to the fixtures library or a human).
5. **App-side facts that constrain the rules (all read from code):**
   - The app's own Add-products path (`buildAssetInput`) writes `is_resizable: false` for every product and writes the vendor hostname into `host`. The upserter instead passes `host` and `is_resizable`/`resizable` straight through from the sheet columns (`SYNONYMS`: `host`, `is_resizable`, `resizable`). So v3 can emit real `host` and `is_resizable` values, but only through the sheet.
   - There is no ceiling-host logic anywhere in `src` (grep found nothing). Ceiling lights are catalog categories with no placement behaviour. [H]
   - `isWallHangingData` falls back to a category-name heuristic whenever `host` does not contain "wall". A floor, leaner or tabletop mirror filed under "Mirrors" becomes a wall hanging and the 40 cm thickness guard cannot rescue it. "Wall Lighting" (99 rows) and "Wall Shelves" (127 rows) are not matched by the heuristic and need `host = wall-based` in the DB. [H, from function bodies; call sites not traced]
   - About 30 DB categories are not in `ALLOWED_CATEGORIES` and so never render in the catalog (hall trees, shoe storage, vanity stands, ovens, dishwashers, dryers, speakers, laptops, instruments, bath, outdoor accessories, "TV (50 and larger)", "Sets" handled separately). Leaves in those areas need an allow-list extension or filing under an allowed bucket. [H, snapshot may be stale]
6. **Top-15 categories that ship "unexpected references"** (lifestyle shots, multiple items, cut-outs): rugs, wall art and gallery sets, mirrors, curtains and blinds, bedding sets, pillows and throws, table/floor lamps and pendants, vases/bowls/candles/tabletop decor, plants and planters, bookcases and display cabinets (styled shelves), TVs and electronics, dining table and chair sets, beds and bedroom sets, sofas and sectionals, outdoor furniture. Triage is automatic (Section 6): filename tokens, aspect ratio, border-whiteness, foreground fill, connected-component count, OCR density, then one VLM enum question.
7. **Not verified, flagged where they matter:** IKEA `_pe`/`_ph` image suffix meaning; whether Jev / System One accepts image input; mattress-on-bed stacking, curtain/blind hosting and leaner-mirror tilt in the app; wall-item pivot convention; exact v2 breadcrumb handling; Wayfair imagery rules (third-party sources conflict).

---

## 1. Retailer taxonomy comparison

### 1.1 Department coverage (what each retailer sells)

Y = a department or clear sub-tree; p = partial; - = not seen. Confidence per column: IKEA, Article, West Elm navigation fetched [H]; Wayfair via seller docs and category pages [M]; Living Spaces, CORT, Temple & Webster, Crate & Barrel search snippets only [M/L].

| Canonical department | LS | WF | CORT | T&W | IKEA | WE | C&B | ART | Retailers selling it |
|---|---|---|---|---|---|---|---|---|---|
| Living seating (sofa, sectional, loveseat, recliner, accent chair, ottoman, chaise) | Y | Y | Y | Y | Y | Y | Y | Y | 8 |
| Living tables and media (coffee, side, console, TV stand) | Y | Y | Y | Y | Y | Y | Y | Y | 8 |
| Dining and bar (tables, chairs, stools, benches, buffets, bar carts) | Y | Y | Y | Y | Y | Y | Y | Y | 8 |
| Bedroom (bed, headboard, nightstand, dresser, chest, wardrobe) | Y | Y | Y | Y | Y | Y | Y | Y | 8 |
| Mattresses | Y | Y | p | Y | Y | Y | Y | p | 6-8 |
| Kids and nursery | Y | Y | - | Y | Y | Y | Y | p | 6-7 |
| Home office | Y | Y | Y | Y | Y | Y | Y | Y | 8 |
| Outdoor | Y | Y | p | Y | Y | Y | Y | Y | 7-8 |
| Lighting | Y | Y | p | Y | Y | Y | Y | Y | 7-8 |
| Rugs | Y | Y | p | Y | Y | Y | Y | Y | 7-8 |
| Decor (art, mirrors, vases, plants, candles, books, clocks, baskets) | Y | Y | p | Y | Y | Y | Y | Y | 7-8 |
| Textiles (curtains, bedding, throws, pillows) | p | Y | Y | Y | Y | Y | Y | p | 6-8 |
| Storage and organization | p | Y | p | Y | Y | Y | Y | p | 6-8 |
| Kitchen and bath fixtures | - | Y | - | Y | Y | Y | Y | - | 5 |
| Appliances and electronics | - | Y | p | p | Y | - | p | - | 2-5 |
| Pet | - | Y | - | Y | Y | p | p | p | 3-6 |
| Fitness | - | Y | - | p | - | - | - | - | 1-2 |

Reading: the first 13 rows are sold by nearly everyone, so those leaves are the priority. Kitchen/bath fixtures, appliances, pet and fitness are sold by a minority and are already partly covered by the app's fixtures library (about 40 items in `src/data/fixtureManifest.js`), so they are priority 3 (box builder, or skip).

### 1.2 IKEA category tree [H] (URL pattern `https://www.ikea.com/us/en/cat/<slug>-<id>/`, product title pattern "NAME, type, colour, dims")

| IKEA department | Sub-categories (slug-id) |
|---|---|
| Storage `st001` | dressers-storage-drawers-st004, bookcases-shelving-units-st002, display-storage-cabinets-st003, armoires-wardrobes-19053, tv-media-furniture-10475, sideboards-buffets-sofa-tables-30454, utility-storage-carts-fu005, room-dividers-46080, shoe-cabinets-10456, storage-cabinets-10385 |
| Sofas and armchairs `700640` | sofas-sectionals-fu003, sleeper-sofas-10663, armchairs-chaises-fu006, ottomans-20926, chaise-lounges-57527, sofa-modules-31786 |
| Beds and mattresses `bm001` | beds-bm003, mattresses-bm002, nightstands-20656, headboards-19064, bedding-tl004 |
| Tables and chairs `fu002` | tables-700675, chairs-700676, benches-700319, bar-furniture-16244, accent-tables-10705, kids-tables-18768, stools-22659, step-stools-20611, dining-chairs-25219, folding-chairs-25222, bar-stools-chairs-20864, cafe-chairs-19144, sofa-console-tables-16246, coffee-tables-10716 |
| Desks `fu004` | desks-computer-desks-20649, desk-chairs-20652, gaming-furniture-55002 |
| Lighting `li001` | lamps-light-fixtures-li002, decorative-lighting-14971, ceiling-fans-700600 |
| Rugs and textiles `tl001` | rugs-10653, decorative-pillows-cushion-covers-10659, blankets-throws-20528, outdoor-cushions-17893, chair-pads-20542 |
| Window `tl002` | curtains-10700, blinds-10701 |
| Decor `de001` | wall-decor-10757, mirrors-20489, plants-flowers-pp003, flower-pots-stands-pp004, home-fragrance-42926, candle-holders-candles-10760, vases-bowls-10769, storage-boxes-baskets-10550, clocks-10759, decorative-accessories-24924 |
| Outdoor `od001` | outdoor-patio-furniture-od003, outdoor-seating-700350, outdoor-dining-700351, chaises/hammocks-21963, outdoor-coffee-side-tables-700192, umbrellas-gazebos-17887, outdoor-rugs-34204 |
| Kitchen `ka001` | kitchen-islands-carts-10471, appliances-ka002 |
| Others | Bathroom `ba001`, Plants `pp001`, Laundry `lc001`, Home electronics `he001`, Pet `pt001` (cats-39569, dogs-39570), Smart home `hs001` |

### 1.3 Other retailers (navigation as captured)

- **Article [H]** (`https://www.article.com/`): rooms Living `/browse/224`, Bedroom 225, Dining and Kitchen 222, Home Office 223, Outdoor 58, Decor 48. Type facets: Sofa+Loveseat, Sectional, Lounge Chair, Media Unit, Accent and Side Table, Sofa Bed, Coffee Table, Ottoman, Dining Table, Dresser, Chair, Bed, Nightstand, Desk, Console, Bookcase, Bar Height Stools. Function facets: Modular Sectional/Sofa/Loveseat, Sleeper, Storage, Individual Module, Powered Recliner. Module pieces are sold individually, which matters for the `sectional` leaf (modules and LAF/RAF).
- **West Elm [H]**: departments Furniture, Outdoor, Office, Rugs, Bedding, Bath, Lighting, Pillows and Decor, Window, Art and Mirrors (`/shop/wall-decor-mirrors/`), Kitchen and Dining, Storage, Baby and Kids. Furniture subtree: sofas, sectionals, loveseats, sleepers, recliners, ottomans/stools, coffee/end/side tables, TV/media consoles, console/sofa tables, bookcases, daybeds, beds, dressers, nightstands, armoires, headboards, benches, dining, bar stools, buffets, desks, filing.
- **Wayfair [M]** (seller documentation): Furniture (Living Room, Bedroom, Kitchen and Dining, Office, Entry and Mudroom, Game Room), Outdoor, Rugs, Bedding and Bath, Decor and Pillows (Home Accessories, Window Treatments, Flowers and Plants, Art, Wall Decor, Candles and Holders, Picture Frames, Decorative Pillows and Blankets, Mirrors, Clocks, Seasonal), Organization, Lighting, Kitchen, Baby and Kids, Home Improvement, Appliances, Pet (Dog/Cat Furniture, Pet Gates, Bowls).
- **Living Spaces [M], snippets only**: departments Living Room, Bedroom, Mattresses, Dining Room, Home Office, Outdoor, Kids + Teens, Rugs, Decor + Pillows, Lighting, Wall Art, Entryway. URL scheme `/departments/furniture/<room>/<type>/p<id>`; product pages `pdp-<title-slug>-<sku>`, for example `pdp-ashaway-grey-extendable-66-84-inch-rectangular-dining-table-410127`. The spec table for extension tables lists Length Closed, Length Open and Leaf Width.
- **CORT Furniture Rental [M]**: rooms Living (111 items in one snapshot), Dining (46), Bedroom (62), Home Office; an Accent group (accent chairs, occasional/accent tables, accent chests and cabinets, ottomans and benches); Housewares (bedding, pillows, towels, small appliances); packages and "3D CORT products" (`/furniture-rental/3d-cort-products/_/N-1hrjebf`). Rental packages are sets, which is why the app has `setFacing.js`.
- **Temple and Webster [M]**: Living (sofas, armchairs, TV units, coffee/side/console tables, ottomans and stools, sofa beds), Buffets and Sideboards under Kitchen and Dining and Hallway, Tallboys under Furniture > Bedroom Furniture > Chest of Drawers.
- **Crate and Barrel [M]**: Living (sofas/sectionals, accent chairs, sleeper sofas, power recliners, coffee/console/end tables, TV stands and media consoles, chaise and daybeds, ottomans and benches, game tables), Dining (tables, chairs, bar/counter stools, benches, credenzas/sideboards, kitchen islands, bar carts), Storage, Bedroom (beds, dressers, nightstands, benches, mattresses, cribs), Office, Outdoor, Entryway, Bath.
- **Spine used for the 15 families: Google Product Taxonomy** [H] (`taxonomy.en-US.txt`): Furniture, Chairs, Tables, Decor, Lighting, Linens and Bedding, Plants, Appliances, Bath, Pots and Planters, Electronics, Pet Supplies, Sporting Goods > Fitness, Outdoor Living.

### 1.4 US / AU / UK vocabulary (drives `match` keyword lists)

| Canonical | US | AU | UK | Trap for rules |
|---|---|---|---|---|
| sofa | sofa, couch | lounge, couch, sofa | sofa, settee | AU "lounge" alone means sofa; "lounge chair" is an armchair |
| sectional | sectional | modular lounge, corner lounge | corner sofa | "L-shaped" also appears on desks |
| loveseat | loveseat, love seat | 2-seater sofa | 2-seater, snuggler | v2 only matches `loveseat`; "Love Seat" falls through |
| chaise | chaise lounge | chaise | chaise longue | "chaise" can be a sofa component |
| ottoman | ottoman, pouf, hassock, footstool | ottoman, footstool, pouf | pouffe, footstool, storage ottoman | v2 has `pouf` but not `pouffe` |
| TV stand | TV stand, media console, entertainment center | TV unit, entertainment unit | TV unit, TV cabinet | "TV" also matches TV products |
| side table | side/end/accent table | side table, lamp table | side table, lamp table | UK/AU "lamp table" is a table, not a lamp |
| sideboard | buffet, credenza, sideboard, server | buffet, sideboard | sideboard, dresser | UK "dresser" is a hutch/Welsh dresser; US "dresser" is a chest of drawers |
| chest of drawers | dresser, chest, bureau | chest of drawers, tallboy, lowboy | chest of drawers, tallboy | tallboy is tall and narrow (AU retail about 110-140 cm high, 50-85 cm wide); lowboy is wide and short |
| nightstand | nightstand, night stand | bedside table | bedside table, bedside cabinet | v2 `bed` excludes "bedside" correctly; "bedside" must route to nightstand |
| wardrobe | armoire, wardrobe, closet | wardrobe, robe | wardrobe, armoire | "closet" in the app catalog is a storage leaf |
| floor lamp | floor lamp | floor lamp | standard lamp, floor lamp | "standard lamp" UK |
| pendant | pendant light | pendant light | ceiling light, pendant | "ceiling light" = flush or pendant |
| rug | rug, area rug | rug, floor rug | rug | AU "throw rug" = blanket; US "throw rug" = small rug; AU/UK "carpet" can mean a rug; `RUG_RE` also matches "table runner" |
| decorative pillow | throw pillow, accent pillow | cushion | cushion, scatter cushion | AU/UK "pillow" = bed pillow; AU "cushion" = decorative pillow |
| duvet | duvet, comforter, quilt | doona, duvet, quilt | duvet, quilt | doona sizes: single 140x210, double 180x210, queen 210x210, king 245x210, super king 270x240 |
| curtain | drapes, curtains | curtains, drapes, blockouts | curtains | width is per panel; fullness 1.5-2.5x; lengths 84/96/108/120 in |
| blind | shade (roman/roller) | blind (roller, roman, venetian) | blind | US "shade" also means lamp shade |
| crib | crib | cot | cot, cot bed | US "cot" = folding camp bed |
| patio | patio | alfresco, outdoor | garden furniture | "garden" appears in decor too |
| grill | grill, BBQ | BBQ | BBQ, barbecue | fixtures library covers some |
| hall tree | hall tree, coat rack | hall stand, coat stand, hat stand | hall stand | |
| planter | planter, pot | planter, pot (pot plant = potted plant) | plant pot, planter | "pot" alone is ambiguous with cookware |
| refrigerator | refrigerator | fridge | fridge-freezer | appliances route to the fixtures library |

### 1.5 Title, dimension and image conventions

| Retailer | Title pattern | Dimension listing | Image notes | Conf. |
|---|---|---|---|---|
| Living Spaces | "Name Colour Material Type" (for example "Ashaway Grey Extendable 66-84 Inch Rectangular Dining Table"); sectionals carry "Right Arm Facing" and "3-Piece 157 Inch" | one "W x D x H" line in Details, no seat or arm height; extension tables list Closed / Open / Leaf; filenames carry the view (`<id>_<colour>_<material>_<type>_<view>_<nn>.jpg`, v2 `[photos]`) | cut-out hero ("signature"), side, back, detail, material swatch, room, dimensions, "airoom" render. `never_send` already blocks dimensions, room, airoom, material | M (snippets) + H (rules.toml) |
| Wayfair | "Brand Name Descriptor Type" | spec block "Overall Width - Side to Side / Depth - Front to Back / Height - Top to Bottom" plus seat and arm heights; ordering varies, so key on the letters, never position | primary on white background per third-party guidance; sources conflict on allowed props | M/L |
| CORT | product name plus package; rental, so "set" is the norm | per-piece dims on the product page | studio shots; packages shot together | M |
| Temple and Webster | "Name N-Drawer Tallboy", AU spelling | cm (some AU sites use mm); W x D x H labels | mix of cut-out and styled | M/L |
| IKEA | "NAME, type, colour, dims" | metric and imperial pairs in one string; separate per-component dims for systems; article-number based | many styled "_pe" shots and plain "_ph" shots; meaning of the suffixes **[UNVERIFIED]** | H (title), UNVERIFIED (images) |
| West Elm | "Name (size range)" for modular lines | per-size table | styled lifestyle images dominate | M/L |
| Crate and Barrel | "Name 83 inch Sofa" (inches in title) | inches; "W x D x H" | white-background hero plus lifestyle | M/L |
| Article | "Name Colour Type" | W x D x H plus seat height | studio hero plus lifestyle | M |

Cross-retailer dimension traps (all [M/L], each is a parser rule in Section 5):
- Lamps: the listed W x D is often the base, not the shade.
- Plants: the height may or may not include the pot.
- Wall art: "W x H" ordering is ambiguous; reconcile with the image aspect. Framed size differs from art size.
- Curtains: width is per panel, not the window.
- TVs: "55-inch" is the screen diagonal. For 16:9, W = diag x 0.8716, H = diag x 0.4903, so 55 in is about 47.9 x 27.0 in (121.8 x 68.5 cm). Bare depth is 2-3 in; with a stand 8-12 in deep and about 30-32 in tall. "Fits TVs up to 65 inch" in a stand's title is a capacity, not the width.
- Stools: counter stool seat 24-27 in, bar stool seat 28-32 in; compare SEAT height, which is the surface height minus 9-12 in.
- Extension tables: model the closed state.
- LAF/RAF: judged standing in front of the piece; mirror the model if the photo disagrees.
- Rugs: US 5x8 ft is about 152x244 cm, 8x10 about 244x305, 9x12 about 274x366. AU small 80x150 to 120x170, medium 160x230 to 200x300, large 250x350 to 300x400, XL 350x450 and above, hallway runner 60x230 to 80x300.
- Mattresses (width x length, inches): US twin 38x75, full 54x75, queen 60x80, king 76x80, Cal king 72x84. UK single 36x75, double 53x75, king 59x79, super king 71x79. AU single 36x74, king single 42x80, double 54x74, queen 60x80, king 72x80. EU 90/120/140/160/180 x 200 cm. "King" differs by country, so the size-name parser must be locale-aware.

---

## 2. Families and leaf categories (100 leaves, 15 families, plus `other`)

### 2.0 Legend and global defaults

**Builders (`Path` column).** `T` = Tripo P2 with Meshy 7.1 fallback (AI), followed by the quad budget. `P-rug`, `P-art` = existing procedural Blender builders. New procedural builders: `P-box`, `P-lathe`, `P-drape`, `P-slab`, `P-cush`, `P-cards`. `H` = hybrid (Tripo body plus a procedural part such as glass top, shade, mattress, cord or pot). `S` = skip (route to the fixtures library or a human).

**Scale (`Sc`).** `Bx` = non-uniform fit to the listed W x D x H box (the v2 default, inferred from `uniform_scale` being the lamp exception). `U` = uniform by listed height (keep Tripo proportions). `Th` = fixed thickness for flat items, W and H from the listing. `Fp` = footprint-led (W x D), height free.

**Host.** `fl` floor (`face-based`, the catalog default). `wl` wall (`wall-based`). `ce` ceiling (`ceiling-based`; the app has no behaviour for it, so those rows are catalog-only until the app adds it). `su` rests on a surface: stored as `face-based` with correct dims; the app decides stacking from `isStackableSize` (height 80 cm or less, longest side 120 cm or less) and `canRestOnHost` (at most 1.05x the host footprint).

**Resz (`is_resizable`).** `N` = false. `P` = true only for generic or house items with no vendor link (procedural builders). Every vendor-linked product is `N`, matching the app's `buildAssetInput` comment ("a real product is the size it is"). The app does not consume the column today, so this is a data-hygiene rule, not a behaviour.

**Flags.** `T` transparent/reflective, `Th` thin parts, `S` soft body.

**Failure codes (`Fail`).**

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| P | props/styling baked in (pillows, plants, books) | Gl | glass/acrylic rendered opaque or noisy |
| Th | thin parts lost or fused (legs, slats, wire, rods, chain) | Rf | reflections/specular baked into texture |
| Mu | multiple items in the image (sets, pairs, with stools) | Dr | drape/fold shape unstable, wrinkles baked |
| Tx | text/graphics smeared (art, clock face, book spines, TV) | Sy | handedness/asymmetry flipped (LAF/RAF, sconce arm) |
| Bk | unseen back/underside hallucinated | Fl | flat item inflated or warped (rug, art, curtain) |
| Sc | scale error from the listed dims (lamp base, pot, TV diagonal) | Ho | holes/mesh/weave/perforation |
| Em | emissive parts (screens, lit lamps) | Fu | fur, fringe, foliage fine detail |

**Views.** LS view names from v2 `[photos]`: `signature` (hero, usually 3/4), `side`, `front`, `back`, `detail`, `feature`, `material`, `room`, `dimensions`, `airoom`. `S+B` = multi-image with a straight front and a straight back (adopted 2026-09-30). `Sd` = side. `3Q` = three-quarter. Never send `dimensions`, `room`, `airoom`, `material` (v2 `never_send`); other retailers' images are mapped to the same names by the triage in Section 6.

**Global defaults** (a leaf states only deviations): builder `T` on P2, `face_limit = 2 x quads`; single image order `side, signature, front`; `Sc = Bx`; host `fl`; `Resz = N`; front = local -Z with pivot at centre-bottom (the catalog authors furniture and wall art facing -Z; `FLOOR_ITEM_FACING_OFFSET = pi`, `WALL_HANGING_FACING_OFFSET = pi`; fixtures vary by batch, `adw_` prefix = +Z, so v3 normalises fixtures to -Z); no postprocess; sets: never feed a set shot to image-to-3D (split or skip).

**Catalog column** names the existing catalog category (from `ALLOWED_CATEGORIES`) a leaf should be filed under. `NA` = the DB has a matching category that is NOT in the allow-list, so it would not render.

### 2.1 F1 Seating (13 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`, flags `S` + `Th` (legs).

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| sofa | sofa, couch, sleeper sofa, sofa bed, futon | lounge, couch, settee, 3-seater, 2.5 seater | one W x D x H line; seat and arm heights not listed at LS; sleepers list closed dims | Sofas, 3 Seat Sofas, 2 Seat Sofas, Apartment Sofas, Long Sofas, Futons & Sleeper Sofas |
| loveseat | loveseat, love seat | 2-seater, snuggler | width 52-70 in; v2 misses "love seat" | Loveseat |
| sectional | sectional, modular, L-shaped, corner, LAF, RAF, chaise sectional, N-piece | modular lounge, corner lounge, corner sofa | LAF/RAF judged standing in front; "157 inch" in the title is the overall width; per-module dims vs total | Sectional Sofas |
| daybed | daybed, day bed (indoor) | day bed | sleeping surface twin 39x75 in; trundle listed separately | Day Beds |
| recliner | recliner, power recliner, rocker recliner, wall hugger, lift chair | recliner chair, lift chair | closed dims given; open length 60-80 in (model closed) | Recliner |
| accent_chair | accent chair, armchair, club chair, lounge chair, wingback, barrel chair, slipper chair, swivel chair, glider, rocker | occasional chair, tub chair, wing chair, feature chair | seat/arm height; swivel base radius | Accent Chair, Armchairs, Living Room Chairs, Rocking Chairs, Nod Chairs, Chair |
| chaise_lounge | chaise lounge, indoor chaise | chaise longue | long (60-75 in), asymmetric | Accent Chair |
| dining_chair | dining chair, side chair, arm chair, parsons, host chair, folding chair, banquette chair | carver, kitchen chair, cafe chair | seat height 17-19 in; "set of N" pricing | Dining Chairs, Dining Chair, Dining Room Chairs, Folding Chairs |
| bar_stool | bar stool, counter stool, counter-height stool, swivel stool, backless stool | kitchen stool, breakfast stool | compare SEAT height: counter 24-27 in, bar 28-32 in; subtract 9-12 in from the surface height | Bar & Counter Stools, Bar Stool, Counter Height Chair, Stools |
| ottoman | ottoman, pouf, hassock, footstool, foot stool, storage ottoman, cocktail ottoman | pouffe, footstool, storage cube | round = diameter; "bench ottoman" is a bench | Poufs, Footstools |
| bench | bench, entryway bench, end-of-bed bench, dining bench, storage bench, banquette, settle | bench seat, hall bench | length 36-72 in; "bed bench" collides with the v2 `bed` exclude | Bedroom Benches, Dining Benches, Storage Benches, Outdoor Benches |
| office_chair | office chair, desk chair, task chair, executive chair, gaming chair, ergonomic chair, drafting chair | computer chair, study chair | adjustable seat height range; 5-star base radius | Office Chairs, Task Chair |
| bean_bag | bean bag, beanbag chair, lounge sack, floor pillow | beanbag | diameter; fill-dependent shape | Poufs (closest) |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes (sets, orientation, flags) |
|---|---|---|---|---|---|
| sofa | S+B, else Sd | P (styled pillows/throw), Th legs, Bk | T 12000 (rule: soft keywords go hd) | pivot_cb | "Sofa + loveseat set" or "3-piece living room set": split, one job per piece. Flag S |
| loveseat | S+B, else Sd | P, Th | T 6000 | pivot_cb | same as sofa |
| sectional | S+B | Sy (LAF/RAF mirrored vs the photo), Mu (ottoman in photo), P, extreme aspect | T 12000 | pivot at footprint bounding-box centre-bottom; mirror_for_LAF_RAF (compare the chaise side in the render with the title, flip X on mismatch) | modular "N-piece": build the assembled form; loose ottoman is its own leaf. Flag S |
| daybed | S + Sd | P (bolsters), Mu (trundle), Th | T 8000 | bed postprocess (mattress added only to an empty frame) | split from outdoor_daybed (F11); v2 sends all daybeds to the outdoor 12,000 route |
| recliner | closed-state view only | Mu (open and closed in one image), Bk mechanism | T 6000 | pivot_cb | reject "reclined" views by VLM; model closed dims. Flag S |
| accent_chair | S + Sd | Th legs, Ho (cane/rattan webbing), P | T 3500 (rule hd) | weave optional for cane | swivel base: pivot on the base axis. Flags S, Th |
| chaise_lounge | S + Sd | Sy, Th | T 5000 | pivot_cb | arm side matters for left/right variants |
| dining_chair | S + Sd | Th (slats, spindles), Mu (set of 2/4), Ho (woven seat) | T 2000 | none | "Set of N": build one chair, keep quantity as metadata. Flag Th |
| bar_stool | S + Sd | Th (footrest ring), Mu | T 2000 | none | height = overall, not seat; keep seat height as metadata. Flag Th |
| ottoman | S | Dr (soft sag), Bk (lid), Mu (tray with objects) | T 1500 | pivot_cb | stackable host (supports a tray or a throw). Flag S |
| bench | S + Sd | Th, Ho (slats), Mu | T 1500 | none | Flag Th |
| office_chair | S+B multi (v2 `multi_image`) | Th, Ho (mesh back: use the existing `[net]` step), Bk | T 10000 (HD) | net -> opacity (existing), pivot_cb at the base axis | height range is adjustable; model the mid position. Flag Th |
| bean_bag | S | Dr (wrinkles baked), Sc | P-cush or T 800 | none | `Resz P` only when house-built. Flag S |

### 2.2 F2 Tables and desks (7 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`, flags `Th` (legs). Table tops are stack hosts for the app; keep the top flat and at the listed height.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| coffee_table | coffee table, cocktail table, center table, lift-top coffee table, nesting coffee table | occasional table | round = diameter; nesting sets list the largest; glass top thickness listed separately | Coffee Tables, Coffee Table, Coffee & Side Tables, Outdoor Coffee Table |
| side_table | side table, end table, accent table, C-table, drink table, snack table, pedestal table, nesting tables, plant stand | lamp table, sofa end table | height 18-26 in; UK/AU "lamp table" is a table | Side Tables, End Table, Coffee & Side Tables, Outdoor Side Table |
| console_table | console table, sofa table, entryway table, hall table | hall table, hallway table | long and narrow (W 40-72 in, D 10-16 in); open back | Console Tables |
| dining_table | dining table, kitchen table, breakfast table, pub table, bar table, counter-height table, extension table, trestle, farmhouse, drop-leaf | kitchen table | Length Closed / Open / Leaf Width; "66-84 inch" in the title is the extension range; bar height 40-42 in; DB "Table" (id 164) is mostly dining | Dining Tables, Oval/Rectangular/Round/Square Dining Tables, Bar Tables, Outdoor Dining Tables, Table |
| desk | desk, writing desk, computer desk, L-shaped desk, corner desk, secretary desk, executive desk, gaming desk | study desk, workstation | height 29-30 in; L-shaped lists two lengths and a return | Desks, Writing Desk |
| standing_desk | standing desk, sit-stand desk, height-adjustable desk, electric desk | - | height RANGE (28-48 in); model the lowest | Desks |
| vanity_table | vanity table, makeup vanity, dressing table, vanity with mirror | dressing table | table, mirror and stool in one listing | Desks (DB 58 "Vanity Stands & Tables" is NA) |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| coffee_table | S + Sd | Gl (glass top), Rf (marble/gloss), Th, Mu (books and vase on top) | T 1500, H when the top is glass | glass_top (procedural pane, `KHR_materials_transmission`, never with metallic=1) | nesting set: build the largest, others as separate assets. Flags T, Th |
| side_table | S | Gl, Th, Mu (nesting pair) | T 1500, H when glass | glass_top | `side_table` must beat `lamp` (UK/AU "lamp table"). Flags T, Th |
| console_table | S + Sd | Th, P (decor on top), Bk (open back must stay open) | T 2000 | none; do NOT apply `close_back` (v2 does, by routing console to cabinet) | host `fl`, back faces the wall. Flag Th |
| dining_table | S (table only) | Mu (chairs, centrepiece in the shot), Th, Gl, extension leaf geometry | T 2000, H when glass | glass_top | model the closed state; "Dining set" is split into table plus chairs. Flags T, Th |
| desk | S + Sd | Mu (chair, monitor, lamp), Th, Bk (drawer side), Sy (L-return side) | T 2000 | none | L-shaped: record the return side. Flag Th |
| standing_desk | S | Th (frame), Mu (monitors) | H: parametric frame (two legs, feet, crossbar) plus a Tripo top, or skip | none | model at the lowest height. Flag Th |
| vanity_table | S | Mu (mirror + stool), Rf, Gl | T 2500 for the table; the mirror is a separate `mirror_wall`/`slab` asset | none | split table, mirror, stool. Flags T, Th |

### 2.3 F3 Bedroom (7 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`. Beds are not stackable (height over 80 cm or span over 120 cm); The super-categories Beds, Dressers, Nightstands and Benches are in `FLOOR_ONLY_SUPER_CATEGORIES`, so a bad vendor `wall-based` flag is overridden for them (Storage is not in that list).

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| bed | bed, platform bed, bed frame, canopy bed, four-poster, storage bed, upholstered bed, sleigh bed, panel bed | bedstead, bed frame, ensemble (bed + mattress + base) | size names are locale-specific (see 1.5); overall dims include the headboard; "with mattress" listings exist | Beds, Queen Bed, King Bed, Twin Bed, Double Bed, Full/King/Queen/Super King/Twin Size Beds, Box Spring and Frame - Queen Size |
| headboard | headboard, upholstered headboard, wall-mounted headboard | bedhead | width equals the mattress width; height 40-65 in; no usable depth | Queen Headboard, Twin Headboard |
| nightstand | nightstand, night stand, bedside table, bedside cabinet, floating nightstand | bedside table, bedside cabinet, bedside | height 22-30 in; "floating" = wall-mounted | Nightstands, Nightstand |
| chest_of_drawers | dresser, chest of drawers, chest, bureau, lowboy, tallboy, highboy, vertical dresser, accent chest | chest of drawers, tallboy (tall and narrow), lowboy (wide and short) | US "dresser" = chest of drawers, UK "dresser" = hutch; "dresser with mirror" is a set | Dressers & Chests, Dresser, Chest of Drawers, Accent Chests |
| storage_chest | blanket chest, trunk, toy chest, hope chest, cedar chest, storage trunk | blanket box, toy box | collides with `\bchest\b` and `blanket`; lid and base | Accent Chests, Storage Benches |
| wardrobe | wardrobe, armoire, closet, freestanding closet, clothes cabinet | wardrobe, robe, sliding door wardrobe | height 70-90 in; "armoire" is also used for TV armoires | Wardrobe, Closets |
| mattress | mattress, memory foam, hybrid, innerspring, box spring, foundation | mattress, ensemble base | locale-aware size name; thickness 8-14 in; toppers, protectors and covers are NOT mattresses | Mattress - Queen Size, Mattress - Twin Size, Box Spring and Frame - Queen Size |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| bed | S + Sd; the frame-only photo when it exists (`bed_frame_photo`) | P (bedding and pillows in the hero shot), Mu (nightstands and lamps in the room shot), Bk (frame interior), Th (slats, spindles, posts), Sc (headboard height) | T 10000 (rule: smart) | `bed` (existing: remove the interior, add a 12 in mattress only to an empty frame) | "Bedroom set" (bed + nightstand + dresser): split. Mattress-on-bed stacking in the app is UNVERIFIED. Flag Th |
| headboard | S front | Bk (depth hallucinated), Fl | T 2500 | flatten_back for wall-mounted; NO mattress add (v2 sends headboards to `bed`) | host `fl` for freestanding, `wl` only for a true wall-mounted headboard (Beds category is floor-only, so a `wl` flag is overridden). Flag S |
| nightstand | S + Sd | Th (legs), P (lamp on top), Bk | T 2500 | none | floating variant stays `fl` in the app for now (Nightstands is floor-only). Flag Th |
| chest_of_drawers | S + Sd | Bk (flat drawer fronts), Th (legs), Mu (mirror, decor) | T 2500 | close_back | "dresser with mirror": split; the mirror is `mirror_wall`/`slab`. Tallboy: fit the box, do not widen |
| storage_chest | S | Bk (lid), Th (legs) | T 1500 | none | stackable host for a throw. Flag S if upholstered |
| wardrobe | S, doors closed | Bk (interior), Rf (mirror doors), Mu | T 2500 | close_back; doors closed | mirror doors: do not bake the reflection (see mirror_wall). Height 180-230 cm |
| mattress | S (cut-out hero, for the texture) | Fl, Dr | P-box (rounded box from the size table, quilted texture from the image) | none | scale from the locale size table; thickness from the listing. `Resz P` when house-built. Flag S |

### 2.4 F4 Storage and media (9 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`, `close_back` on solid-backed units. Styled shelves are the main hazard (see Section 6).

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| bookcase | bookcase, bookshelf, etagere, ladder shelf, leaning shelf, cube organizer, shelving unit, corner shelf, open shelf, wall unit | bookcase, shelving unit, display shelf | shelf count; a ladder shelf leans, so depth is the base | Bookcases, Shelving Units, Shelving |
| display_cabinet | display cabinet, curio cabinet, china cabinet, glass door cabinet, hutch, vitrine, wine cabinet, bar cabinet | display cabinet, cabinet with glass doors, hutch | glass doors; a hutch is a top section | Cabinets |
| accent_cabinet | accent cabinet, storage cabinet, utility cabinet, pantry cabinet, shoe cabinet, locker | cupboard, shoe cabinet | doors open vs closed in the photo | Cabinets, Shoe Racks, Entryway & General |
| sideboard | sideboard, buffet, credenza, server, buffet table | sideboard, buffet | W 48-80 in, D 14-20 in, H 28-38 in | Buffets and Credenzas |
| tv_stand | tv stand, media console, entertainment center, tv unit, tv cabinet, floating tv stand, fireplace tv stand | tv unit, entertainment unit | "fits TVs up to 65 inch" is a capacity, not the width | TV Console |
| file_cabinet | file cabinet, filing cabinet, lateral file, vertical file, mobile pedestal, drawer unit | filing cabinet | widths 15/18/30/36/42 in | Filling Cabinets |
| hall_tree | hall tree, coat rack, coat stand, hat stand, entryway bench with hooks, shoe rack | hall stand, coat stand, hat stand | tall and thin; hooks are thin parts | DB categories Hall Trees (72), Coat Hangers (70), Shoe Storage (71) are NA; file under Shoe Racks or Entryway & General, or extend the allow-list |
| basket_bin | basket, storage basket, woven basket, storage bin, hamper, laundry hamper, trash can, storage box | basket, bin (UK/AU "bin" = trash), hamper | diameter x height; fabric bins collapse | Storage |
| room_divider | room divider, folding screen, privacy screen, partition, shoji screen | screen, partition | panel count; model unfolded at a typical angle | Room Divider (the snapshot calls id 180 "Screens and Dividers": verify against the live DB) |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| bookcase | S front, empty shelves | P (books and decor baked), Th (shelves, rails), Bk (open vs closed back), Mu | T 2500 | close_back if the back is solid; reject styled-shelf images (Section 6) | Flag Th |
| display_cabinet | S | Gl, Rf, P (curios inside), Bk | H: Tripo carcass + procedural glass doors, T 2500 | glass_door | Flag T |
| accent_cabinet | S + Sd | Bk, Th (legs), Mu | T 2500 | close_back | doors closed |
| sideboard | S + Sd | Th (legs), Mu (decor on top), Sc | T 2500 | close_back | |
| tv_stand | S, no TV in the image | Em (lit TV on the stand), P, Mu, Gl (glass shelves), Bk | T 2500 | close_back; reject views with a TV (`[triage.avoid]` in 4.4) | floating variant stays `fl` with `floating = true` metadata (see 2.16). Flag T when glass |
| file_cabinet | S | Th (handles), Bk | T 2500 | close_back | |
| hall_tree | S | Th (hooks, rails, slats), Mu (coats and bags) | T 3000 | none | Flag Th |
| basket_bin | S | Ho (weave), Fu (fringe), Dr (soft bins), Mu (contents) | T 1500; P-lathe for a plain round bin | none | host `su` for decor baskets, `fl` for hampers. Flag S |
| room_divider | S unfolded | Th (panels, hinges), Ho (lattice), Gl | T 2500 | none | unfolded zigzag; Flag Th |

### 2.5 F5 Lighting (8 leaves)

Family defaults: `Resz N`, `Sc U` (by height) for lamps, flags `T`, `Th`. The v2 `lamp` postprocess (remove the floor cord, size by height) stays for table, floor and desk lamps. Pivot rules: floor and table items centre-bottom; ceiling items pivot at the canopy (the ceiling point); wall items at the back-plate centre (wall-item pivot convention in the app is UNVERIFIED).

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| table_lamp | table lamp, accent lamp, buffet lamp, bedside lamp, lamp (bare, under 80 cm) | lamp, bedside lamp, table light | listed W x D is often the BASE; height includes the shade; shade diameter may be a separate field; over 80 cm tall the app treats it as a floor item | Table Lamps, Table Lamp, Lamps, Lighting |
| floor_lamp | floor lamp, arc lamp, tripod lamp, torchiere, standing lamp, reading floor lamp | standard lamp, standing lamp | height 55-75 in; arc lamps overhang 40-80 in from the base | Floor Lamp, Standing Lamps |
| desk_lamp | desk lamp, task lamp, clip lamp, architect lamp, adjustable lamp | study lamp, task light | articulated arms and springs; adjustable pose | Desk Lamps, Desk Lamp |
| pendant | pendant light, pendant lamp, hanging lamp, mini pendant, drum pendant, cluster pendant | pendant, ceiling pendant | drop length is adjustable (chain or cord); canopy diameter; shade diameter is W | Ceiling Lighting, Kitchen & Dining Lighting |
| chandelier | chandelier, sputnik chandelier, linear chandelier, multi-light fixture | chandelier | drop; arm count; crystals | Ceiling Lighting |
| flush_mount | flush mount, semi-flush mount, ceiling light, ceiling fixture, drum ceiling light | ceiling light, oyster light | diameter x depth (4-10 in) | Ceiling Lighting |
| wall_sconce | sconce, wall sconce, wall light, wall lamp, vanity light, picture light, swing arm lamp | wall light, bracket light | arm extension is the depth; mounting height is separate | Wall Lighting (the DB host MUST be `wall-based`: the app's category heuristic does not match "Wall Lighting") |
| ceiling_fan | ceiling fan, ceiling fan with light | ceiling fan | blade span 42-60 in; down-rod length | Ceiling Lighting (no fan-specific category) |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Host / Sc / Notes |
|---|---|---|---|---|---|
| table_lamp | S + Sd | Th (cord, finial), Gl (glass base), Sc (base dims), Em (lit shade), Rf (metal), Mu (pair) | T 3000, or H: Tripo base + procedural lathe shade for plain drum/empire shades | `lamp` (existing); lathe shade as an option | host `su`; Sc U by height. "Set of 2" lamps: one lamp. Flags T, Th |
| floor_lamp | S + Sd | Th (pole, tripod legs, arc), Sc, Em | T 3000, or H: cylinder pole + base disc + head | `lamp`; arc lamps keep `uniform_scale_match` (`\barc\b`, `adjustable`) | `fl`; Sc U. Flag Th |
| desk_lamp | S + Sd | Th (arms, springs, clip), Sy | T 2500 | `lamp` | `su`; Sc U; model the neutral pose. Flag Th |
| pendant | S | Th (chain/cord), Gl (globe), Sc (drop), Em | H: Tripo shade (T 2000) + procedural chain/cord + canopy | cord/chain rebuild (cylinder, drop from the listing or a 60 cm default); pivot at the canopy | `ce` (no app support); Sc U by shade diameter. Flags T, Th |
| chandelier | S | Th (arms, crystals), Gl, Mu | T 6000 (many arms) | chain rebuild; pivot at the canopy | `ce`; Sc U by width. Flags T, Th |
| flush_mount | S | Gl (frosted diffuser), Em | T 1500, or P-lathe for a plain drum | flatten_back; pivot at the ceiling plane | `ce`; Sc Bx (diameter x depth) |
| wall_sconce | S + Sd | Th (arm), Sy (arm side), Em, Gl (shade) | T 2000 | flatten_back (back plate flat to the wall); pivot at the back-plate centre | `wl`; Sc Bx (arm extension = depth). Mounting height 150-170 cm as metadata. Flags T, Th |
| ceiling_fan | S | Th (blades), Sy (blade pitch) | H: procedural blades + Tripo motor housing and light kit, or T 5000 | pivot at the canopy | `ce`; Sc Bx. Flag Th |

### 2.6 F6 Rugs and mats (4 leaves)

Family defaults: builder `P-rug` (6 quads, no credits), `Sc Fp` (W x L exact, thickness fixed 1 cm), host `fl`, `Resz N`. The best view is a straight top-down or a rectified one; the app classifies all of these as floor coverings through `RUG_RE` (collision-exempt). `RUG_RE` over-matches "table runner", "stair runner", "kilim pillow" and any "mat", so those titles must be routed away before the rug leaves (Section 5).

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| rug_rect | rug, area rug, rectangular rug, runner (aspect ratio 2.5 or more), shag rug, kilim, outdoor rug | floor rug, runner, hall runner | feet-inches "5'3" x 7'7"" or "5x8"; US 5x8 ft is about 152x244 cm; AU sizes in cm; pile height rarely listed | Rugs, Rug, Area Rugs |
| rug_round | round rug, circular rug, oval rug, semi-circle rug | round rug | diameter; oval is W x L | Rugs |
| rug_shaped | hide rug, cowhide rug, sheepskin, faux fur rug, irregular rug, organic-shaped rug | cowhide rug | approximate outline; "approx." dims | Rugs |
| mat_small | door mat, welcome mat, bath mat, kitchen mat, anti-fatigue mat, kitchen runner | doormat, bath mat | typically 16x26 in; yoga mats belong to fitness | Kitchen Mats, Rugs |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| rug_rect | top-down hero; else rectify the 3/4 view | Fl, Fu (shag), P (room shot with furniture), perspective | P-rug | rectify (homography), crop the border, texture only | runner by aspect ratio 2.5 or more; size variants are separate jobs |
| rug_round | top-down hero | Fl, perspective | P-rug (disc with a circular alpha mask) | rectify | oval: ellipse |
| rug_shaped | cut-out hero with a clean mask | outline hallucinated, Fu | P-rug with an alpha outline polygon from the mask (200-400 quads) | mask cleanup | skip if the mask is poor |
| mat_small | hero | Fl | P-rug, thickness 1-1.5 cm | rectify | |

### 2.7 F7 Wall decor (8 leaves)

Family defaults: host `wl`, `Sc Th` (W x H from the listing, thickness fixed), `Resz N`, front -Z (the app's `WALL_HANGING_FACING_OFFSET = pi`), postprocess `flatten_back`. Wall hangings are never stack hosts. The app flags an asset as wall-mounted when `host` contains "wall", or `is_on_wall`, or (fallback) the category name matches `artwork|painting|picture|poster|tapestr|mirror|sconce` or `wall art|decor|hanging|lamp|clock|mount|piece`. Known gaps are in Section 5.5.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| art_framed | wall art, framed art, framed print, canvas, canvas print, painting, poster, photograph, art print, oil painting, abstract art | wall art, canvas print, framed print, picture (UK), artwork | "W x H" ordering is ambiguous (reconcile with the image aspect); framed size differs from art size; depth 1-2 in (gallery wrap 1.5 in) | Artwork, Wall Art, Paintings & Pictures |
| art_set | set of 2/3/4/5, gallery set, diptych, triptych, panel set | triptych, 3-piece canvas set | total width vs per-piece dims | Wall Art |
| wall_decor_3d | wall sculpture, metal wall art, wall hanging, wall letters, wall plaque, wood wall decor | metal wall art | depth 2-10 in; hanging offset | Wall Decor, Wall Decor Misc |
| wall_textile | tapestry, wall hanging, macrame wall hanging, woven wall hanging, fabric wall art | tapestry | thin and soft; the app regex `tapestr\b` cannot match "tapestry" | Wall Decor |
| mirror_wall | wall mirror, framed mirror, round mirror, arched mirror, oval mirror, sunburst mirror, beveled mirror, accent mirror | wall mirror, hall mirror, overmantel | W x H; "round 30 inch" is the diameter; frame depth 1-3 in | Mirrors, Mirror |
| mirror_floor | floor mirror, full-length mirror, leaner mirror, standing mirror, cheval mirror, dressing mirror | cheval mirror | height 55-72 in; a leaner tilts 5-8 degrees; a cheval has a stand | Mirrors (but see 5.5: the app would class it as a wall hanging) |
| clock_wall | wall clock, large wall clock, decorative wall clock | wall clock | diameter | Clocks |
| wall_shelf | wall shelf, floating shelf, ledge shelf, picture ledge, corner wall shelf, wall cube | floating shelf | depth 4-12 in; bracket hidden | Wall Shelves (host must be `wall-based`; the heuristic misses it) |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| art_framed | straight-on hero | Fl, Tx, Rf (glass glare), P (room shot), perspective | P-art (6 quads, existing) | rectify; crop the frame; flatten_back | thickness 3 cm (gallery wrap 3.8). A furniture title containing "framed" or "print" must NOT route here (v2 does) |
| art_set | straight-on hero of the set | Mu | P-art, one panel per piece with the listing's spacing | rectify per panel | composite one asset or split per piece; decide per retailer |
| wall_decor_3d | S + Sd | Th, Fl, Rf | T 1500 | flatten_back | `Sc Bx` (depth listed). Flag Th |
| wall_textile | hero | Fu (fringe), Dr | P-drape (flat hang) or P-slab | none | thickness 1-3 cm. Flag S |
| mirror_wall | straight-on hero | Rf (the baked room reflection makes the mirror look like a photo), Th (thin frame), Gl | H: frame (T 400, or P-slab for plain frames) + procedural neutral reflective glass pane | glass_mirror (metallic, low roughness; NOT `KHR_materials_transmission`, which is invalid with metallic=1); flatten_back | never keep the reflection in the texture. Environment-map reflection in the app is UNVERIFIED. Flag T |
| mirror_floor | straight-on hero | Rf, Th (stand) | H as mirror_wall | bake a 5-8 degree tilt for a leaner (app tilt support UNVERIFIED); pivot at the feet | host `fl`, which collides with the app heuristic (5.5) |
| clock_wall | straight-on hero | Tx (clock face), Th (hands) | P-lathe (disc + bezel) with the face texture, hands as thin boxes | none | `Th` fixed thickness. Tabletop clocks go to `decor_small` |
| wall_shelf | S | Th (brackets), P (decor on the shelf) | P-slab for a plain board, else T 1000 | flatten_back | `wl`; the DB must carry `wall-based` |

### 2.8 F8 Tabletop and objects (7 leaves)

Family defaults: host `su` (stored `face-based` with correct dims so `isStackableSize` and `canRestOnHost` can work), `Sc U` by height, `Resz N`, flags `T` for glass and glazed items. Decor rows in the catalog are mostly "Decorations", "Decorative Objects", "Vases & Jars", "Sculptures & Figurines", "Table Frames", "Clocks". Heights above 80 cm or spans above 120 cm are not stackable.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| vase | vase, jar, bottle vase, urn, ginger jar, bud vase, floor vase, pitcher | vase | height and mouth diameter; "set of 3" | Vases & Jars |
| bowl_tray | decorative bowl, fruit bowl, tray, serving tray, ottoman tray, platter, catchall tray | bowl, tray | diameter x height; shallow | Decorations, Decorative Objects |
| candle_holder | candle holder, candlestick, hurricane, lantern, taper holder, votive, tealight holder, candelabra | candlestick, lantern | height; glass hurricane; lantern handle | Decorations |
| candle | candle, pillar candle, jar candle, scented candle, taper candle, LED candle | candle | diameter x height | Decorations |
| sculpture_object | sculpture, figurine, statue, bust, decorative object, orb, sphere, objet, bookend, animal figurine | figurine, ornament | small; height | Sculptures & Figurines, Decorative Objects |
| book_stack | decorative books, book set, coffee table book, book stack, faux books | decorative books | each book about 9x11 in; stacks of 2-3 | Decorations |
| decor_small | photo frame, picture frame (tabletop), table clock, desk organizer, tabletop sign, jewelry box, desk accessory, pen cup, tissue box | photo frame, desk tidy | frame sizes 4x6 up to 8x10 | Table Frames, Clocks, Decorations, Office Accessories |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| vase | S | Gl (glass), Rf (glaze), Mu (flowers inside), Tx | P-lathe (profile from the cut-out silhouette), T 800 for asymmetric shapes | remove flowers; keep a shallow interior | Sc U; flags T |
| bowl_tray | S | Mu (fruit, contents), Gl, Rf, Th (handles) | P-lathe; trays with handles T 1000 | none | Sc Bx |
| candle_holder | S | Gl, Th (taper), Em (flame), Mu | P-lathe or T 1000 | remove flame | Flags T, Th |
| candle | S | Em (flame), Gl (jar), Tx (label) | P-lathe cylinder with wick, no flame | none | Sc Bx (diameter x height) |
| sculpture_object | S | Th, Rf (metal), Mu (pair), Sc | T 1500 | pivot_cb | Sc U |
| book_stack | S | Tx (spines) | P-box (N boxes with slight rotation offsets) | none | `Resz P` when house-built |
| decor_small | S | Mu, Tx, Gl (frame glass), Th | P-slab for frames (frame + neutral inner photo; remove the sample photo), P-lathe for round clocks, else T 1000 | remove sample photo | flags T |

### 2.9 F9 Plants and planters (4 leaves)

Family defaults: `Resz N`, `Sc U` by height, flags `Th`, `Fu`. `Plants` is in `FLOOR_ONLY_SUPER_CATEGORIES`. From the plant/pot memory note: 3dsky-style plants ship foliage and pot as separate GLBs; combine with `dy = potMaxY - plantMinY - insert` (insert 0.03 m, because pots already have a modelled soil surface); drooping plants need the anchor at the origin; pivot on the floor and on the pot axis; a `_pot` file can be pot plus stand; never round-trip through Blender.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| plant_potted | potted plant, faux plant, artificial plant, fiddle leaf fig, snake plant, succulent, monstera, bonsai, houseplant | pot plant (AU: potted plant), artificial plant | height may or may not include the pot (check the listing text); pot diameter separate | Plants |
| plant_tree | faux tree, artificial tree, floor plant, palm tree, olive tree, topiary, ficus tree, "6 ft tree" | artificial tree | 4-8 ft; includes the pot or not | Plants |
| planter | planter, plant pot, flower pot, plant stand, hanging planter, window box, cachepot, trough | plant pot, planter | diameter x height; liner vs cachepot; "pot" alone is ambiguous with cookware | Plants, Decorations (DB "Outdoor Accessories" 141 is NA) |
| stems_florals | faux stems, flower stems, floral arrangement, faux flowers, branches, pampas grass, eucalyptus, dried flowers (a wreath is a wall item: `wall_decor_3d`) | faux flowers, florals | stem height 24-48 in; bundles | Plants |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Host / notes |
|---|---|---|---|---|---|
| plant_potted | S | Fu (foliage detail), Th (stems, leaves), Mu (pot and plant), Sc (height with or without pot), Fl (leaf sheets) | H: pot (P-lathe or T 800) + foliage (T 3000 or P-cards) | plant_pot_combine (insert 0.03 m); double-sided leaf alpha | `fl` (desk succulents under 80 cm are `su`); Sc U. Flags Th, Fu |
| plant_tree | S | Fu, Th (trunk, branches), Mu | T 5000, or P-cards for the crown | plant_pot_combine | `fl`; Sc U. Flags Th, Fu |
| planter | S, plant removed | Gl and Rf (glaze), Mu (plant inside), Th (stand legs) | P-lathe plus a soil disc for round or cylindrical; T 1000 for fluted or square | soil disc (matte dark) | `fl` or `su`; Sc Bx |
| stems_florals | S | Fu, Th, Dr | P-cards (2-3 crossed alpha cards from the cut-out) | none | `su`; Sc U. Flags Th, Fu |

### 2.10 F10 Textiles and window (6 leaves)

Family defaults: `Resz N`, host `su` for pillows and bedding (the app treats them as pillow-class: `isPillowClassName` matches `/pillow|cushion/` in the name and `BEDDING_RE` in the name or category, so they ride the bed when it is dragged and are collision-exempt), flag `S`. Stacking of bedding on a mattress asset and any curtain or blind hosting logic are UNVERIFIED.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| pillow | throw pillow, accent pillow, decorative pillow, lumbar pillow, pillow cover, cushion cover, cushion, outdoor cushion (a floor cushion or floor pillow is `bean_bag`, which is matched first) | cushion, scatter cushion | "18x18 in", lumbar "12x20 in"; cover vs insert; "set of 2" | Pillows, Cushions |
| bed_pillow | bed pillow, sleeping pillow, body pillow, memory foam pillow | pillow | standard 20x26, queen 20x30, king 20x36 in; protectors are not pillows | Pillows |
| throw_blanket | throw, throw blanket, blanket, knit throw, faux fur throw, bath towel | throw rug (AU, means blanket), blanket | about 50x60 in; folded vs draped | Throws, Sheets and Blankets |
| bedding_set | duvet cover set, comforter set, quilt set, bedspread, sheet set, coverlet, bed in a bag | doona cover, quilt cover set | locale size; doona single 140x210 to super king 270x240 cm; the photo is a made-up bed | Sheets and Blankets |
| curtain | curtain, curtain panel, drapes, sheers, blackout curtain, window panel | curtains, drapes, blockouts, sheers | width is per panel; fullness 1.5-2.5x; lengths 84/96/108/120 in; rod pocket or grommet | Curtains, Drape |
| blind_shade | blinds, window shade, roman shade, roller shade, cellular shade, venetian blind, bamboo shade | blind, roller blind, roman blind | width x drop; inside or outside mount; US "shade" also means a lamp shade | Shades, Window Treatments |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| pillow | S | Dr (baked wrinkles), Tx (prints), Fl | T 600 (SPEC: HD 600), or P-cush for solid colours | none | thickness from the listing or 12 cm |
| bed_pillow | S | Dr | P-cush | none | rides the bed |
| throw_blanket | S | Dr, Fu (fringe), Mu (on a sofa), Tx | P-drape (folded rectangle) or T 600 | fold geometry | `throw` alone is not in `BEDDING_RE` but "blanket" is |
| bedding_set | S, flat or made-up shot | Mu (bed, pillows and nightstands in the set shot), Dr | P-drape from the bed size plus a 30-50 cm drop, texture from the hero | none | needs the target bed size; `Resz P` |
| curtain | S, flat-lit | Fl, Dr, Gl (sheers need alpha), Mu (window and furniture), Sc (per panel) | P-drape (sinusoidal pleats from the width and fullness; pair of panels) | alpha for sheers; pivot at the rod top | host `wl`; Sc Bx (panel W x length); thickness 3-8 cm. Flags T, S |
| blind_shade | S | Gl, Fl | P-slab (stepped slabs for roman or roller folds from width x drop) | pivot at the headrail | host `wl`; Th. Flag S |

### 2.11 F11 Outdoor (9 leaves)

Family defaults: host `fl`, `Resz N`, `Sc Bx`, flags `Th` and `Ho` (wicker, slats, mesh). Titles that contain outdoor, patio, garden, alfresco, pool or deck route here before the indoor leaves. The catalog has dedicated Outdoor categories (Outdoor Sofas/Chairs/Dining Chairs/Dining Tables/Coffee Table/Side Table/Bar Stools/Bar Tables/Benches); `Terrace Outdoor` (id 191) is a 16-piece kit.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| outdoor_sofa | outdoor sofa, patio sofa, outdoor sectional, outdoor loveseat | patio lounge, outdoor lounge, alfresco sofa | cushion thickness; frame vs cushions; sets of 4-7 pieces | Outdoor Sofas, Terrace Outdoor |
| outdoor_chair | outdoor chair, patio chair, adirondack chair, outdoor dining chair, outdoor bar stool, rocking chair (outdoor) | patio chair, outdoor armchair, deck chair | seat height | Outdoor Chairs, Outdoor Dining Chairs, Outdoor Bar Stools |
| outdoor_lounger | outdoor chaise, sun lounger, pool lounger, zero gravity chair, reclining lounger | sun lounge, sun lounger | length 75-80 in; model flat or a typical 30 degrees | Outdoor Chairs |
| outdoor_table | outdoor dining table, patio table, outdoor coffee table, outdoor side table, bistro table, fire table, picnic table | alfresco table, garden table | umbrella hole; glass or tile top | Outdoor Dining Tables, Outdoor Coffee Table, Outdoor Side Table, Outdoor Bar Tables |
| outdoor_daybed | outdoor daybed, patio daybed, canopy daybed, pool daybed | cabana bed | 150-260 cm; canopy | Day Beds (v2 HD route kept) |
| patio_umbrella | patio umbrella, market umbrella, cantilever umbrella, parasol, cabana | outdoor umbrella, parasol | canopy diameter 7-11 ft; model open | Outdoor (DB "Outdoor Accessories" 141 is NA) |
| fire_pit | fire pit, fire table, outdoor fireplace, chiminea, patio heater | firepit, chiminea | diameter; flame | Outdoor |
| hammock_swing | hammock, hammock stand, porch swing, swing chair, hanging chair, egg chair | hammock, hanging egg chair | stand footprint; hang-point height | Outdoor |
| bbq_grill | grill, gas grill, charcoal grill, smoker, kamado, pizza oven, outdoor kitchen | BBQ, barbecue, BBQ trolley | lid open or closed; cart | Kitchen Appliances (allowed), or the fixtures library |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| outdoor_sofa | S+B | P (separate cushions), Ho (wicker), Th, Mu (set) | T 12000 (HD, `multi_image`) | weave optional | conversation sets: split. Flags S, Th |
| outdoor_chair | S + Sd | Ho, Th (slats), Mu | T 3500 | none | Flag Th |
| outdoor_lounger | S + Sd | Th (slats), Ho, Sy | T 5000 | none | model a typical reclined angle, decide once |
| outdoor_table | S | Gl, Th, Mu (umbrella, chairs) | T 2000, H when glass | glass_top | ignore the umbrella hole. Flags T, Th |
| outdoor_daybed | S+B | P (pillows, canopy), Th (canopy posts), Mu | T 12000 (existing v2 route) | none (it carries its own cushions; no mattress add) | Flags S, Th |
| patio_umbrella | S open | Th (ribs, pole), Fl (canopy) | H: lathe pole and base + ribbed cone canopy, texture from the hero | none | model open. Flags Th, S |
| fire_pit | S | Em (flame), Rf, Gl (fire glass) | T 2500 | remove the flame | Flag T |
| hammock_swing | S | Th (chains, ropes, stand), Dr (sag), Ho (net) | T 4000, or H | none | hanging swing chairs are host `ce` (no app support). Flags Th, S |
| bbq_grill | S lid closed | Th (handles), Rf, Mu (accessories) | S (route to the fixtures library) or T 3000 | none | |

### 2.12 F12 Kids and nursery (4 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`, flag `Th` (slats, ladders, rails). A `kids` flag narrows or shifts the height and length sanity ranges (a kids chair is 40-80 cm high, a crib 80-110 cm). The catalog has only "Kids & Toddlers Beds" and "Kids Bedroom Accessories" and "Toys"; other kids furniture has no dedicated category.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| crib | crib, convertible crib, baby crib, bassinet, cradle, playpen, play yard, mini crib | cot, cot bed, travel cot | US standard mattress 28x52 in; US "cot" = camp bed | Kids & Toddlers Beds |
| kids_bed | toddler bed, kids bed, bunk bed, loft bed, twin loft, trundle bed, house bed, car bed | cabin bed, bunk | height 60-70 in for bunk and loft; ladder and rails | Kids & Toddlers Beds, Bunk Beds, Loft Beds |
| kids_table_set | kids table, kids table and chairs, play table, activity table, kids desk, kids chair | kids table | small (H 20-24 in); table plus 2 chairs in one listing | no dedicated category (file under the adult equivalent with the `kids` flag) |
| changing_table | changing table, diaper changing table, changer dresser, changer topper | change table | topper height | Dressers & Chests |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| crib | S + Sd | Th (slats), Mu (bedding, mobile), Bk | H: parametric slat generator for rails and slats plus a Tripo headboard (T 4000) | strip bedding; optional 28x52 in mattress (bed postprocess) | Flag Th |
| kids_bed | S + Sd | Th (ladder, rails), Mu (two mattresses and bedding), Bk | T 10000 | bed postprocess (a bunk needs two mattresses) | trundle: separate asset. Flag Th |
| kids_table_set | S | Mu, Th | T 1500 each, after splitting table and chairs | none | split |
| changing_table | S | Mu (pad, baby items), Th | T 2500 | close_back | |

### 2.13 F13 Kitchen and bath (3 leaves)

Family defaults: `fl`, `Resz N`, `Sc Bx`. The app already ships a fixtures library (about 40 items in `src/data/fixtureManifest.js`: appliances, sinks, toilets, bathtubs), so bath fixtures are `skip`, and only furniture-like pieces are built.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| kitchen_island | kitchen island, kitchen cart, utility cart, rolling cart, butcher block island, microwave cart | kitchen trolley; AU "island bench" is usually built-in | height 34-36 in; casters; stools tucked in | Kitchen Islands, Kitchen & Dining Carts |
| bar_cart | bar cart, serving cart, tea cart, beverage cart, wine cart | drinks trolley, bar trolley | 2-tier or 3-tier; glass shelves | Kitchen & Dining Carts |
| bath_vanity | bathroom vanity, vanity cabinet, vanity with sink, vanity set, washstand | vanity unit, washstand | single or double sink; top and faucet may not be included; W 24-72 in | DB "Bath" (142) is NA; file under Cabinets or extend the allow-list |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| kitchen_island | S + Sd | Mu (stools, decor), Th (casters), Rf (marble) | T 2500 | none (viewed from all sides; no close_back) | Flag Th |
| bar_cart | S | Th (rails, wheels), Gl (shelves), Mu (bottle and glass props) | T 2000 | strip props via triage | Flags T, Th |
| bath_vanity | S | Rf (porcelain, marble), Mu (faucet, towels), Gl (mirror above) | H: Tripo cabinet (T 2500) + procedural basin and top, no faucet; or skip to the fixtures library | close_back | floating vanities stay `fl` for now. Flag T |

### 2.14 F14 Appliances and electronics (7 leaves)

Family defaults: `fl` unless stated, `Resz N`, `Sc Bx`, flags `T`, `Em`. Most of these are better as procedural boxes than as AI meshes, because screens, stainless steel and glass produce baked reflections and lit-screen content.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| tv | TV, television, smart TV, 4K TV, OLED, QLED, Frame TV | TV, television | the number is the screen diagonal: W = diag x 0.8716, H = diag x 0.4903 for 16:9 (55 in is about 121.8 x 68.5 cm); bare depth 2-3 in; with a stand 8-12 in deep | TVs, Standing TVs (DB "TV (50 and larger)" 162 and "TV (32 and under)" 160 are NA) |
| appliance_large | refrigerator, washer, dryer, dishwasher, range, oven, stove, cooktop, range hood, microwave, freezer | fridge, rangehood, cooktop, hob | W 24-36 in; counter depth; door swing | Refrigerators, Washing Machines, Kitchen Appliances (DB Ovens and Stoves 77, Dishwashers 78, Dryers 82, Utility Room 80 are NA) |
| small_appliance | coffee maker, toaster, blender, air fryer, kettle, stand mixer, espresso machine, slow cooker, rice cooker | jug (kettle) | counter-top | Kitchen Appliances |
| speaker_soundbar | speaker, soundbar, bookshelf speaker, floor speaker, subwoofer, smart speaker, turntable, record player | | grille cloth; stand | Entertainment (DB "Music Systems and Speakers" 85 is NA) |
| fan_heater_purifier | tower fan, pedestal fan, space heater, air purifier, humidifier, dehumidifier, portable air conditioner | oil heater | thin and tall; vents | none (extend the allow-list) |
| fireplace_electric | electric fireplace, fireplace insert, fireplace mantel, wall mounted fireplace, bio-ethanol fireplace | fireplace surround | flame; "fireplace TV stand" is a `tv_stand` | none (extend the allow-list) |
| bath_fixture | toilet, bathtub, shower, sink, faucet, pedestal sink, wall-hung basin, towel rail | basin, WC, shower screen | | DB "Bath" (142) is NA; use the fixtures library |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| tv | S front, screen off if possible | Em (screen content baked), Tx, Rf, Th (stand legs) | P-box: slab with a thin bezel, black glass screen, optional V-foot stand; W and H from the diagonal; depth 6 cm | none | `Resz P`. TRAP: a 55 in TV is 121.8 cm wide, above the app's 120 cm stackable limit, so it cannot be placed on furniture. Wall-mounted: host `wl`. Flag T |
| appliance_large | S front, doors closed | Rf (stainless), Th (handles), Mu (open doors with food), Bk | P-box (door lines, handle, top), or S (route to the fixtures library) | none | fixtures batches differ in facing; normalise to -Z |
| small_appliance | S | Rf (chrome), Th (cords), Gl (carafe), Em | T 2500 | remove the cord | host `su`. Flags T, Th |
| speaker_soundbar | S | Tx (logos), Th (stands) | P-box (grille box plus feet), T for ornate | none | host `su` or `fl` |
| fan_heater_purifier | S | Th and Ho (grille, blades), Tx | T 2500 | none | |
| fireplace_electric | S | Em (flame), Gl (glass front), Mu (TV above) | H: Tripo surround (T 3000) + procedural firebox, flame off | close_back | wall-mounted variant host `wl`. Flag T |
| bath_fixture | S | Rf, Gl | S (fixtures library) | none | |

### 2.15 F15 Pet, fitness and misc (4 leaves) and the fallback

Family defaults: `fl`, `Resz N`, `Sc Bx`. The catalog has "Pets", "Toys", "Gaming", "Entertainment", "Kids Bedroom Accessories", "Clothing"; there is no fitness category.

**(a) Identity**

| Leaf | Keywords EN | Keywords AU/UK | Dimension format and traps | Catalog |
|---|---|---|---|---|
| pet_bed | dog bed, cat bed, pet bed, pet sofa, donut bed, orthopedic dog bed, cat cave, heated pet bed | dog bed, cat bed | diameter or W x D; v2 `bed` matches "dog bed" | Pets |
| pet_furniture | cat tree, cat tower, cat condo, scratching post, dog crate, kennel, dog house, pet gate, pet stairs, pet feeder station | cat tree, cat scratcher | cat trees 60-180 cm; sisal poles | Pets |
| fitness_machine | treadmill, exercise bike, rowing machine, elliptical, weight bench, power rack, kettlebell, pull-up bar | exercise bike, cross trainer (elliptical) | folded vs unfolded dims | none (extend the allow-list) |
| game_table | pool table, billiard table, ping pong table, table tennis table, foosball, air hockey, poker table, arcade cabinet | table tennis table | large footprint; folded dims | Gaming, Entertainment |

**(b) Build**

| Leaf | Views | Fail | Path | Postprocess | Notes |
|---|---|---|---|---|---|
| pet_bed | S, no pet | Dr, Fu (faux fur), Mu (pet in image) | P-cush (donut or bolster with a raised rim), or T 1500 | none | Flags S, Fu |
| pet_furniture | S, no pet | Th (sisal, hammocks), Mu (cats), Sc | T 4000 | none | Flags Th, S |
| fitness_machine | S, unfolded | Th (rails, spokes), Mu (person exercising), Em (console) | T 6000, or S | none | decide folded vs unfolded once |
| game_table | S | Th (legs), Mu (balls, cues), Fl | T 3500 + procedural felt top for a pool table | none | Flag Th |

**Fallback `other`** (family `misc`): Tripo P2, Smart Mesh 2,500 quads, host `fl`, `Resz N`, no postprocess; in v3 every `other` hit goes to the human queue with the top-3 candidate leaves (Section 5).

**Leaf count check:** F1 13, F2 7, F3 7, F4 9, F5 8, F6 4, F7 8, F8 7, F9 4, F10 6, F11 9, F12 4, F13 3, F14 7, F15 4 = **100 leaves**, plus `other`.

### 2.16 Modifier flags (set during head-phrase parsing; they change routing, host or sanity ranges, not the leaf list)

| Flag | Detection keywords | Effect |
|---|---|---|
| outdoor | outdoor, patio, garden, alfresco, pool, deck | route to F11, or swap the catalog category (for example Outdoor Sofas) |
| kids | kids, children, toddler, youth, nursery, baby, junior | route to F12 or shift the height and length sanity ranges |
| sleeper | sleeper, pull-out, sofa bed, futon, convertible | route to `sofa` with closed dims; never to `bed` |
| set | set of N, N-piece, pair, bundle, collection | set handling: split or skip (never feed the set shot) |
| tabletop | tabletop, desktop, countertop, mini | host `su`, small height; frames and clocks go to `decor_small` |
| easel | easel, standing frame | art is not a wall item |
| unframed | unframed, gallery wrapped, canvas only | gallery-wrap thickness 3.8 cm |
| floating | floating, wall-mounted | host `wl` only for the wall leaves (`wall_shelf`, `wall_sconce`, `clock_wall`, `mirror_wall`, art). For nightstand, TV stand and vanity the host stays `fl` and `floating = true` is stored as metadata (the app has no elevated floor placement; UNVERIFIED), because a `wall-based` row would be placed as a wall hanging |
| glass | glass, acrylic, lucite, mirrored, crystal, clear | hybrid glass path (T flag) |
| mesh | mesh, net, cane, rattan, wicker, webbed, slat, perforated | `net` step or weave postprocess |
| module | module, modular, armless, corner, wedge, add-on | build one module; no assembly |
| ladder | ladder, leaning, leaner | ladder bookcase or leaner mirror; bake the tilt |
| rocker | rocker, rocking, glider | accent_chair variant (curved base, thin parts) |
| bar_height | bar height, counter height, pub, bistro | dining_table or bar_stool variant; height sanity [90,115] |
| standing | standing, sit-stand, height adjustable, electric | `standing_desk`; model the lowest height |
| extension | extendable, extension, expandable, drop-leaf, butterfly | `dining_table` closed state |

---

## 4. Proposed v3 `rules.toml` skeleton

The skeleton is split into five fenced blocks below (4.1 header and families; 4.2 stages 1-2; 4.3 stage 3 part A; 4.4 stage 3 part B with fallbacks, modifiers and `dims_route`; 4.5 golden probes). **Concatenate the four `toml` blocks in order to get one file.** A harness (Python `tomllib` reading this report from stdin, no files written) parsed it, checked the schema and ran the golden probes; results are in 4.6.

Schema notes (what changes from v2):
- Routing runs on the **head phrase** of the title (Section 5), not on the whole title. A pattern ending in `$` is a head-noun anchor ("sofa table" ends in "table", so it can never match a `sofa$` pattern). `match` = unconditional patterns on the head; `match_ctx` = patterns that only count when one of the leaf's `ctx` regexes hits the context (title plus last two breadcrumbs), used for the outdoor leaves; `match_title` = patterns on the full title; `match_low` = pass-2 patterns that hit only when no leaf matched in pass 1, and mark the result low-confidence (VLM check). `exclude` is tested on the head.
- `postprocess` is a **list** (v2: a single string `lamp` or `bed`).
- `resizable` is the value for vendor-linked products (always false, matching the app's `buildAssetInput`); `resizable_house = true` marks procedural builders whose house-built assets with no vendor link may be resizable.
- `dims = { h = [..], l = [..] }` replaces `height_cm` / `length_cm` (h = overall height range in cm, l = longest side range in cm); the loader maps them back.
- `mode` is dropped from leaves (all categories run on P2 since 2026-10-06; `face_limit = 2 x quads` is unchanged).
- Vocabulary is declared in `[vocab]` so the loader can reject typos.

### 4.1 Header, vocabulary, defaults and families

```toml
schema_version = 3          # v2 had no version key

[detect]
match_on = "head"
fold_ascii = true
strip_trailing_dims = true
ikea_style = true           # "NAME, type, colour, dims": the head is the second comma segment
# the head phrase ends at the first of these (note: NOT at "in": "bed in a bag")
head_cut = '\s(?:with|w/|including|includes|featuring|by|for|from|plus|and|&|\+)\s|[,:(\[;|]|\s-\s'
# "bed frame in walnut" -> "bed frame"; "bed in a bag" is left intact (the lookahead refuses "in a/an ..."); "3 in 1 crib" is left intact (no digit on either side of "in");
# "plug in wall sconce", "walk in closet", "built in bookcase" and "slide in" are left intact (the lookbehinds refuse a verb particle before "in")
tail_strip = '(?<!\d)(?<!plug)(?<!walk)(?<!built)(?<!drop)(?<!roll)(?<!slide)(?<!lay)(?<!fold)(?<!clip)(?<!snap)\s(?:in)\s(?!\d|an?\s)[\w\s/&.-]+$'
# trailing colour and material words are not part of the head ("velvet sofa grey" -> "velvet sofa", "dining table walnut" -> "dining table"); at least one word always remains.
# Deliberately absent: olive, sage, rose, lavender, orange, cherry, pine, coral (they are also plant names: "faux olive", "artificial rose")
trail_finish = '(?:\s(?:black|white|grey|gray|beige|cream|ivory|brown|tan|taupe|navy|blue|green|teal|turquoise|aqua|red|burgundy|maroon|pink|blush|yellow|mustard|purple|rust|terracotta|gold|silver|bronze|brass|copper|chrome|charcoal|natural|espresso|walnut|oak|mahogany|ebony|teak|anthracite|multi|multicolou?red?|clear|wood|wooden|metal|fabric|velvet|(?<!bed\s)(?<!bath\s)(?<!table\s)(?<!kitchen\s)linen|leather|boucle|rattan|wicker|marble|glass|faux|solid|engineered))+$|\s\d[- ]?in[- ]?\d$|\s(?:only|alone)$|(?<!\sof)\s\d{1,2}[- ]?(?:doors?|drawers?|shelf|shelves|tiers?|seaters?|seats?)$'
# the extra alternatives drop (in order) a trailing multi-use count ("Convertible Crib 3 in 1" -> "convertible crib"), "only" or "alone" ("Queen Headboard Only") and a trailing
# count of doors, drawers, shelves or seats ("Wardrobe 3 Door", "Dresser 6 Drawer", "Sofa 3 Seater"). A LEADING "3 in 1 crib" or "6 drawer dresser" needs nothing: the match patterns are anchored at the end only.
# The (?<!\sof) guard keeps "Chest of 6 drawers" whole (the count belongs to the noun phrase there; without the guard the head collapses to "chest of").
# "linen" is not stripped after bed, bath, table or kitchen: "Bed Linen" is bedding and "Table Linen" is a textile (stripping gave the heads "bed" and "table").
# a brand whose name contains a head_cut separator ("&", "and", "+") is removed from the front of the folded title BEFORE the head is cut; without this "Sand & Stable Ethan 24'' Round Side Table" has the head "sand".
# Wayfair and Amazon put the brand first. Add a brand here when a probe shows a one-word head; the list is deliberately short and anchored at the start.
brand_strip = '^(?:sand & stable|joss & main|crate & barrel|better homes & gardens|hearth & hand|stone & beam|room & board|bed bath & beyond|mack & milo|isabelle & max|ophelia & co\.?|viv \+ rae|lulu (?:&|and) georgia|drew & jonathan)\s+'
passes = ["match", "match_low", "breadcrumb", "vlm", "queue"]
breadcrumb_depth = 2        # last two crumbs, then the URL slug
vlm_min_confidence = 0.80
queue_below = 0.80          # below this the job goes to the human queue with the top-3 leaves

[vocab]
hosts = ["fl", "wl", "ce", "su"]
builders = ["tripo", "rug", "art", "box", "lathe", "drape", "slab", "cushion", "cards", "hybrid", "skip"]
scales = ["box", "uniform_height", "uniform_width", "thickness", "footprint"]   # uniform_width: ceiling items, whose drop is rebuilt separately
props = ["tv", "books", "decor", "plants", "pillows", "throws", "lamps", "dishes", "food", "clothes", "toys", "people", "pets", "monitor", "mirror", "frames", "furniture"]   # vocabulary of [triage.avoid]
views = ["signature", "side", "front", "back", "top", "detail"]
postprocess = ["lamp", "bed", "net", "weave", "close_back", "glass_top", "glass_door", "glass_mirror",
               "chain", "pivot_cb", "pivot_top", "pivot_back", "flatten_back", "rectify", "laf_raf",
               "plant_pot_combine", "soil_disc", "strip_props", "tilt", "fold", "pleat", "cord_strip"]
flags = ["T", "Th", "S", "Em", "Ho", "Fu"]

[host_map]                  # placement column written to assets_input.host
fl = "face-based"           # floor (the catalog default)
wl = "wall-based"           # wall; MUST be written for sconces and wall shelves
ce = "ceiling-based"        # no app behaviour yet (grep of src found none)
su = "face-based"           # rests on a surface; the app decides from isStackableSize / canRestOnHost

[defaults]
builder = "tripo"
quads = 2500
host = "fl"
resizable = false           # vendor-linked products are never resizable
scale = "box"
views = ["side", "signature", "front"]    # v2 single_order
postprocess = []            # a leaf's list REPLACES its family's list; v2 `close_back = true` is now the postprocess entry "close_back"
multi_image = false
set = "split"               # never feed a set shot to image-to-3D
front = "-z"                # catalog GLBs face local -Z
pivot = "center_bottom"

[family.seating]
host = "fl"
quads = 3500
flags = ["S", "Th"]
[family.tables]
quads = 2000
flags = ["Th"]
[family.bedroom]
quads = 2500
[family.storage]
quads = 2500
postprocess = ["close_back"]
[family.lighting]
scale = "uniform_height"
quads = 3000
flags = ["T", "Th"]
[family.rugs]
builder = "rug"
quads = 6
scale = "footprint"
resizable_house = true
postprocess = ["rectify"]
[family.wall_decor]
host = "wl"
scale = "thickness"
postprocess = ["flatten_back"]
[family.tabletop]
host = "su"
scale = "uniform_height"
quads = 1000
flags = ["T"]
[family.plants]
scale = "uniform_height"
quads = 3000
flags = ["Th", "Fu"]
[family.textiles]
host = "su"
quads = 600
flags = ["S"]
[family.outdoor]
quads = 3500
flags = ["Th", "Ho"]
[family.kids]
quads = 2500
flags = ["Th"]
[family.kitchen_bath]
quads = 2500
[family.appliances]
quads = 2500
flags = ["T", "Em"]
[family.pet_fitness]
quads = 3500
[family.control]
builder = "skip"
```

### 4.2 Routing, stages 1 and 2 (control entries, then compounds that must beat a generic head noun)

Resolution order: every `[[category]]` is tried in file order inside a pass. Stage 1 (control) first, then stage 2 (compounds and ctx-gated variants: kids, pet, game, fitness, outdoor), then stage 3 (the ordinary leaves, 4.3 and 4.4), then pass 2 (`match_low`), then `other`. "Outdoor" leaves carry `ctx = "outdoor"`: their `match_ctx` patterns only count when `[modifier.outdoor]` matches the title or the last two breadcrumbs.

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 1  control: a hit is a skip with a reason, and the job goes to the review queue.
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "x_accessory"
family = "control"
label = "Not a 3D product (cover, topper, pad, skirt, runner, rod, shade, mount, part, swatch, card)"
match = [
  '\b(slip ?covers?|sofa covers?|couch covers?|chair covers?|furniture covers?|mattress (toppers?|protectors?|pads?|covers?|encasements?)|bed (skirts?|trays?|rails?|risers?|runners?|bumpers?|wedges?)|rug (pads?|grippers?|tape|underlay)|carpet (pads?|tape)|table (runners?|cloths?|linens?|mats?|placemats?|toppers?|skirts?)|stair (runners?|treads?)|placemats?|napkins?|coasters?|tablecloths?)$',
  '\b(curtain|drapery|shower|window) (rods?|poles?|tracks?|hooks?|rings?|tie ?backs?|holdbacks?|finials?|brackets?)$',
  '\b(lamp ?shades?|lamp bases?|(tv|television|monitor|projector|speaker)( \w+)? (mounts?|brackets?)|pillow ?cases?|pillow (protectors?|inserts?|forms?|shams?)|(euro |standard |king |queen |bed )?shams?|fireplace (tools?|screens?|grates?|pokers?)|(sofa|bed|table|chair|desk|furniture) legs?|furniture (pads?|sliders?|risers?)|(gift|e[- ]?gift) cards?|warranty|protection plans?|swatch(es)?|fabric samples?|cushion inserts?)$',
  '\b(replacement|spare) \w+( \w+)?$',
]
builder = "skip"
quads = 0

# ---------------------------------------------------------------------------------------------------
# STAGE 2a  compounds whose last word is also another leaf's head noun (bed, table, chair, tree, bench)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "hall_tree"
family = "storage"
label = "Hall trees, coat racks, hat stands"
match = ['\b(hall|coat|hat|umbrella|garment|clothes|clothing|mudroom|entryway|entry) (trees?|racks?|stands?)$', '\bhall stands?$']
match_title = ['\b(bench|storage bench|entryway bench|shoe bench)\b.*\b(with|w/)\b.*\b(hooks?|coat rack|hall tree|shoe rack)\b']
exclude = ['\b(cat|plant|towel|jewelry|jewellery|key|mug|bag|display|shelf|ladder)\b']
quads = 3000
postprocess = []                         # open frame: overrides the storage family's close_back
dims = { h = [100, 220], l = [30, 150] }
flags = ["Th"]
catalog = "Hall Trees"
na = true

[[category]]
key = "game_table"
family = "pet_fitness"
label = "Game tables (pool, ping pong, foosball, air hockey, poker, arcade)"
match = [
  '\b(pool|billiards?|snooker|ping[- ]?pong|table tennis|poker|card|game|gaming|arcade|shuffleboard|air hockey|foosball|chess|checkers?|multi[- ]?game|casino|bumper pool) (tables?|cabinets?|machines?)$',
  '\b(foosball|pinball|air hockey|shuffleboard|bumper pool|table tennis)( tables?| machines?)?$',
]
quads = 3500
dims = { h = [30, 130], l = [60, 320] }
flags = ["Th"]
catalog = "Gaming"

[[category]]
key = "fitness_machine"
family = "pet_fitness"
label = "Fitness machines and racks"
match = ['\b(treadmills?|exercise bikes?|stationary bikes?|spin(ning)? bikes?|rowing machines?|rowers?|ellipticals?|elliptical (machines?|trainers?)|cross trainers?|power racks?|squat racks?|kettlebells?|dumbbells?|barbells?|pull[- ]?up bars?|home gyms?|punching bags?|inversion tables?|stair ?steppers?|smith machines?|cable machines?|lat pulldowns?|exercise (equipment|machines?|balls?)|gym (equipment|bench(es)?)|trampolines?|rebounders?|weight (benches|bench|sets?|plates?|racks?)|workout (benches|bench|stations?)|ab (benches|bench|rollers?|machines?)|fitness (machines?|equipment)|peloton)$']
builder = "tripo"
alt = "skip"
quads = 6000
dims = { h = [20, 210], l = [30, 230] }
flags = ["Th"]
catalog = ""
na = true

[[category]]
key = "pet_bed"
family = "pet_fitness"
label = "Pet beds"
match = ['\b(dog|cat|pet|puppy|kitten)( \w+)? beds?$', '\b(donut|calming|cuddler)( dog| cat| pet)? beds?$', '\b(dog|cat|pet) (sofas?|couch(es)?|nests?|mats?|cushions?|cots?|hammocks?|caves?|igloos?)$', '\bcat caves?$']
builder = "cushion"                       # round and oval donut, bolster and mat beds only; cave, tent and structured beds fail the gate
alt = "tripo"
proc_gate = true
quads = 1500
resizable_house = true
dims = { h = [5, 45], l = [30, 130] }
flags = ["S", "Fu"]
catalog = "Pets"

[[category]]
key = "pet_furniture"
family = "pet_fitness"
label = "Cat trees, crates, gates, kennels, litter enclosures"
match = [
  '\bcat (trees?|towers?|condos?|furniture|shelves|perch(es)?|walkways?|houses?|scratch\w*)\b',
  '\bscratching (posts?|boards?|pads?)$', '\bscratchers?$', '\bkennels?$', '\bdog ?houses?$',
  '\b(dog|pet|wire|folding|collapsible|travel|heavy duty) (crates?|cages?|houses?|gates?|pens?|playpens?|stairs|steps|ramps?|carriers?|strollers?|feeders?|feeding stations?|fences?|runs?|doors?)( furniture)?$',   # Wayfair's own category name is "Dog Crate Furniture"
  '\b(litter box(es)?|litter box enclosures?|litter enclosures?|bird ?cages?|aquariums?|fish tanks?|terrariums?)$',
  '\b(rabbit|bunny|guinea pig|chicken|hen|poultry|duck)( \w+)* (hutch(es)?|coops?|houses?|runs?|cages?)$', '\brabbit hutch(es)?$',
]
quads = 4000
dims = { h = [15, 210], l = [30, 140] }
flags = ["Th", "S"]
catalog = "Pets"

[[category]]
key = "kids_bed"
family = "kids"
label = "Kids and toddler beds, bunk, loft, trundle"
match = [
  '\b(toddler|kids?|childrens?|children|youth|junior|bunk|loft|trundle|cabin|house|race ?car|fire ?truck|twin over (twin|full)|full over (full|queen)|triple bunk|low loft)( \w+)* beds?( frame)?$',
  '\bbunk ?beds?$', '\bloft ?beds?$', '\btrundle( beds?)?$',
]
builder = "tripo"
postprocess = ["bed"]
quads = 10000
dims = { h = [30, 200], l = [140, 230] }
flags = ["Th"]
catalog = "Kids & Toddlers Beds"

[[category]]
key = "crib"
family = "kids"
label = "Cribs, cots, bassinets, play yards"
match = ['\bcribs?$', '\bcots?$', '\bcot ?beds?$', '\bbassinets?$', '\bcradles?$', '\bplay ?(pens?|yards?)$', '\bbaby beds?$']
exclude = ['\b(camp|camping|military|army)\b']
builder = "hybrid"
alt = "tripo"
postprocess = ["bed"]
quads = 4000
dims = { h = [60, 125], l = [85, 165] }
flags = ["Th"]
catalog = "Kids & Toddlers Beds"

[[category]]
key = "changing_table"
family = "kids"
label = "Changing tables and changer units"
match = ['\b(baby |diaper |nappy )?chang(ing|er) (tables?|stations?|dressers?|units?|toppers?)$', '\bchangers?$']
postprocess = ["close_back"]
quads = 2500
dims = { h = [60, 115], l = [50, 160] }
catalog = "Dressers & Chests"

[[category]]
key = "kids_table_set"
family = "kids"
label = "Kids tables, chairs, desks, stools, high chairs and booster seats"
match = [
  '\b(kids?|childrens?|children|toddler|youth|junior|play|activity|sensory|lego|water) (tables?|desks?|chairs?|stools?|bench(es)?|table and chairs?)$',
  '\b(kids?|childrens?|children|toddler|youth|junior) (craft|art|study|writing) (tables?|desks?)$',   # "Kids Craft Table"; a bare "Craft Table" is a hobby-room desk
  '\b(high ?chairs?|booster seats?|baby (chairs?|seats?))$',
]
quads = 1500
dims = { h = [20, 85], l = [25, 140] }
set_mixed = "split"
catalog = "Kids Bedroom Accessories"
```

### 4.3a Stage 2b: outdoor leaves (before every indoor leaf, so "outdoor sofa" never reaches `sofa`)

Unconditional patterns catch nouns that are outdoor by nature (fire pit, hammock, BBQ, adirondack). `match_ctx` patterns count only when the `outdoor` modifier (4.4) hits the title or the last two breadcrumbs. If a ctx-gated leaf finds no noun, the title falls through to the indoor leaves ("outdoor pillow" is a `pillow` with the `outdoor` flag).

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 2b  outdoor (unconditional nouns first, then ctx-gated ones)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "fire_pit"
family = "outdoor"
label = "Fire pits, fire tables, chimineas, patio heaters"
match = ['\bfire ?(pits?|bowls?|columns?|rings?)( tables?)?$', '\bfire tables?$', '\bfirepits?$', '\bchimineas?$', '\bpatio heaters?$']
match_ctx = ['\b(fireplaces?|heaters?)$']
ctx = "outdoor"
quads = 2500
postprocess = ["strip_props"]            # remove the baked flame and fire glass
dims = { h = [25, 220], l = [40, 200] }
flags = ["T"]
catalog = "Outdoor"

[[category]]
key = "hammock_swing"
family = "outdoor"
label = "Hammocks, hammock stands, porch swings, swing and hanging chairs"
match = ['\bhammocks?$', '\bhammock( \w+)? (stands?|chairs?|swings?)$', '\b(hanging|swing|egg|cocoon|bubble)( \w+)? chair stands?$', '\bhanging (egg )?chairs?$', '\bswing chairs?$', '\b(porch|patio|garden|hanging|rope) swings?$', '\bswing seats?$', '\bcocoon chairs?$']
quads = 4000                             # host is `fl` for stands; hanging seats are `ce` (no app support): the job card lets the operator flip it
dims = { h = [60, 260], l = [60, 400] }
flags = ["Th", "S"]
catalog = "Outdoor"

[[category]]
key = "patio_umbrella"
family = "outdoor"
label = "Patio umbrellas, parasols, cantilever umbrellas (modelled open)"
match = ['\b(patio|market|cantilever|offset|garden|beach|outdoor|pool|cafe|banana|rotating|tilting|solar|led|giant|sun|deck) umbrellas?$', '\bparasols?$']
match_ctx = ['\bumbrellas?$', '\bcabanas?$']
ctx = "outdoor"
builder = "hybrid"                       # lathe pole and base plus a ribbed cone canopy textured from the hero
alt = "tripo"
quads = 2500
dims = { h = [180, 330], l = [150, 420] }
flags = ["Th", "S"]
catalog = "Outdoor"                      # the generic allowed bucket (Decorations super); the natural DB category "Outdoor Accessories" (141) is NOT in ALLOWED_CATEGORIES

[[category]]
key = "bbq_grill"
family = "outdoor"
label = "BBQ grills, smokers, kamado, pizza ovens, outdoor kitchens"
match = ['\b(bbqs?|barbecues?|barbeques?|kamados?|smokers?|pizza ovens?|outdoor kitchens?|(charcoal|gas|pellet|propane|natural gas|kettle|flat ?top|offset|built[- ]in) (grills?|bbqs?|smokers?|griddles?)|(bbqs?|barbecues?|barbeques?) (grills?|smokers?|griddles?|islands?|carts?|trolleys?)|grill (carts?|islands?|trolleys?))$']
match_ctx = ['\bgrills?$', '\bgriddles?$']
ctx = "outdoor"
builder = "skip"                         # route to the fixtures library
alt = "tripo"
quads = 3000
dims = { h = [60, 200], l = [40, 220] }
flags = ["Th"]
catalog = "Kitchen Appliances"

[[category]]
key = "outdoor_lounger"
family = "outdoor"
label = "Sun loungers, outdoor chaises, zero-gravity chairs"
match = ['\bsun ?(loungers?|lounges?|beds?)$', '\bpool (loungers?|lounges?|chairs?)$', '\bzero gravity (chairs?|loungers?|recliners?)$']
match_ctx = ['\bchaise( lounges?| longues?)?s?$', '\bloungers?$', '\breclining (lounge|lounger|chairs?)s?$']
ctx = "outdoor"
quads = 5000
dims = { h = [25, 125], l = [150, 230] }
flags = ["Th", "Ho"]
catalog = "Outdoor Chairs"

[[category]]
key = "outdoor_daybed"
family = "outdoor"
label = "Outdoor daybeds (v2 HD route kept; carries its own cushions, no mattress is added)"
match_ctx = ['\bday ?beds?$', '\b(cabana|canopy|pool|patio|outdoor) beds?$']   # no "garden": "Raised Garden Bed" and "Garden Bed" are planters (4.3f)
ctx = "outdoor"
quads = 12000
multi_image = true
views = ["signature", "back"]
dims = { h = [30, 200], l = [150, 260] }
flags = ["S", "Th"]
catalog = "Day Beds"

[[category]]
key = "outdoor_sofa"
family = "outdoor"
label = "Outdoor sofas, sectionals, loveseats (AU: patio lounge)"
match_ctx = ['\b(sofas?|sectionals?|loveseats?|love seats?|couch(es)?|lounges?|settees?|corner (sofas?|lounges?))$']
ctx = "outdoor"
quads = 12000
multi_image = true
views = ["signature", "back"]
postprocess = ["weave"]                  # only when a wicker weave is detected
dims = { h = [55, 125], l = [90, 400] }
flags = ["S", "Th", "Ho"]
set_mixed = "skip"                       # "Garden Sofa Set" / "Patio Sofa Set" is a conversation set (sofa, chairs, table); "Set of 2 Outdoor Sofas" is explicit and stays identical
catalog = "Outdoor Sofas"

[[category]]
key = "outdoor_chair"
family = "outdoor"
label = "Outdoor and patio chairs, stools, adirondacks, folding camp chairs"
match = ['\b(adirondack|beach|camp|camping|lawn|directors?|deck)( \w+)* chairs?$', '\bdeck ?chairs?$', '\badirondacks?$']
match_ctx = ['\b(chairs?|armchairs?|stools?|barstools?|rockers?|gliders?)$']
ctx = "outdoor"
quads = 3500
dims = { h = [40, 130], l = [35, 130] }
flags = ["Th", "Ho"]
catalog = "Outdoor Chairs"

[[category]]
key = "outdoor_table"
family = "outdoor"
label = "Outdoor dining, bistro, coffee, side and picnic tables"
match = ['\bpicnic tables?$', '\bbistro sets?$']
match_ctx = ['\btables?$']
ctx = "outdoor"
postprocess = ["glass_top"]              # only when a glass or tile top is detected
quads = 2000
dims = { h = [20, 115], l = [30, 300] }
flags = ["T", "Th"]
set_mixed = "split"                      # "Outdoor Dining Table with 6 Chairs": the table and the chair become two jobs. A bare "Patio Dining Set" names no piece: it routes to `other`, whose action is skip (human queue), whatever the kind label says
catalog = "Outdoor Dining Tables"
```

### 4.3b Stage 3, F1 seating (13 leaves)

Order inside the family is specific before generic: recliner, sectional, loveseat, daybed, chaise, sofa, bean bag, office chair, dining chair, bar stool, accent chair (the `chairs?$` catch-all), ottoman, bench. Anchoring on `$` is what keeps "sofa table", "bed bench" and "sofa cover" away from these leaves.

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F1 seating
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "recliner"
family = "seating"
label = "Recliners, lift chairs, massage chairs (modelled closed)"
match = ['\brecliners?$', '\b(reclining|lift|power lift|massage|power|manual|rocker) chairs?$', '\bwall ?hugger$']
match_title = ['\brise (and|&|n) recline\b']   # "Rise & Recline Chair": the head cut removes "and" and "&" (the head is "rise"), so only the full title can see the phrase; a bare "Zero Gravity Chair" is an outdoor_lounger
quads = 6000
postprocess = ["pivot_cb"]               # reject "reclined" views by VLM; model closed dims
dims = { h = [75, 125], l = [60, 120] }
catalog = "Recliner"

[[category]]
key = "sectional"
family = "seating"
label = "Sectionals, modular sofas, LAF/RAF pieces, sofa chaises"
match = ['\bsectionals?\b', '\b(modular|corner|l[- ]shaped|u[- ]shaped|curved|wedge|reversible) (sofas?|couch(es)?|lounges?|suites?|sofa[- ]?beds?)$', '\bchaise (sofas?|couch(es)?|suites?)$', '\b(sofa|couch|loveseat|love seat) chaises?$', '\b(laf|raf|lhf|rhf|left[- ]arm[- ]facing|right[- ]arm[- ]facing|left[- ]hand[- ]facing|right[- ]hand[- ]facing)\b', '\b(sofa|couch|sectional|lounge|armless|corner|middle|center|centre|chaise|wedge|ottoman|armchair|seat)( chair| sofa| couch| seat)? (modules?|sections?)$']
quads = 12000
multi_image = true
views = ["signature", "back"]
postprocess = ["pivot_cb", "laf_raf"]    # flip X when the chaise side in the render disagrees with the title
dims = { h = [55, 125], l = [150, 520] }
catalog = "Sectional Sofas"

[[category]]
key = "loveseat"
family = "seating"
label = "Loveseats and 2-seaters (v2 missed the two-word spelling)"
match = ['\blove ?seats?\b', '\b(2|two)[- ]?seat(er|ers)?( (sofas?|couch(es)?|lounges?))?$', '\bsnugglers?$']
quads = 6000
multi_image = true
views = ["signature", "back"]
postprocess = ["pivot_cb"]
dims = { h = [55, 125], l = [110, 210] }
set_mixed = "skip"                       # "Sofa and Loveseat Set" is routed to `sofa` by the first head word; a bare "Loveseat Set" is still two different pieces
catalog = "Loveseat"

[[category]]
key = "daybed"
family = "seating"
label = "Indoor daybeds (v2 sent every daybed to the outdoor 12,000-quad route)"
match = ['\bday ?beds?\b']
quads = 8000
postprocess = ["bed"]                    # mattress added only to an empty frame
dims = { h = [30, 200], l = [150, 260] }
flags = ["Th"]
catalog = "Day Beds"

[[category]]
key = "chaise_lounge"
family = "seating"
label = "Indoor chaise lounges"
match = ['\bchaises?( lounges?| longues?| chairs?)?$', '\bchaise (lounges?|longues?)\b', '\bindoor chaises?\b']
quads = 5000
postprocess = ["pivot_cb"]
dims = { h = [55, 115], l = [100, 230] }
catalog = "Accent Chair"

[[category]]
key = "sofa"
family = "seating"
label = "Sofas, couches, sleepers, futons, settees (AU: lounge)"
match = ['\b(sofas?|couch(es)?|settees?|sleepers?|futons?|chesterfields?|davenports?|lounges?)$', '\b(sofa|couch|settee)[- ]?(beds?|sleepers?)$', '\bsleeper (sofas?|chairs?)$', '\b(2\.5|3|three|4|four)[- ]?seat(er|ers)?( (sofas?|couch(es)?|lounges?))?$']
quads = 12000
multi_image = true
views = ["signature", "back"]
postprocess = ["pivot_cb"]
dims = { h = [55, 125], l = [140, 340] }
set_mixed = "skip"                       # "Sofa Set", "3-Piece Sofa Set" and the AU "Lounge Suite" are a sofa plus a loveseat plus a chair: queue, never build one of them as the set
catalog = "Sofas"

[[category]]
key = "bean_bag"
family = "seating"
label = "Bean bags, lounge sacks, floor pillows and floor cushions"
match = ['\bbean ?bags?\b', '\blounge sacks?$', '\bsack chairs?$', '\bfloor (pillows?|cushions?)$']
builder = "cushion"
alt = "tripo"
proc_gate = true
quads = 800
dims = { h = [10, 110], l = [40, 200] }
flags = ["S"]
resizable_house = true
catalog = "Poufs"

[[category]]
key = "office_chair"
family = "seating"
label = "Office, task, executive, gaming and ergonomic chairs (HD, multi-image)"
match = ['\b(office|work|desk|task|executive|gaming|ergonomic|drafting|computer|conference|managers?|racing|reception|operator|typist|study|student|swivel desk)( \w+)? chairs?$']
quads = 10000
multi_image = true
views = ["signature", "back"]
postprocess = ["net", "pivot_cb"]        # `net` only when a mesh backrest is detected; pivot on the base axis
dims = { h = [75, 150], l = [45, 95] }
flags = ["Th", "Ho"]
catalog = "Office Chairs"

[[category]]
key = "dining_chair"
family = "seating"
label = "Dining, side, host, cafe and folding chairs (kitchen stools are bar stools)"
match = ['\bdining\b[\w\s-]*\b(arm ?)?chairs?$', '\b(side|parsons?|host|hostess|banquet|banquette|kitchen|cafe|bistro|windsor|carver|folding|stacking|armless|spindle|cross ?back|ladder ?back|slat ?back) chairs?$', '\bcarvers?$']
quads = 2000
dims = { h = [60, 130], l = [35, 80] }
flags = ["Th"]
catalog = "Dining Chairs"

[[category]]
key = "bar_stool"
family = "seating"
label = "Bar, counter, kitchen and breakfast stools (compare SEAT height)"
match = ['\b(bar|counter|counter[- ]height|bar[- ]height|swivel|backless|kitchen|breakfast|pub|island|saddle)( \w+)* stools?$', '\bbarstools?$', '\b(bar|counter)( \w+)* chairs?$', '\bcounter[- ]height chairs?$']
match_low = ['\bstools?$']               # a bare "stool" goes through [[dims_route]]: h under 55 cm becomes an ottoman
quads = 2000
dims = { h = [55, 125], l = [30, 60] }
flags = ["Th"]
catalog = "Bar & Counter Stools"

[[category]]
key = "accent_chair"
family = "seating"
label = "Accent, club, wing, barrel, swivel, rocking chairs (the `chairs?$` catch-all, after every specific chair)"
match = ['\barmchairs?$', '\bchairs?$', '\b(rockers?|gliders?|wing ?backs?|chair and a half)$']
quads = 3500
postprocess = ["weave"]                  # only when a cane or wicker panel is detected
dims = { h = [55, 130], l = [50, 130] }
catalog = "Accent Chair"

[[category]]
key = "ottoman"
family = "seating"
label = "Ottomans, poufs, hassocks, footstools, step stools"
match = ['\b(ottomans?|poufs?|pouffes?|hassocks?|foot ?stools?|foot ?rests?|step ?stools?|cube (ottomans?|poufs?))$', '\b(vanity|makeup|dressing|bathroom|shower)( \w+)? stools?$']
# a bare "Storage Cube" is a basket_bin (4.3d); "Cube Ottoman" and "Storage Cube Ottoman" still end in "ottoman"
quads = 1500                             # host stays `fl` (Poufs is floor-only); it is a stack HOST for a tray or a throw
postprocess = ["pivot_cb"]
dims = { h = [20, 60], l = [25, 160] }
catalog = "Poufs"

[[category]]
key = "bench"
family = "seating"
label = "Benches: entryway, end-of-bed, dining, storage, banquette"
match = ['\bbench(es)?$', '\bbanquettes?$', '\bsettles?$', '\bpews?$']
exclude = ['\b(work|workshop|potting|tool|lab|craft|sewing|weight|workout|gym|tv|television|media|entertainment)\b', '\bisland\b']   # "tv bench" (IKEA, UK) is a tv_stand; "kitchen island bench" (AU) is kitchen_island
quads = 1500
dims = { h = [30, 100], l = [60, 250] }
flags = ["Th"]
catalog = "Bedroom Benches"
```

### 4.3c Stage 3, F2 tables and desks (7 leaves) and F3 bedroom (7 leaves)

Table leaves exclude each other's head words instead of relying on file order alone: `side_table` refuses `dining|console|coffee|...`, so "pedestal dining table" and "side console table" still reach the right leaf. In F3, `storage_chest` precedes `chest_of_drawers` and `headboard` precedes `bed`; a mattress "in a box" is a mattress, but "bed in a bag" is bedding (4.3f).

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F2 tables and desks
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "coffee_table"
family = "tables"
label = "Coffee, cocktail, center and lift-top tables"
match = ['\b(coffee|cocktail|center|centre|occasional)( \w+)? tables?$', '\blift[- ]?top( \w+)? tables?$', '\bnesting( coffee| cocktail)? tables?$']
quads = 1500
postprocess = ["glass_top"]              # only when a glass top is detected (procedural pane, never metallic=1 with transmission)
dims = { h = [20, 80], l = [30, 250] }
flags = ["T", "Th"]
set_mixed = "split"                      # "Coffee Table and End Tables Set"; "Nesting Coffee Table Set of 2" is an identical set (`set`)
catalog = "Coffee Tables"

[[category]]
key = "side_table"
family = "tables"
label = "Side, end, accent, drink, C and lamp tables; plant stands"
match = ['\b(side|end|accent|drink|snack|lamp|chairside|chair side|martini|magazine|telephone|phone|corner|round end|sofa end|couch end|tray|tv tray)( \w+)? tables?$', '\bc[- ]?tables?$', '\bnesting (end|side|accent) tables?$', '\bnests? of (?:(?:\d+|two|three|four) )?(?:(?:side|end|accent) )?tables?$', '\bplant stands?$']
# "pedestal" is not a key word here: a bare "Pedestal Table" is a dining or bistro table (dining_table match_low); "Pedestal Side/End Table" still match on side/end.
# "farmhouse", "extension" and "extendable" are not excluded: "Rustic Farmhouse End Table" and "Extendable Side Table" are side tables (the 2026-10-22 stress sweep).
# "Nest of Coffee Tables" is a coffee_table (the exclude below says so); "Nest of 3 Tables" and "Nest of Side Tables" are side tables.
exclude = ['\b(console|dining|kitchen|breakfast|dinette|bar|pub|counter|bistro|conference|trestle|banquet|coffee|cocktail|nightstand|bedside|desk|writing|study|vanity|dressing|makeup)\b']
quads = 1500
postprocess = ["glass_top"]
dims = { h = [20, 85], l = [25, 120] }
flags = ["T", "Th"]
catalog = "Side Tables"

[[category]]
key = "console_table"
family = "tables"
label = "Console, sofa, entryway and hall tables (open back: NO close_back)"
match = ['\b(console|sofa|couch|entryway|entry|hall|hallway|foyer|behind[- ]the[- ]sofa|narrow)( \w+)? tables?$', '\bconsoles?$']
exclude = ['\b(media|tv|television|entertainment|gaming|game|video|audio|stereo|fireplace)\b']
quads = 2000
dims = { h = [65, 120], l = [60, 220] }
flags = ["Th"]
catalog = "Console Tables"

[[category]]
key = "dining_table"
family = "tables"
label = "Dining, kitchen, breakfast, pub, bar and counter-height tables"
match = ['\b(dining|kitchen|breakfast|dinette|pub|bar|counter[- ]height|bar[- ]height|bistro|cafe|farmhouse|trestle|extension|extendable|drop[- ]leaf|gate[- ]?leg(ged)?|butterfly|banquet|conference|meeting|gathering|harvest|expandable)\b[\w\s-]*\btables?$']
match_low = ['\b(round|oval|square|rectangular|rectangle|folding|marble|glass|wood|wooden|solid wood|pedestal)( \w+)* tables?$', '^tables?$']
exclude = ['\bisland\b']
quads = 2000
postprocess = ["glass_top"]
dims = { h = [65, 115], l = [60, 400] }
flags = ["T", "Th"]
set_mixed = "split"                      # "7 Piece Dining Table Set", "Dining Table with 4 Chairs": the table is one job, a chair gallery shot is another (the chair is routed on its own). A bare "5-Piece Dining Set" names no piece: it routes to `other`, whose action is skip (human queue), whatever the kind label says
catalog = "Dining Tables"

[[category]]
key = "standing_desk"
family = "tables"
label = "Standing, sit-stand and height-adjustable desks (modelled at the lowest height)"
match = [
  '\b(standing|sit[- ]?(to[- ])?stand|height[- ]adjustable|adjustable[- ]height|electric|motori[sz]ed|lift|stand[- ]up|variable[- ]height)\b[\w\s-]*\b(desks?|work ?stations?)$',
  '\bdesks? (sit ?[/-] ?stand|sit[- ]?stand|standing|height[- ]adjustable|electric)$',   # IKEA type phrase: "BEKANT, Desk sit/stand, white, 160x80 cm"
]
builder = "hybrid"                       # parametric frame (two legs, feet, crossbar) plus a Tripo top
alt = "skip"
quads = 2500
dims = { h = [60, 130], l = [80, 260] }
catalog = "Desks"

[[category]]
key = "desk"
family = "tables"
label = "Desks: writing, computer, L-shaped, corner, secretary, executive, gaming"
match = ['\bdesks?$', '\b(writing|computer|study|drafting|craft|sewing|work|office|gaming|executive|laptop|student|school|home office)( \w+)? (tables?|stations?)$', '\bsecretar(y|ies|aires?)$', '\bwork ?stations?$']
exclude = ['\b(vanity|makeup|make-?up|dressing|cosmetic|beauty)\b']      # "Vanity Desk" is `vanity_table`, which comes next
quads = 2000
dims = { h = [65, 190], l = [60, 260] }
catalog = "Desks"

[[category]]
key = "vanity_table"
family = "tables"
label = "Makeup vanities and dressing tables (a bathroom vanity is `bath_vanity`)"
match = ['\b(vanity|makeup|make-?up|dressing|cosmetic|beauty)( \w+)? (tables?|desks?)$', '\bdressing tables?$', '\b(makeup|make-?up|cosmetic|beauty) vanit(y|ies)$']
match_low = ['\bvanit(y|ies)$']             # a bare "vanity" is ambiguous (bath or makeup): the VLM check chooses between this leaf and `bath_vanity`. "Vanity with Sink" never gets here: `bath_vanity.match_title` fires in pass 1
exclude = ['\b(bath|bathroom|sink|basin|washstand|lavatory|powder room|single sink|double sink)\b']
quads = 2500
dims = { h = [70, 170], l = [60, 160] }
flags = ["T", "Th"]
catalog = "Desks"                        # closest allowed name; DB "Vanity Stands & Tables" (58) is NOT in ALLOWED_CATEGORIES (5.5)

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F3 bedroom
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "headboard"
family = "bedroom"
label = "Headboards (no mattress is added; v2 sent these to `bed`)"
match = ['\bheadboards?$', '\bbed ?heads?$', '\bfootboards?$', '\bheadboard (bookcase|storage)$']   # "Headboard Bench" is a bench (the storage bench with a back)
views = ["front", "signature", "side"]
quads = 2500
postprocess = ["flatten_back"]
dims = { h = [40, 200], l = [60, 230] }
flags = ["S"]
catalog = "Queen Headboard"

[[category]]
key = "nightstand"
family = "bedroom"
label = "Nightstands and bedside tables"
match = ['\bnight ?stands?$', '\bnite ?stands?$', '\bbedside (tables?|cabinets?|chests?|drawers?|units?|pedestals?)$', '\bnight tables?$', '\bbedside$', '\b(bedside|night)( \w+)? (tables?|stands?|cabinets?|chests?)$']
quads = 2500
dims = { h = [35, 95], l = [30, 95] }
flags = ["Th"]
catalog = "Nightstands"

[[category]]
key = "bed"
family = "bedroom"
label = "Beds and bed frames (10,000 quads; mattress added only to an empty frame)"
match = ['\bbeds?$', '\bbed ?frames?$', '\bbedsteads?$', '\bbed ?bases?$', '\b(four|4)[- ]?posters?$', '\bdivans?( beds?| bases?)?$']
exclude = ['\b(air|inflatable|water|massage|tanning|flower|garden|raised|plant|planter|vegetable|veggie|herb|hospital|medical)\b']
quads = 10000
postprocess = ["bed"]
bed_frame_photo = true                   # prefer the frame-only photo when one exists
dims = { h = [20, 200], l = [180, 260] }
flags = ["Th"]
catalog = "Beds"

[[category]]
key = "storage_chest"
family = "bedroom"
label = "Blanket chests, trunks, toy boxes, hope and cedar chests (before `chest_of_drawers`)"
match = ['\b(blanket|toy|hope|cedar|treasure|steamer|pirate|dowry|linen|bedding|quilt)( \w+)* (chests?|trunks?|box(es)?)$', '\bstorage (chests?|trunks?)$', '\b(trunks?|coffers?|cassones?)$', '\b(wood|wooden|vintage|antique|rustic|leather)( \w+)? (chests?|trunks?)$']
exclude = ['\bin an? (box|bag)\b']   # "Bedding in a Box" and "Quilt in a Bag" are bedding_set (4.3f); "Bed in a Box" is a mattress
quads = 1500
dims = { h = [25, 90], l = [40, 160] }
flags = ["Th"]
catalog = "Accent Chests"

[[category]]
key = "chest_of_drawers"
family = "bedroom"
label = "Dressers, chests of drawers, bureaus, tallboys, lowboys"
match = ['\b(dressers?|chests? of (?:(?:\d+|two|three|four|five|six|seven|eight) )?drawers|bureaus?|lowboys?|tallboys?|highboys?|chiffoniers?|semainiers?|drawer chests?|bedroom chests?|accent chests?)$', '\b(\d+|two|three|four|five|six|seven|eight)[- ]drawer( \w+)? (chests?|dressers?|cabinets?|units?)$', '\bchests?$']
exclude = ['\b(welsh|kitchen|plate|display|dining|china)\b']
quads = 2500
postprocess = ["close_back"]
dims = { h = [45, 170], l = [40, 200] }
flags = ["Th"]
catalog = "Dressers & Chests"

[[category]]
key = "wardrobe"
family = "bedroom"
label = "Wardrobes, armoires, freestanding closets"
match = ['\b(wardrobes?|armoires?|closets?|wardrobe closets?|clothes closets?|clothing armoires?)$', '\bwardrobe (cabinets?|units?)$']
exclude = ['\b(tv|television|media|entertainment|linen|bath|bathroom|towel|kitchen|pantry|broom|cleaning|utility|coat|water|toilet)\b', '\b(china|curio|display|shoe|wine|liquor|jewel(l)?e?ry|gun|trophy)\b']   # those are accent_cabinet or hall_tree; a china closet is display_cabinet, a shoe closet or a jewellery armoire is accent_cabinet
quads = 2500
postprocess = ["close_back"]             # doors closed in the model, back panel capped
dims = { h = [100, 260], l = [40, 300] }
catalog = "Wardrobe"

[[category]]
key = "mattress"
family = "bedroom"
label = "Mattresses, box springs, foundations (toppers and protectors are control entries)"
match = ['\bmattress(es)?$', '\bmattress(es)? in an? box$', '\bbed in an? box$', '\bbox ?springs?$', '\b(bed )?foundations?$', '\bbunkie boards?$']
builder = "box"                          # rounded box from the locale size table, quilted texture from the hero
quads = 200
views = ["signature"]
resizable_house = true
dims = { h = [8, 50], l = [60, 260] }
flags = ["S"]
catalog = "Mattress - Queen Size"
```

### 4.3d Stage 3, F4 storage (8 leaves; `hall_tree` is in 4.2) and F5 lighting (8 leaves)

Inheritance rule used here and in every block: a leaf's `postprocess` and `flags` lists REPLACE the family's lists (they do not merge), so open-frame storage leaves state `postprocess = []`. Storage order is tv_stand, display_cabinet, bookcase, file_cabinet, sideboard, accent_cabinet (the `cabinets?$` catch-all), basket_bin, room_divider. Lighting order is by mounting plane so the catch-all `lamps?$` is last: wall, ceiling (fan, chandelier, pendant, flush), floor, desk, table. A bare "lamp" becomes `table_lamp` and `[[dims_route]]` (4.4) sends it to `floor_lamp` when the listed height is 115 cm or more.

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F4 storage and media
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "tv_stand"
family = "storage"
label = "TV stands, media consoles, entertainment centers and units (AU: TV unit, entertainment unit; IKEA: TV bench)"
match = [
  '\b(tv|television|media|entertainment|home theat(er|re)|lowline|low[- ]line)( \w+)* (stands?|consoles?|units?|centers?|centres?|cabinets?|bench(es)?|lowboards?|credenzas?|walls?|furniture|racks?|tables?|storage|towers?)$',
  '\bentertainment (centers?|centres?|units?|walls?|consoles?|systems?)$',
  '\bfireplace (tv )?(stands?|consoles?|entertainment centers?)$',
]
exclude = ['\b(tray|mount|mounts|bracket|brackets)\b']
quads = 2500                             # postprocess close_back comes from the family; reject views that show a TV ([triage.avoid])
dims = { h = [25, 210], l = [70, 320] }
catalog = "TV Console"

[[category]]
key = "display_cabinet"
family = "storage"
label = "Display, curio, china, bar and wine cabinets, hutches, vitrines, glass-door bookcases"
match = [
  '\b(display|curio|china|vitrine|trophy|collectors?|glass[- ]?door|glazed|lighted|led)( \w+)* (cabinets?|cases?|cupboards?|units?)$',
  '\bhutch(es)?$', '\bcurios?$', '\bvitrines?$', '\bchina (closets?|cupboards?|cabinets?)$',
  '\b(bar|wine|liquor|barware|drinks?|bottle|cocktail)( \w+)* (cabinets?|cupboards?)$',
]
# v2 sent "Bookcase with Glass Doors" to the cabinet route by accident; here it is deliberate (the head is cut at "with")
match_title = ['\b(book ?cases?|book ?shelf|book ?shelves|cabinets?|etageres?|shelving units?|display units?|storage units?)\b.*\b(with|w/)\b.*\b(glass|glazed|mirrored|acrylic)\b.*\b(doors?|panels?|fronts?)\b']
exclude = ['\b(rabbit|bunny|guinea pig|chicken|hen|poultry|pet|dog|cat|bathroom|bath|medicine|kitchen|pantry|file|filing|shoe|tv|media|entertainment|cooler|fridge|refrigerator|jewelry|jewellery|watch|gun|rifle|knife|wall)\b', '\b(shelf|shelves|shelving|etageres?)\b']   # "Display Shelving Unit" is a bookcase; a bare "Display Unit" stays here
builder = "hybrid"                       # Tripo carcass plus procedural glass doors
alt = "tripo"
quads = 2500
postprocess = ["close_back", "glass_door"]
dims = { h = [60, 260], l = [30, 200] }
flags = ["T", "Th"]
catalog = "Cabinets"

[[category]]
key = "bookcase"
family = "storage"
label = "Bookcases, bookshelves, etageres, shelving units, cube organizers, ladder and leaning shelves, free-standing wine racks"
match = [
  '\bbook ?(cases?|shelf|shelves|racks?)$', '\bbookshelves$', '\betageres?$',
  '\b(shelving|shelf|display|storage|cube|cubby|bakers?)( \w+)* (units?|systems?|racks?|organi[sz]ers?)$',
  '\b(ladder|leaning|corner|open|standing|free[- ]?standing|tiered|\d+[- ]tier|\d+[- ]shelf|\d+[- ]cube|cube|storage|display) (shelf|shelves|shelving)$',
  '\bcubbies$', '\bcubby (storage|shelf|shelves)$', '\bwire shelving$', '\bshelving$',
  '\b(blanket|quilt) (ladders?|racks?|stands?)$',
  '\bwine (racks?|shelf|shelves|storage|holders?|stands?)$',          # a free-standing wine rack is open lattice shelving; `wall`/`mounted` ones are excluded below and fall to the human queue
]
match_low = ['\bshelf$', '\bshelves$']       # a bare "wall unit" (a TV wall unit or a wall shelf) is deliberately unmatched: the human queue
exclude = ['\b(wall|floating|hanging|mounted|ledge|picture|spice|shower|rabbit|bunny)\b']
quads = 2500
dims = { h = [30, 260], l = [25, 250] }  # close_back from the family; the `ladder` modifier bakes the lean
flags = ["Th"]
catalog = "Bookcases"

[[category]]
key = "file_cabinet"
family = "storage"
label = "File and filing cabinets, lateral files, mobile pedestals, drawer units"
match = [
  '\b(file|filing)( \w+)* (cabinets?|units?|drawers?|pedestals?|carts?)$', '\b(lateral|vertical|mobile|rolling|fireproof|locking) (file|filing)s?( cabinets?)?$',
  '\bfiling cabinets?$', '\bmobile pedestals?$', '\bpedestal (drawers?|units?)$', '\bdrawer (pedestals?|units?)$',
]
quads = 2500
dims = { h = [40, 200], l = [30, 120] }
catalog = "Filling Cabinets"             # sic: the DB name

[[category]]
key = "sideboard"
family = "storage"
label = "Sideboards, buffets, credenzas, lowboards (W 48-80 in, D 14-20 in, H 28-38 in)"
match = ['\b(sideboards?|buffets?|credenzas?|lowboards?|low boards?)$', '\bbuffet (tables?|cabinets?|servers?|sideboards?)$', '\bdining (servers?|buffets?|sideboards?)$', '\bside (cabinets?|units?)$', '\bconsole cabinets?$']
quads = 2500
dims = { h = [45, 130], l = [80, 260] }
catalog = "Buffets and Credenzas"

[[category]]
key = "accent_cabinet"
family = "storage"
label = "Accent, storage, pantry, linen, bath and shoe cabinets, cupboards, lockers (the `cabinets?$` catch-all)"
match = [
  '\b(cabinets?|cupboards?|lockers?|pantr(y|ies)|larders?)$', '\bstorage (cabinets?|towers?|cupboards?)$',
  '\b(linen|bath|bathroom|toilet|spa) (towers?|storage|units?)$',
  '\b(jewel(l)?e?ry|wine|liquor|gun|china|curio|trophy|display|shoe) armoires?$',   # these armoires are not wardrobes (the wardrobe exclude lets them through)
  '\bshoe (cabinets?|racks?|shelf|shelves|storage|organi[sz]ers?|closets?)$',
  '\b(grandfather|grandmother|longcase|long case|tall case|floor|standing) clocks?$',   # a floor clock is a tall closed cabinet; clock_wall excludes these words
]
exclude = ['\b(wall|medicine|hanging|floating|mounted|island)\b', '\b(vanit(y|ies)|(sink|basin) (cabinets?|units?|bases?)|under[- ]?(sink|basin))\b']   # wall, medicine and floating cabinets are wall items (wall_shelf, 4.3e); an island cabinet is kitchen_island; a vanity or sink cabinet is bath_vanity (4.3g)
quads = 2500
dims = { h = [30, 260], l = [25, 200] }
catalog = "Cabinets"                      # shoe racks: "Shoe Racks"; DB "Shoe Storage" (71) is NA

[[category]]
key = "basket_bin"
family = "storage"
label = "Baskets, bins, hampers, trash cans, storage boxes and crates"
match = ['\b(baskets?|hampers?|bins?|crates?|storage (boxes|box|cubes?|crates?|totes?|bins?|baskets?)|trash (cans?|bins?)|waste ?(baskets?|bins?|paper baskets?)|dust ?bins?|rubbish bins?|garbage (cans?|bins?)|laundry (hampers?|baskets?|bags?|bins?)|magazine (racks?|holders?|baskets?)|log (baskets?|holders?|carriers?|racks?)|toy (bins?|baskets?|chests?))$']
exclude = ['\b(gift|bike|bicycle|bait|fishing|shopping|ice|wine|champagne|beer|cooler|pet|dog|cat|picnic)\b', '\b(plant|planter|flower|hanging)\b']   # a plant or hanging basket is a planter (4.3f)
alt = "lathe"                            # a plain round bin is a lathe solid
quads = 1500
postprocess = []
dims = { h = [10, 90], l = [10, 90] }
flags = ["S", "Ho"]
catalog = "Storage"                       # host `fl` for hampers; [[dims_route]] makes it `su` for a basket of 40 cm or less

[[category]]
key = "room_divider"
family = "storage"
label = "Room dividers, folding and privacy screens, partitions, shoji screens (modelled unfolded)"
match = [
  '\b(room|space|privacy|folding|partition|shoji|japanese|decorative|wood|wooden|bamboo|rattan|garden|outdoor|office|panel|hinged|\d+[- ]panel)( \w+)* (dividers?|screens?|partitions?)( \d{1,2}[- ]?panels?)?$',   # a trailing panel count is allowed: "Room Divider Screen 4 Panel"
  '\b(dividers?|partitions?|paravents?|shoji)( \d{1,2}[- ]?panels?)?$', '\bfolding screens?( \d{1,2}[- ]?panels?)?$', '\bprivacy screens?( \d{1,2}[- ]?panels?)?$',
]
exclude = ['\b(projector|projection|tv|monitor|computer|laptop|phone|window|door|fireplace|fire|spark|mosquito|insect|fly|sun|shade|touch|lcd|led|drawer|cutlery|utensil|tray|file|binder|shelf|desk|cubicle|acoustic|radiator|heater|cover|guard|splash|sneeze|shower|bath|pool|fence)\b']
quads = 2500
postprocess = []
dims = { h = [90, 220], l = [40, 400] }
flags = ["Th", "Ho"]
catalog = "Room Divider"                  # the allowed name; the DB snapshot calls id 180 "Screens and Dividers" (NOT allowed): verify against the live DB, then rename the row or add an alias

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F5 lighting (wall, ceiling, floor, desk, table; the bare `lamps?$` catch-all is last)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "wall_sconce"
family = "lighting"
label = "Sconces, wall lights and lamps, vanity bars, picture lights, swing-arm lamps (host MUST be wall-based in the DB)"
match = [
  '\b(wall )?sconces?( (plug[- ]?in|hard[- ]?wired|battery|operated|powered|rechargeable|wireless|corded|cordless|led|dimmable|indoor|outdoor|lights?|lamps?|lighting))*$',   # "Wall Sconce Plug In", "Wall Sconce Battery Operated"
  '\bwall[- ]?(mounted|mount|hung)?( \w+)* (lights?|lamps?|lighting|sconces?|washers?)$',
  '\b(vanity|bathroom|bath|picture|swing[- ]arm|plug[- ]in|hardwired|bracket|gallery|art|mirror|over[- ]the[- ]mirror|cabinet|headboard) (lights?|lamps?|light bars?|lighting)$',
  '\bpicture lights?$', '\bvanity (light )?bars?$',
]
exclude = ['\b(floor|table|desk|standing|tripod|arc|clip|torchiere|string|fairy|strip|rope|tree|christmas|holiday|garland|candle|tea ?light|bulb|replacement)\b']
host = "wl"                               # the app's category heuristic does NOT match "Wall Lighting" (99 rows): the host column is the only thing that makes it a wall item
scale = "box"                             # arm extension is the depth
quads = 2000
postprocess = ["flatten_back", "pivot_back"]
dims = { h = [8, 100], l = [8, 140] }
catalog = "Wall Lighting"

[[category]]
key = "ceiling_fan"
family = "lighting"
label = "Ceiling fans (with or without a light kit; modelled with the blades at rest)"
match = ['\bceiling fans?$', '\bhugger fans?$', '\bfandeliers?$']
builder = "hybrid"                       # procedural blades plus a Tripo motor housing and light kit
alt = "tripo"
host = "ce"                              # no app behaviour yet: catalog-only until the app adds ceiling placement
scale = "box"
quads = 5000
postprocess = ["pivot_top"]
dims = { h = [15, 120], l = [70, 200] }
flags = ["Th"]
catalog = "Ceiling Lighting"

[[category]]
key = "chandelier"
family = "lighting"
label = "Chandeliers and multi-arm fixtures"
match = [
  '\bchandeliers?$',
  '\b(sputnik|linear|tiered|multi[- ]?tier|multi[- ]?arm|branch|candelabra|wagon wheel) (fixtures?|lights?|pendants?|lighting|suspension)$',
  '\b(multi[- ]?light|\d+[- ]?light|(two|three|four|five|six|seven|eight|nine|ten|twelve)[- ]light) (fixtures?|pendants?|chandeliers?)$',
]
host = "ce"
scale = "uniform_width"                  # the drop is adjustable: size by the listed width, rebuild the chain
quads = 6000
postprocess = ["chain", "pivot_top"]
dims = { h = [10, 250], l = [15, 220] }
catalog = "Ceiling Lighting"

[[category]]
key = "pendant"
family = "lighting"
label = "Pendant, hanging and suspension lights (mini, drum, cluster, globe)"
match = [
  '\bpendants?$', '\bpendant (lights?|lamps?|lighting|fixtures?)$', '\blight pendants?$',
  '\b(hanging|suspension|suspended|ceiling[- ]hung|drop|cord|swag|plug[- ]in hanging) (lights?|lamps?|lighting|fixtures?)$',
]
builder = "hybrid"                       # Tripo shade (about 2000 quads) plus procedural chain or cord and canopy
alt = "tripo"
host = "ce"
scale = "uniform_width"
quads = 2000
postprocess = ["chain", "pivot_top"]
dims = { h = [8, 250], l = [8, 150] }
catalog = "Ceiling Lighting"

[[category]]
key = "flush_mount"
family = "lighting"
label = "Flush and semi-flush mounts, ceiling lights, oyster lights (recessed and track lights are low confidence)"
match = [
  '\b(flush|semi[- ]?flush)( mount(ed)?)?( \w+)* (lights?|fixtures?|lamps?|lighting|ceiling lights?)$', '\bflush ?mounts?$', '\bsemi[- ]?flush( mounts?)?$',
  '\bceiling (lights?|lamps?|fixtures?|lighting)$', '\b(oyster|disc|disk|puck|panel|dome|saucer|plafonnier|bulkhead) (lights?|lamps?|fixtures?)$',
]
match_low = ['\b(down ?lights?|recessed( \w+)* (lights?|lighting|cans?)|spot ?lights?|track (lights?|lighting|heads?)|ceiling spots?)$']
builder = "tripo"
alt = "lathe"                            # a plain drum or disc is a lathe solid
host = "ce"
scale = "box"                            # diameter x depth (4-10 in)
quads = 1500
postprocess = ["flatten_back", "pivot_top"]   # flatten_back = flatten the MOUNTING face (the top for ceiling items)
dims = { h = [3, 45], l = [10, 120] }
flags = ["T"]
catalog = "Ceiling Lighting"

[[category]]
key = "floor_lamp"
family = "lighting"
label = "Floor, arc, tripod, torchiere and standing lamps"
match = ['\bfloor[- ]?(standing )?(lamps?|lights?|lighting)$', '\b(standing|standard|tripod|arc|pole|torchi?ere) (lamps?|lights?)$', '\buplighters?$', '\btorchi?eres?$']
uniform_scale_match = ['\barc\b', 'adjustable']   # unchanged from v2
host = "fl"
quads = 3000
postprocess = ["lamp"]                   # remove the floor cord, size by height
dims = { h = [55, 230], l = [15, 220] }  # an arc lamp overhangs 40-80 in from its base
catalog = "Floor Lamp"

[[category]]
key = "desk_lamp"
family = "lighting"
label = "Desk, task, clip, clamp, architect and study lamps"
match = ['\b(desk|task|clip[- ]?on|clip|clamp|architect|study|drafting|magnifying|gooseneck|workbench|work)( \w+)* (lamps?|lights?|lighting)$']
match_low = ['\badjustable( \w+)* lights?$', '\breading lights?$']   # "Adjustable Lamp" and "Reading Lamp" are table_lamp (pass 1; [[dims_route]] makes a tall one a floor_lamp); only the "light" forms are not caught there
uniform_scale_match = ['\barc\b', 'adjustable']
host = "su"
quads = 2500
postprocess = ["lamp"]
dims = { h = [15, 120], l = [8, 90] }
flags = ["Th"]
catalog = "Desk Lamps"

[[category]]
key = "table_lamp"
family = "lighting"
label = "Table, accent, buffet, bedside lamps, and any other head ending in 'lamp' (listed W x D is often the BASE; size by height)"
match = ['\blamps?$']
match_low = ['\blights?$', '\blighting$']
exclude = ['\b(heat|projector|bulb|replacement|uv|grow|sun|sunrise|therapy|street|solar|stake|path|garden|camping|bike|head|flash|emergency|string|fairy|twinkle|icicle|led strip|strip lights?|neon|christmas|holiday|party|festoon|garland|curtain)\b']   # string and fairy lights are not lamps: they go to the queue, never to a lamp build
host = "su"
quads = 3000
postprocess = ["lamp"]
dims = { h = [15, 130], l = [8, 80] }
catalog = "Table Lamps"
```

### 4.3e Stage 3, F6 rugs (4 leaves) and F7 wall decor (8 leaves)

Rugs: `x_accessory` (stage 1) has already removed rug pads, table runners and stair runners, so the rug leaves only see real floor coverings (this is also what the app's `RUG_RE` fails to do). Order is mat, shaped, round, rect. New leaf keys introduced here: `thickness_cm` (default thickness of a flat item, used when the listing has no depth) and, for pure procedural builders, `resizable_house = true` (checked by the harness: every leaf whose builder is rug, art, box, lathe, drape, slab, cushion or cards must carry it).

Wall decor: order is clock, floor mirror (before wall mirror), wall mirror, wall shelf, art set, textile, 3D decor, framed art. Every art pattern is anchored on the LAST word of the head, so "Art Deco Dresser", "Framed Mirror" and "Printed Sofa" can no longer reach the 6-quad art builder (the v2 mis-routes).

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F6 rugs and mats (family defaults: builder rug, 6 quads, footprint scale, rectify)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "mat_small"
family = "rugs"
label = "Door, welcome, bath, kitchen, anti-fatigue and chair mats; bath and kitchen rugs and runners"
match = [
  '\b(door|welcome|bath|bathroom|kitchen|entry|entryway|shower|bathtub|tub|bed ?side|anti[- ]fatigue|comfort|chair|floor|boot|scraper|coir)( \w+)* mats?$',
  '\bdoor ?mats?$', '\b(bath|bathroom|shower|tub|bed ?side) (rugs?|runners?)$', '\bkitchen (rugs?|runners?)$',
]
match_low = ['\bmats?$']
exclude = ['\b(yoga|exercise|gym|workout|fitness|play|baby|camping|car|pet|dog|cat|place|table|desk|mouse|cutting|drying|dish|craft|sewing|sleeping|beach|picnic|tatami|puzzle|gaming|bar|sushi|garage|trunk|cargo|tool)\b']
quads = 6
views = ["signature"]
thickness_cm = 1.2
dims = { h = [0.2, 5], l = [25, 250] }
catalog = "Kitchen Mats"

[[category]]
key = "rug_shaped"
family = "rugs"
label = "Hide, cowhide, sheepskin, faux-fur, irregular and shaped rugs (alpha outline polygon from the cut-out mask)"
match = [
  '\b(cow ?hides?|sheepskins?|sheep skins?|reindeer hides?|zebra hides?|animal hides?|hides?)$',
  '\b(hide|cowhide|cow hide|sheepskin|faux fur|faux sheepskin|faux hide|faux cowhide|fur|irregular|organic|free[- ]?form|amoeba|pebble|cloud|heart|star|flower|hexagon(al)?|octagon(al)?|shaped|scalloped|wavy|puddle|blob)( \w+)* (rugs?|carpets?|mats?)$',
]
exclude = ['\b(rectangle|rectangular|square|runner|round|circular|door|bath|kitchen)\b', '\bthrow rugs?$']
builder = "rug"
alt = "skip"                             # skip when the mask is poor
quads = 300                              # outline polygon from the mask, 200-400 quads
views = ["signature"]
thickness_cm = 1.5
dims = { h = [0.3, 8], l = [40, 400] }
flags = ["Fu"]
catalog = "Rugs"

[[category]]
key = "rug_round"
family = "rugs"
label = "Round, circular, oval, semi-circle and half-moon rugs (disc or ellipse with an alpha mask)"
match = ['\b(round|circular|circle|oval|semi[- ]?circle|half[- ]?moon|half[- ]?round|elliptical|ellipse)( \w+)* (rugs?|carpets?|mats?)$']
quads = 6
views = ["signature"]
thickness_cm = 1.0
dims = { h = [0.2, 8], l = [50, 450] }
catalog = "Rugs"

[[category]]
key = "rug_rect"
family = "rugs"
label = "Area rugs, runners, kilims, shag and outdoor rugs (rectangular; a runner is aspect 2.5 or more)"
match = ['\b(rugs?|carpets?|kilims?|dhurr?ies?|runners?)$']
exclude = ['\bthrow rugs?$']             # AU/UK: a blanket; US: a small rug. Pass 2 (`throw_blanket.match_low`) sends it to the VLM check with both candidates
quads = 6
views = ["signature"]
thickness_cm = 1.0
dims = { h = [0.2, 8], l = [50, 600] }
catalog = "Rugs"

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F7 wall decor (family defaults: host wl, scale thickness, flatten_back)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "clock_wall"
family = "wall_decor"
label = "Wall clocks (tabletop, alarm and mantel clocks are `decor_small`; floor clocks are cabinets)"
match = ['\bwall( \w+)* clocks?$']
match_low = ['\bclocks?$']
exclude = ['\b(alarm|desk|table|mantel|mantle|travel|grandfather|grandmother|longcase|floor)\b']
builder = "lathe"                        # disc plus bezel with the face texture, hands as thin boxes
alt = "tripo"
proc_gate = true                         # round dials only; square, sunburst and pendulum clocks go to Tripo
quads = 300
postprocess = []
thickness_cm = 4.0
resizable_house = true
dims = { h = [15, 200], l = [15, 200] }
flags = ["Th"]
catalog = "Clocks"

[[category]]
key = "mirror_floor"
family = "wall_decor"
label = "Floor, full-length, leaner, cheval and standing mirrors; tabletop and vanity mirrors (host `su` via [modifier.tabletop])"
match = [
  '\b(floor|full[- ]?length|full[- ]?body|leaner|leaning|standing|cheval|dressing|free[- ]?standing|body|long|tall|pier|psyche)( \w+)* mirrors?$',
  '\b(cheval|psyche)( mirrors?)?$',
  '\b(tabletop|table[- ]?top|desktop|vanity|makeup|make[- ]?up|shaving|countertop|magnifying)( \w+)* mirrors?$',
]
exclude = ['\b(wall|hanging|hung|door|mounted|bath|bathroom)\b']
builder = "hybrid"                       # frame (T 400 or a slab) plus a procedural reflective pane
alt = "tripo"
host = "fl"                              # 5.5: the app classes ANY category with the word "mirror" as a wall hanging, so a floor mirror filed under "Mirrors" would hang on the wall
scale = "box"
quads = 400
postprocess = ["glass_mirror", "pivot_cb"]   # the `ladder` modifier adds `tilt` (5-8 degrees) for a leaner
dims = { h = [15, 220], l = [10, 130] }
flags = ["T", "Th"]
catalog = "Mirrors"

[[category]]
key = "mirror_wall"
family = "wall_decor"
label = "Wall, framed, round, arched, oval, sunburst, beveled and accent mirrors (frame plus a neutral reflective pane)"
match = ['\bmirrors?$']
exclude = ['\b(rear ?view|car|handheld|hand|pocket|compact|dental|baby)\b']
builder = "hybrid"
alt = "tripo"
quads = 400
postprocess = ["glass_mirror", "flatten_back"]   # metallic 1 with low roughness; NOT KHR_materials_transmission (invalid with metallic 1); never keep the baked room reflection
thickness_cm = 3.0
dims = { h = [10, 250], l = [10, 250] }
flags = ["T", "Th"]
catalog = "Mirrors"

[[category]]
key = "wall_shelf"
family = "wall_decor"
label = "Wall and floating shelves, ledges, picture ledges, wall cubes, wall and medicine cabinets (host MUST be wall-based in the DB)"
match = [
  '\b(wall|floating|hanging|wall[- ]mounted|mounted|corner wall|bracket)( \w+)* (shelf|shelves|shelving|ledges?|racks?|cubes?|cabinets?)$',
  '\b(floating|ledge|picture|display ledge)( \w+)* (shelf|shelves|ledges?)$', '\bpicture ledges?$', '\bfloating shelves?$', '\bmedicine cabinets?$',
]
exclude = ['\b(book ?case|bookshelf|etagere|floor|standing|freestanding)\b']
builder = "slab"                         # a plain board; T 1000 for bracketed or shaped shelves
alt = "tripo"
scale = "box"                            # the depth is listed (4-12 in)
quads = 1000
resizable_house = true
dims = { h = [3, 200], l = [15, 250] }
flags = ["Th"]
catalog = "Wall Shelves"                 # 127 DB rows; the app heuristic does not match this name, so host = wall-based is mandatory

[[category]]
key = "art_set"
family = "wall_decor"
label = "Triptychs, diptychs, multi-panel canvases, gallery walls (a `set` flag on `art_framed` also routes here: [set_detect.route])"
match = [
  '\b(diptychs?|triptychs?|tryptychs?|quadriptychs?)$',
  '\b(diptychs?|triptychs?|tryptychs?|quadriptychs?)( \w+)* (wall art|art|canvas(es)?|prints?|paintings?|pictures?|artworks?|posters?|panels?)$',
  '\b(\d+|two|three|four|five|six|seven|eight|nine)[- ]?(piece|pieces|pc|pcs|panel|panels)( \w+)* (wall art|art|canvas|canvases|prints?|paintings?|posters?|pictures?|artworks?|frames?)$',
  '\b(wall art|art|canvas(es)?|prints?|paintings?|pictures?|posters?|artworks?)( \w+)* (\d+|two|three|four|five|six|seven|eight|nine)[- ]?(pieces?|pcs?|panels?)$',   # the count at the end: "Canvas Wall Art 3 Panel"
  '\b(gallery|multi[- ]?panel|split|panel)( \w+)* (wall art|art|canvas|canvases|prints?|paintings?|posters?|pictures?|artworks?)$',
  '\bgallery walls?$',
]
exclude = ['\b(metal|wood|wooden|iron|brass|resin|ceramic|3d|sculptural|sculpture|carved|rattan|bamboo|capiz)\b']
builder = "art"
quads = 6                                # per panel
views = ["signature"]
thickness_cm = 3.0
resizable_house = true
dims = { h = [20, 300], l = [20, 400] }
catalog = "Wall Art"

[[category]]
key = "wall_textile"
family = "wall_decor"
label = "Tapestries, macrame and woven wall hangings (the app regex `tapestr\b` cannot match 'tapestry', see 5.5)"
match = [
  '\btapestr(y|ies)$',
  '\b(macrame|macrame wall|woven|fabric|textile|fiber|fibre|rope|yarn|felt|boho|bohemian|quilted)( \w+)* (wall hangings?|hangings?|wall art|wall decor|tapestr(y|ies))$',
  '\bwall hangings?$', '\bmacrame$',
]
exclude = ['\b(metal|wood|wooden|iron|brass|resin|ceramic|3d|sculpture|sculptural|plaque|letters?|sign|framed|frame|canvas|print|poster|painting|mirror|clock|shelf)\b']
builder = "drape"                        # a flat hang; a slab for stiff panels
alt = "slab"
quads = 400
postprocess = []
thickness_cm = 2.0
resizable_house = true
dims = { h = [20, 300], l = [20, 300] }
flags = ["S", "Fu"]
catalog = "Wall Decor"

[[category]]
key = "wall_decor_3d"
family = "wall_decor"
label = "Metal, wood and resin wall sculptures, plaques, panels and other 3D wall decor (a bare 'wall decor' is low confidence)"
match = [
  '\b(metal|wood|wooden|iron|brass|resin|ceramic|3d|sculptural|sculpture|carved|relief|rattan|bamboo|capiz|tree of life|sunburst|starburst|mandala|dream ?catcher)( \w+)* (wall art|wall decor|wall hangings?|wall sculptures?|wall plaques?|wall panels?|wall accents?|wall ornaments?|wall pieces?|wall decorations?)$',
  '\bwall (sculptures?|plaques?|letters?|panels?|accents?|ornaments?|decorations?|pieces?|word art)$',
  '\b(plaques?|dream ?catchers?|sunbursts?|starbursts?|mandalas?)$',
  '\bwreaths?$',                           # a wreath (door, holiday, eucalyptus, grapevine, any) is a wall or door item, not a stem arrangement
]
match_low = ['\bwall (decor|decorations?|accents?)$']
exclude = ['\b(framed|frame|canvas|print|prints|poster|painting|photo|picture|glass|mirror|clock|shelf|shelves|light|lamp|sconce|tapestry|macrame|fabric|textile)\b', '\b(tabletop|table ?top|desktop|countertop)\b']   # "Tabletop Plaque" and "Tabletop Sign" are decor_small
builder = "tripo"
scale = "box"                            # the depth is listed (2-10 in)
quads = 1500
dims = { h = [5, 250], l = [5, 250] }
flags = ["Th"]
catalog = "Wall Decor"

[[category]]
key = "art_framed"
family = "wall_decor"
label = "Wall art, framed prints, canvas, paintings, posters, photographs (a furniture title can never reach this leaf)"
match = ['\b(art ?work|artworks?|art|wall art|paintings?|posters?|prints?|pictures?|canvas(es)?|photographs?|photography|lithographs?|etchings?|screen ?prints?|giclee|watercolou?rs?|illustrations?)$']
match_low = ['\b(poster|gallery|wall|hanging|collage)( \w+)* frames?$', '\bframes?$']
builder = "art"
quads = 6
views = ["signature"]
postprocess = ["rectify", "flatten_back"]
thickness_cm = 3.0                       # gallery wrap 3.8 through the `unframed` modifier
resizable_house = true
dims = { h = [10, 300], l = [10, 300] }
catalog = "Artwork"
```

### 4.3f Stage 3, F8 tabletop (7 leaves), F9 plants (4 leaves) and F10 textiles (6 leaves)

New leaf keys used here (all go into the harness whitelist, defined in 4.4):
- `proc_gate = true` means the primary procedural builder only runs when its own pre-check passes, otherwise `alt` is used. The pre-check is chosen by the builder: lathe needs a mirror-symmetric silhouette (IoU 0.93 or more) with no handle or spout; cushion needs a plain, low-variance texture (so the pillow is a box with rounded corners, not a sculpted one); rug and art keep their own clean-mask test. Every leaf whose primary builder is lathe or cushion carries the flag (all of them have a Tripo `alt`); box leaves carry it only when an `alt` exists (`tv`, `speaker_soundbar`, `appliance_large`), while `mattress` and `book_stack` are always boxes.
- `builder_by_head = { builder = [regex, ...] }` overrides the primary builder from the head phrase (frames are slabs, tabletop clocks are lathe discs, everything else in `decor_small` is Tripo).
- `set` is the multi-unit rule: `split` (default, one job per piece), `first` (identical units, build one and store the count), `keep` (the set is one product), `skip` (human queue).
- `catalog` may be a list; the first entry is the default.

Order rules: in F8, `bowl_tray` and `candle_holder` precede `decor_small`, so "decorative tray" and "decorative candle holder" never land in the catch-all desk-accessory pattern; in F9, `planter` precedes the plants and `plant_tree` precedes `plant_potted` (so "faux tree" and "faux plant" split on the last word); in F10, `bed_pillow` precedes `pillow` and a bare "pillow" is low confidence. "Floor cushion" and "floor pillow" never reach `pillow` because `bean_bag` (4.3b) matches them first; "pillow case" and "pillow insert" are `x_accessory`; "pillow cover" and "cushion cover" are `pillow` (a cover is photographed on an insert). "Throw rug" is ambiguous (blanket in AU/UK, small rug in the US), so both rug leaves exclude it and `throw_blanket.match_low` sends it to the VLM check.

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F8 tabletop and objects (family defaults: host su, scale uniform_height, quads 1000, flags T)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "vase"
family = "tabletop"
label = "Vases, urns, ginger jars, bottles and pitchers used as decor (flowers inside are masked out first)"
match = [
  '\b(vases?|urns?|ginger jars?|temple jars?|bud vases?|amphoras?|demijohns?)$',
  '\b(floor|table|tabletop|glass|ceramic|decorative|decor|bubble|cylinder|fluted|ribbed|crackle|textured|stoneware|terracotta|porcelain|marble|metal|brass|gold|matte|hammered|woven|rattan|vintage|antique|apothecary|mercury|cobalt|amber|clear)( \w+)* (jars?|jugs?|pitchers?|bottles?|carafes?)$',
]
match_low = ['\bjars?$', '\bpitchers?$', '\bjugs?$', '\bcarafes?$', '\bbottles?$']
exclude = ['\b(water|wine|beer|baby|feeding|spray|squeeze|shampoo|perfume|soda|sports?|thermos|insulated|reusable|pet|cookie|candy|canning|storage|spice|sauce)\b']
builder = "lathe"                         # profile read from the cut-out silhouette
alt = "tripo"
proc_gate = true                          # symmetric silhouettes only; handles, spouts and asymmetric shapes go to Tripo
quads = 800
postprocess = ["strip_props"]             # remove stems and flowers before the silhouette is read ([triage.avoid] vase = plants)
resizable_house = true
dims = { h = [5, 150], l = [4, 60] }
catalog = "Vases & Jars"

[[category]]
key = "bowl_tray"
family = "tabletop"
label = "Decorative bowls, trays, platters, dishes and catchalls (round ones by lathe, trays with handles by Tripo)"
match = ['\b(bowls?|trays?|platters?|catch[- ]?alls?|dishes|dish)$']
match_low = ['\bplates?$', '\bchargers?$']
exclude = ['\b(dog|cat|pet|puppy|kitten|feeding|water|singing|tv|bed|breakfast|laptop|lap|car|drying|ice|cutlery|silverware|utensil|litter|paint|desk|file|letter|paper|baking|cookie|sheet|oven|roasting|muffin|seedling|plant|cooling|drip|nail|toilet|bidet|soap|sink|bath|shower|mixing|salad|soup|cereal|pasta|rice|prep|satellite|petri|radar|washing)\b']
builder = "lathe"
alt = "tripo"
proc_gate = true
scale = "box"                             # a bowl is judged by diameter x height, not by height alone
resizable_house = true
dims = { h = [1, 40], l = [8, 90] }
catalog = "Decorations"

[[category]]
key = "candle_holder"
family = "tabletop"
label = "Candle holders, candlesticks, hurricanes, lanterns, votive and tealight holders, candelabras (flame removed)"
match = ['\b(candle ?holders?|candle ?sticks?|candelabras?|candelabrum|hurricanes?|hurricane (candle )?holders?|lanterns?|taper holders?|votive holders?|tea ?lights? holders?|candle stands?|candle plates?|pillar holders?)$']
exclude = ['\b(solar|string|fairy|camping|headlamp|flashlight|torch|tiki|street)\b']
builder = "lathe"
alt = "tripo"
proc_gate = true
quads = 1000
postprocess = []
resizable_house = true
dims = { h = [3, 120], l = [3, 40] }
flags = ["T", "Th"]
catalog = "Decorations"

[[category]]
key = "candle"
family = "tabletop"
label = "Candles (a cylinder with a wick and no flame; the jar glass is kept as a flag)"
match = ['\b(candles?|tea ?lights?|votives?)$']
builder = "lathe"
alt = "tripo"
proc_gate = true
scale = "box"
quads = 600
postprocess = []
resizable_house = true
dims = { h = [2, 40], l = [2, 25] }
flags = ["T", "Em"]
catalog = "Decorations"

[[category]]
key = "sculpture_object"
family = "tabletop"
label = "Sculptures, figurines, statues, busts, bookends, orbs and other decorative objects"
match = ['\b(sculptures?|figurines?|statues?|statuettes?|busts?|bookends?|orbs?|objets?|totems?|obelisks?|spheres?|animal figures?|decorative (objects?|spheres?|orbs?|balls?)|decor balls?)$']
match_low = ['\b(ornaments?|figures?|decorative (accents?|accessor(y|ies)|pieces?)|accent pieces?|decor accents?|home accents?|decor pieces?|decorations?|decor)$']
exclude = ['\b(action|toy|collectible|baby|stepping|nativity)\b']
builder = "tripo"
quads = 1500
postprocess = ["pivot_cb"]
dims = { h = [3, 150], l = [3, 100] }
flags = ["Th"]
catalog = "Sculptures & Figurines"

[[category]]
key = "book_stack"
family = "tabletop"
label = "Decorative books, faux book sets and coffee-table books (N boxes with small rotation offsets; cover or spine texture from the hero)"
match = [
  '\b(decorative|faux|fake|decor|coffee table|vintage|antique|hardcover|stacked|designer|home decor|display)( \w+)* books?$',
  '\bbooks? (stacks?|sets?|bundles?|decor)$', '\bbook stacks?$', '\bbooks? decor$',
]
match_low = ['\bbooks?$']
exclude = ['\b(guest|note|sketch|cook|colou?ring|children|childrens|kids?|baby|bible|prayer|photo)\b']
builder = "box"
scale = "box"
quads = 60
views = ["signature"]
resizable_house = true
dims = { h = [3, 45], l = [15, 50] }
flags = []
catalog = "Decorations"

[[category]]
key = "decor_small"
family = "tabletop"
label = "Photo frames, tabletop and desk clocks, desk organisers, jewellery boxes, globes and other small desk or shelf objects"
match = [
  '\b(photo|picture) frames?$',
  '\b(tabletop|desktop|digital|acrylic|magnetic|freestanding|multi ?photo|polaroid|baby|wedding|family)( \w+)* frames?$',
  '\b(table|desk|mantel|mantle|alarm|tabletop|bedside|shelf|digital|analog|flip|travel|desktop)( \w+)* clocks?$',
  '\b(desk|desktop|pen|pencil|stationery|office|makeup|make up|cosmetic|jewelry|jewellery|trinket|keepsake|tissue|remote|decorative|memory|music|treasure|ring|watch|cigar)( \w+)* (organizers?|organisers?|boxes|box|holders?|cups?|caddy|caddies|tidy|tidies|stands?|trays?|covers?|cases?)$',
  '\b(tabletop|table ?top|desktop|countertop) (signs?|plaques?|decor|decorations?|accents?|ornaments?|figures?|pieces?|centerpieces?|centrepieces?)$',
  '\b(globes?|centerpieces?|centrepieces?|hourglass(es)?|snow ?globes?|fountains?|incense (burners?|holders?)|oil burners?)$',
]
exclude = ['\b(collage|gallery|wall|hanging|poster)( \w+)* frames?$']   # wall-hung frames are art_framed (low confidence, the VLM check decides)
builder = "tripo"
alt = "slab"
builder_by_head = { slab = ['\bframes?$'], lathe = ['\bclocks?$'] }   # frames: frame plus a neutral inner panel (the sample photo is dropped); round clocks: lathe disc
proc_gate = true                          # applies to the lathe clocks only
quads = 1000
postprocess = []
resizable_house = true
dims = { h = [1, 90], l = [3, 90] }
catalog = ["Table Frames", "Clocks", "Decorations", "Office Accessories"]

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F9 plants (family defaults: host fl, scale uniform_height, quads 3000, flags Th and Fu)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "planter"
family = "plants"
label = "Planters, plant pots, cachepots, troughs, window boxes and raised garden beds (the plant is masked out; a soil disc is added)"
match = ['\b(planters?|plant pots?|flower ?pots?|cache ?pots?|jardinieres?|window box(es)?|window planters?|plant (holders?|baskets?|containers?|caddy|caddies)|hanging (planters?|baskets?|pots?)|flower baskets?|(raised|vegetable|veggie|herb|flower|planter|garden)( \w+)? beds?|troughs?|plant troughs?|herb (planters?|pots?))$']
match_low = ['\bpots?$']
exclude = ['\b(stock|cooking|soup|sauce|tea|coffee|chamber|hot|crock|slow|pressure|rice|baking|pasta|fondue|cookware|potpourri|jam|chili|stew|stir|steam|pie|spice)\b']
builder = "lathe"
alt = "tripo"
proc_gate = true
scale = "box"
quads = 1000
postprocess = ["soil_disc", "strip_props"]   # [triage.avoid] planter = plants
resizable_house = true
dims = { h = [5, 120], l = [5, 150] }
flags = ["Th"]
catalog = "Plants"                        # the DB's "Outdoor Accessories" (141) is not in ALLOWED_CATEGORIES (5.5)

[[category]]
key = "stems_florals"
family = "plants"
label = "Faux and dried stems, sprays, floral arrangements, garlands, pampas grass and eucalyptus (2-3 crossed alpha cards from the cut-out)"
match = [
  '\b(faux|artificial|fake|silk|dried|preserved|real ?touch|natural|decorative|realistic|lifelike)( \w+)* (flowers?|florals?|stems?|sprays?|bouquets?|branch(es)?|greenery|foliage|garlands?|bunch(es)?|picks?|vines?|eucalyptus|pampas( grass)?|grass(es)?|ferns?|lavender|roses?|peonies|peony|hydrangeas?|tulips?|orchids?|sunflowers?|berries|cotton stems?|arrangements?|centerpieces?|palm (leaves|leaf|fronds?))$',
  '\b(stems?|florals?|flowers?|bouquets?|branch(es)?|pampas( grass)?|eucalyptus|garlands?|greenery|foliage|floral arrangements?|flower arrangements?|succulent arrangements?|botanicals?|palm (leaves|leaf|fronds?))$',
]
exclude = ['\b(stemware|wine|glass|flower ?pot|flower ?bed|flower stand|flower cart|flower box|vase)\b']
builder = "cards"
alt = "tripo"
host = "su"
quads = 200
views = ["signature"]
postprocess = []
resizable_house = true
dims = { h = [15, 200], l = [3, 90] }
catalog = "Plants"

[[category]]
key = "plant_tree"
family = "plants"
label = "Faux and live trees, palms, topiaries, fiddle-leaf figs and floor plants over 1 m (Tripo, or alpha cards for the crown; pot combined)"
match = [
  '\b(faux|artificial|fake|silk|potted|floor|indoor|preserved|realistic|lifelike|large|tall|giant|decorative|real ?touch)( \w+)* (trees?|palms?)$',
  '\b(olive|lemon|orange|citrus|palm|ficus|fig|bay|bamboo|banana|bonsai|cypress|eucalyptus|birch|cherry blossom|magnolia|money|rubber|jade|dracaena|yucca|areca|kentia|fern|boxwood|laurel|ming|schefflera|corkscrew|pine|fir|spruce|christmas|xmas|holiday|pencil|norfolk|ponytail|dwarf|mini)( \w+)* trees?$',
  '\b(topiar(y|ies)|ficus|fiddle leaf figs?|bird of paradise|kentia|areca palms?|palms?|floor plants?)$',
]
match_low = ['\btrees?$']
exclude = ['\b(jewelry|jewellery|earring|necklace|shoe|towel|mug|key|nail|family|genealogy|decision|display|cat|dog|pet)\b']
builder = "tripo"
alt = "hybrid"
quads = 5000
postprocess = ["plant_pot_combine"]
dims = { h = [90, 320], l = [30, 180] }
catalog = "Plants"

[[category]]
key = "plant_potted"
family = "plants"
label = "Potted and artificial plants up to 1.5 m (pot by lathe or Tripo, foliage by Tripo or alpha cards, then combined with an insert of 0.03 m)"
match = [
  '\b(houseplants?|house plants?|potted plants?|pot plants?|faux plants?|artificial plants?|fake plants?|silk plants?|indoor plants?|live plants?|real plants?|plants?)$',
  '\b(succulents?|cactus|cacti|snake plants?|sansevieria|monstera( deliciosa| adansonii)?|bonsai|ferns?|orchids?|aloe( vera)?|pothos|philodendron|peace lil(y|ies)|zz plants?|rubber plants?|calathea|air plants?|bromeliads?|anthuriums?|jade plants?|spider plants?|ivy|boston ferns?|tillandsia|dracaena|yucca|aspidistra|croton|begonias?|geraniums?|african violets?|poinsettias?|lucky bamboo)$',
]
builder = "hybrid"
alt = "tripo"
quads = 3000
postprocess = ["plant_pot_combine"]
dims = { h = [8, 160], l = [8, 100] }
catalog = "Plants"

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F10 textiles and window (family defaults: host su, quads 600, flags S)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "bed_pillow"
family = "textiles"
label = "Bed, sleeping, body, memory-foam, euro and neck pillows (they ride the bed; protectors, cases and shams are control entries)"
match = ['\b(bed|sleeping|sleep|body|memory foam|cooling|gel|down|feather|hotel|side sleeper|stomach sleeper|back sleeper|neck|cervical|knee|wedge|pregnancy|maternity|travel|orthopedic|orthopaedic|contour|latex|buckwheat|nursing|support|leg|reading|standard|queen|king|jumbo|european|euro|hypoallergenic|down alternative|goose|duck|shredded|cluster|fiber ?fill|fibre ?fill|adjustable)( \w+)* pillows?$']
builder = "cushion"
alt = "tripo"
proc_gate = true
quads = 300
postprocess = []
resizable_house = true
set = "first"                             # "pack of 2": build one, store the count
dims = { h = [8, 30], l = [30, 150] }
catalog = "Pillows"

[[category]]
key = "pillow"
family = "textiles"
label = "Throw, accent, decorative, lumbar, outdoor and seat pillows and cushions, pillow and cushion covers (a bare 'pillow' is low confidence)"
match = [
  '\b(throw|accent|decorative|decor|lumbar|scatter|toss|bolster|outdoor|patio|seat|chair|bench|sofa|couch|tufted|velvet|linen|boucle|faux fur|embroidered|knit|woven|geometric|striped|floral|tassel|fringe|pom ?pom|round|square|rectangular|rectangle|oblong)( \w+)* (pillows?|cushions?)$',
  '\b(cushions?|bolsters?|(pillow|cushion) covers?)$',
]
match_low = ['\bpillows?$']
builder = "cushion"                       # solid or low-texture pillows: a rounded box with the rectified texture
alt = "tripo"                             # prints, embroidery, piping, tassels, pom-poms
proc_gate = true
quads = 600
postprocess = ["rectify"]
resizable_house = true
set = "first"
dims = { h = [5, 80], l = [15, 140] }
catalog = ["Pillows", "Cushions"]        # two allowed names; the app has no single "Pillows, Cushions" category

[[category]]
key = "throw_blanket"
family = "textiles"
label = "Throws, blankets, afghans and towels (a folded or draped rectangle; AU/UK 'throw rug' is a blanket)"
match = ['\b(throws?|blankets?|afghans?|towels?|bath sheets?|plaids?)$']
match_low = ['\bthrow rugs?$']             # blanket in AU/UK, small rug in the US: the VLM check decides between throw_blanket and rug_rect
exclude = ['\b(dog|cat|pet|puppy|kitten|horse|fire|emergency|moving|packing|furniture)\b']
builder = "drape"
alt = "tripo"
quads = 600
postprocess = ["fold"]
resizable_house = true
set = "first"
dims = { h = [1, 45], l = [25, 230] }
flags = ["S", "Fu"]
catalog = "Throws"

[[category]]
key = "bedding_set"
family = "textiles"
label = "Duvet and doona covers, comforters, quilts, coverlets, bedspreads, sheets and 'bed in a bag' (one drape sized to the target bed; pillows and shams are not built)"
match = [
  '\b(bed|bedding|comforter|duvet|quilt|sheet|coverlet)s?( set)? in an? (bag|box)$',
  '\b(duvet covers?|comforters?|quilts?|quilt covers?|doonas?|doona covers?|coverlets?|bedspreads?|bed ?spreads?|bed covers?|bedcovers?|bed linens?|bed sheets?|sheets?|sheet sets?|bedding|duvets?|eiderdowns?|counterpanes?|bedding sets?)$',
]
exclude = ['\b(sofa|couch|chair|table|furniture|car|dog|cat|pet|music|metal|plastic|vinyl|drop|tarp|craft|baking|cookie|oven|pan|muffin|nail|cling|dryer)\b']
builder = "drape"                         # bed size from the locale table plus a 30-50 cm drop; texture from the hero
alt = "skip"
views = ["signature"]
quads = 1200
postprocess = []
resizable_house = true
set = "keep"                              # the "set" is one drape; the pillows and nightstands in the set shot are ignored
dims = { h = [2, 60], l = [90, 300] }
catalog = "Sheets and Blankets"

[[category]]
key = "curtain"
family = "textiles"
label = "Curtains, drapes, sheers, blockouts and curtain panels (a pleated drape per panel; pivot at the rod top)"
match = [
  '\b(curtains?|drapes?|draperies|drapery|sheers?|voiles?|blockouts?|block ?outs?)$',
  '\b(curtain|drape|window|sheer|blackout|thermal|insulated|grommet|rod pocket|pinch pleat|voile|blockout|beaded|string|door|linen|velvet|cotton|room darkening|light filtering)( \w+)* panels?$',
]
exclude = ['\b(shower|bath|bathroom|car|window film|tent|bed|canopy|privacy screen|room divider|stage|photo|backdrop|party|fireplace)\b']
builder = "drape"
alt = "slab"
host = "wl"                               # hosting of curtains on a window or wall in the app is UNVERIFIED (5.5)
scale = "box"                             # panel width x drop
quads = 1500
postprocess = ["pleat", "pivot_top"]
thickness_cm = 5.0
resizable_house = true
set = "first"                             # "set of 2 panels": one panel is built, the count is stored
dims = { h = [60, 350], l = [40, 400] }
flags = ["T", "S"]
catalog = "Curtains"

[[category]]
key = "blind_shade"
family = "textiles"
label = "Blinds and window shades: roman, roller, cellular, venetian, bamboo, vertical (stepped slabs from width x drop)"
match = [
  '\b(blinds?|window shades?|roman shades?|roller shades?|cellular shades?|honeycomb shades?|venetians?|roman blinds?|roller blinds?|holland blinds?|vertical blinds?|zebra blinds?|day ?night blinds?|pleated shades?|woven wood shades?|bamboo shades?|solar shades?|roller screens?)$',
  '\b(roman|roller|cellular|honeycomb|venetian|bamboo|woven|blackout|window|vertical|pleated|zebra|solar|cordless|faux wood|wood|sheer|light filtering|day night|privacy|exterior|mini|micro)( \w+)* (blinds?|shades?)$',
]
match_low = ['\bshades?$']                 # US "shade" can also mean a lamp shade (those are `x_accessory`)
exclude = ['\b(sun ?shades?|sail|umbrella|canopy|awning|car|windshield|patio|garden|lamp)\b']
builder = "slab"
alt = "skip"
host = "wl"
scale = "box"
quads = 400
postprocess = ["pivot_top"]
thickness_cm = 6.0
resizable_house = true
dims = { h = [20, 300], l = [30, 300] }
flags = ["Th", "S"]
catalog = "Shades"
```

### 4.3g Stage 3, F13 kitchen and bath (3 leaves) and F14 appliances and electronics (7 leaves)

Order matters in three places. (1) `fireplace_electric` precedes `appliance_large`, so "wood stove" and "log burner" reach the fireplace leaf while a bare "stove" or "gas range" reaches the kitchen leaf. (2) `appliance_large` precedes `small_appliance`, and only accepts a microwave when it is built-in or over-the-range; every other microwave and every toaster, countertop or mini oven is a counter-top item (host `su`). (3) `bar_cart` precedes `kitchen_island`, so "rolling bar cart" is a bar cart while "rolling cart" and "utility cart" are islands. "Vanity with Sink" reaches `bath_vanity` through `match_title` (the head cut removes "with Sink", so the head alone would be a bare "vanity"); a bare "vanity" is low confidence and the VLM check chooses between `vanity_table` and `bath_vanity`. A shower curtain is routed to `bath_fixture` (skip) so it does not fall into `other`.

New vocabulary entry: the postprocess `cord_strip` (added to `[vocab].postprocess` in 4.1) removes a trailing power cord or hose from the mesh. It is the cord step that v2 performs inside its `lamp` postprocess (the v2 label says "floor cord removed"), split out so appliances can use it without the lamp-specific behaviour. Proposal only: the v2 implementation is not in this report's scope.

TV note: the number in a TV title is the screen DIAGONAL, so the dimension parser derives W and H from it (4.4, dimension rules). A 55 in set is 121.8 cm wide, which is above the app's 120 cm `isStackableSize` limit, so it can never be placed on a stand in the editor (5.5). Wall-mounted TVs and fireplaces get host `wl` through the `floating` modifier (4.4).

```toml
# ---------------------------------------------------------------------------------------------------
# STAGE 3  F13 kitchen and bath (family defaults: host fl, quads 2500)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "bar_cart"
family = "kitchen_bath"
label = "Bar carts, tea carts, serving carts, wine carts and drinks trolleys (bottles and glassware are removed from the reference first)"
match = ['\b(bar|serving|tea|beverage|wine|drinks?|liquor|cocktail|champagne|coffee|home bar)( \w+)* (carts?|trolleys?|trolley carts?)$', '\bbar (carts?|trolleys?)$']
exclude = ['\b(golf|shopping|grocery|hospital|medical|food truck|hot dog|popcorn|ice cream|vending|baby|doll|pet)\b']
quads = 2000
postprocess = []                         # open frame, viewed from all sides
dims = { h = [55, 120], l = [25, 130] }
flags = ["T", "Th"]
catalog = "Kitchen & Dining Carts"

[[category]]
key = "kitchen_island"
family = "kitchen_bath"
label = "Kitchen islands, kitchen and utility carts, butcher-block islands, microwave carts (a bare 'cart' is low confidence)"
match = [
  '\b(kitchen|butcher block|butcher|utility|rolling|microwave|prep|mobile|portable|breakfast|multi[- ]?purpose|storage|folding|expandable|farmhouse|industrial|rustic|cooking|pantry|stainless steel)( \w+)* (islands?|carts?|trolleys?)$',
  '\bislands?$', '\bislands?( \w+)? (tables?|bench(es)?|units?|cabinets?)$',
]
match_low = ['\bcarts?$', '\btrolleys?$']
exclude = ['\b(golf|shopping|grocery|tool|hospital|medical|food truck|hot dog|popcorn|ice cream|vending|baby|doll|pet|garden|beach|luggage|baggage|hand|laundry|cleaning|janitorial|housekeeping|file|filing|tv|charging|laptop|av|audio|projector|printer)\b']
quads = 2500
postprocess = []                         # a kitchen island is seen from every side, so no close_back
dims = { h = [60, 115], l = [40, 240] }
flags = ["Th"]
catalog = "Kitchen Islands"              # kitchen carts: "Kitchen & Dining Carts"

[[category]]
key = "bath_vanity"
family = "kitchen_bath"
label = "Bathroom vanities and washstands (body from Tripo, basin and top procedural, no faucet; a makeup vanity is `vanity_table`)"
match = [
  '\b(bath|bathroom|powder( room)?|ensuite|en[- ]suite|cloakroom|vessel|sink|basin|single sink|double sink|dual sink|undermount|wash ?basin|lavatory)( \w+)* vanit(y|ies)( (cabinets?|units?|sets?|combos?|bases?))?$',
  '\bwash ?stands?$', '\b(sink|basin) (cabinets?|units?|bases?)$', '\bunder[- ]?(sink|basin) (cabinets?|units?|storage)$',
  '\bvanit(y|ies) (cabinets?|units?|bases?|combos?)$',   # "Vanity Cabinet" and the UK "Vanity Unit" are bathroom vanities (accent_cabinet excludes the word); "Vanity Combo" is the sink-and-top bundle
  '\b(single|double|dual|twin) vanit(y|ies)$',   # "72 Inch Double Vanity": the size words only occur on bathroom vanities; a bare "Vanity" stays low (vanity_table, VLM check)
]
match_title = ['\bvanit(y|ies)\b.*\b(sink|basin|faucet|tap|undermount|vessel|backsplash)\b']   # "Vanity with Sink": the head cut removed the sink word
exclude = ['\b(makeup|make-?up|dressing|cosmetic|beauty|jewelry|jewellery|table|desk|stool|bench|chair|lights?|lamps?|mirrors?|tops?|countertops?)\b']
builder = "hybrid"                       # Tripo cabinet (2500) plus a procedural basin and top; the faucet is left out
alt = "skip"                             # the fixtures library covers basins
quads = 2500
postprocess = ["close_back"]
dims = { h = [30, 125], l = [40, 220] }
flags = ["T"]
catalog = "Cabinets"                     # DB "Bath" (142) is not in ALLOWED_CATEGORIES: file under Cabinets until the allow-list is extended (5.5)

# ---------------------------------------------------------------------------------------------------
# STAGE 3  F14 appliances and electronics (family defaults: host fl, quads 2500, flags T and Em)
# ---------------------------------------------------------------------------------------------------
[[category]]
key = "fireplace_electric"
family = "appliances"
label = "Electric, bio-ethanol and wood-burning fireplaces, inserts, mantels, surrounds and stoves (flame off; a fireplace TV stand is a `tv_stand`)"
match = [
  '\b(electric|wall[- ]mounted|recessed|built[- ]in|freestanding|free[- ]standing|bio[- ]?ethanol|ethanol|gel|gas|infrared|led|3d|smart|wifi|panoramic|linear|tabletop|table top|corner|insert|log|flame)( \w+)* (fireplaces?|fire ?surrounds?|fire ?box(es)?|fire inserts?)$',
  '\b(fireplaces?|fireplace (inserts?|mantels?|surrounds?|heaters?)|mantels?|mantles?|mantel shelf|chimney breasts?|hearths?|log burners?|wood burners?)$',
  '\b(wood|pellet|log|multi[- ]?fuel|cast iron|wood[- ]burning|coal|solid fuel)( \w+)* (stoves?|burners?)$',
]
exclude = ['\b(tools?|accessor(y|ies)|screens?|grates?|pokers?|baskets?|holders?|racks?|covers?|rugs?|mats?|gloves?|pads?|bellows|lighters?|matches|candles?|starters?)\b']
builder = "hybrid"                       # Tripo surround (3000) plus a procedural firebox, flame off
alt = "tripo"
quads = 3000
postprocess = ["close_back"]
dims = { h = [15, 260], l = [30, 260] }
flags = ["T", "Em"]
catalog = ""
na = true                                # no matching allowed category: extend the allow-list

[[category]]
key = "tv"
family = "appliances"
label = "TVs (the title number is the screen diagonal; wall-mounted ones are host `wl` via [modifier.floating])"
match = ['\b(tvs?|televisions?)$', '\bthe (frame|serif|sero|terrace)$']
exclude = ['\b(toy|pretend|prop|cardboard|dollhouse|miniature)\b']
builder = "box"                          # bezel slab with a black glass screen, optional V-foot; W and H from the diagonal, depth from the listing
alt = "tripo"
proc_gate = true
scale = "box"
quads = 60
views = ["front", "signature"]
postprocess = []
thickness_cm = 6.0
resizable_house = true
dims = { h = [25, 150], l = [40, 260] }
flags = ["T", "Em"]
catalog = ["TVs", "Standing TVs"]        # DB "TV (50 and larger)" (162) and "TV (32 and under)" (160) are not allowed (5.5)

[[category]]
key = "speaker_soundbar"
family = "appliances"
label = "Speakers, soundbars, subwoofers, turntables, record players, radios and amplifiers"
match = ['\b(soundbars?|sound bars?|speakers?|subwoofers?|woofers?|turntables?|record players?|boom ?box(es)?|jukebox(es)?|home theat(er|re) systems?|receivers?|amplifiers?|radios?|gramophones?|phonographs?|stereos?|stereo systems?)$']
exclude = ['\b(toy|pretend|miniature|dollhouse)\b']
builder = "box"                          # grille box plus feet; Tripo for ornate cabinets
alt = "tripo"
proc_gate = true
host = "su"
scale = "box"
quads = 200
views = ["front", "signature"]
postprocess = []
resizable_house = true
dims = { h = [3, 130], l = [10, 140] }
flags = []
catalog = "Entertainment"                # DB "Music Systems & Speakers" (85) is not allowed

[[category]]
key = "fan_heater_purifier"
family = "appliances"
label = "Tower and pedestal fans, space and oil heaters, air purifiers, humidifiers, dehumidifiers and portable air conditioners"
match = [
  '\b(heaters?|space heaters?|radiators?|oil[- ]filled radiators?|air (purifiers?|cleaners?|conditioners?|coolers?)|purifiers?|humidifiers?|dehumidifiers?|air conditioners?|ac units?|swamp coolers?|diffusers?)$',
  '\b(tower|pedestal|floor|desk|table|stand|standing|box|window|bladeless|oscillating|misting|evaporative|portable|personal|usb|clip[- ]on|circulator|cooling|exhaust|extractor|industrial|drum|wall[- ]mount(ed)?|mini)( \w+)* fans?$',
]
match_low = ['\bfans?$']
exclude = ['\b(ceiling|handheld|hand held|neck|bottle|blanket|pad|replacement|filters?|covers?|remote|hair|pet|baby|bed)\b']
quads = 2500
postprocess = []
dims = { h = [10, 190], l = [10, 90] }
flags = ["Ho", "Th"]
catalog = ""
na = true                                # no matching allowed category

[[category]]
key = "appliance_large"
family = "appliances"
label = "Refrigerators, freezers, washers, dryers, dishwashers, ranges, cooktops, wall ovens, range hoods and built-in microwaves"
match = [
  '\b(refrigerators?|fridges?|fridge[- ]?freezers?|freezers?|chest freezers?|upright freezers?|mini[- ]?fridges?|wine (coolers?|fridges?|refrigerators?|cellars?)|beverage (coolers?|centers?|centres?|refrigerators?|fridges?)|ice makers?|kegerators?)$',
  '\b(washers?|washing machines?|dryers?|tumble dryers?|clothes dryers?|washer[- ]?dryers?|washer and dryer|laundry (pairs?|centers?)|dishwashers?)$',
  '\b(ranges?|cookers?|stoves?|cooktops?|hobs?|wall ovens?|ovens?|double ovens?|oven ranges?|slide[- ]in ranges?|freestanding ranges?|range ovens?|dual fuel ranges?)$',
  '\b(range ?hoods?|cooker hoods?|extractor hoods?|vent hoods?|exhaust hoods?|kitchen hoods?|chimney hoods?|under[- ]cabinet hoods?|island hoods?)$',
  '\b(over[- ]the[- ]range|built[- ]in|otr|trim kit|drawer) microwaves?( ovens?)?$',
]
exclude = ['\b(countertop|toaster|tabletop|table top|benchtop|bench top|portable|pizza|rotisserie|air fryer|bread|camping|mini oven|dollhouse|toy|play|pretend|kids?|replacement|spare|parts?|accessor(y|ies)|covers?|stands?|carts?|racks?|trays?|liners?|filters?|gaskets?|knobs?|handles?|drip pans?|guards?)\b', '\b(slow|rice|pressure|egg|instant|sous vide)\b|\bmulti[- ]?cookers?\b']   # a slow, rice, pressure or multi cooker is a counter-top appliance (small_appliance), not a range cooker
builder = "box"                          # door lines, handle, top; or skip and use the fixtures library (about 40 fixtures in src/data/fixtureManifest.js)
alt = "skip"
proc_gate = true
scale = "box"
quads = 300
views = ["front", "signature", "side"]
postprocess = []
resizable_house = true
dims = { h = [15, 215], l = [30, 160] }
flags = ["T"]
catalog = ["Refrigerators", "Washing Machines", "Kitchen Appliances"]   # DB Ovens & Stoves (77), Dishwashers (78), Dryers (82), Utility Room Appliances (80) are not allowed (5.5)

[[category]]
key = "small_appliance"
family = "appliances"
label = "Coffee and espresso machines, toasters, blenders, air fryers, kettles, mixers, cookers, countertop and toaster ovens, microwaves (cord removed)"
match = [
  '\b(coffee (makers?|machines?|brewers?|grinders?|percolators?)|espresso (machines?|makers?|grinders?)|toasters?|toaster ovens?|blenders?|air fryers?|kettles?|electric kettles?|stand mixers?|hand mixers?|mixers?|slow cookers?|rice cookers?|pressure cookers?|multi[- ]?cookers?|instant pots?|food processors?|juicers?|waffle makers?|sandwich makers?|bread makers?|popcorn makers?|ice cream makers?|deep fryers?|griddles?|hot plates?|sous vide( \w+)?|steamers?|food steamers?|yogurt makers?|milk frothers?|stick blenders?|immersion blenders?|dehydrators?|water dispensers?|soda ?makers?|carbonators?|nespresso|keurig|pod machines?|microwaves?|microwave ovens?)$',
  '\b(countertop|toaster|tabletop|table top|benchtop|bench top|mini|portable|pizza|rotisserie|bread|electric|indoor|smokeless|panini|contact|raclette|korean|induction) (ovens?|grills?|cookers?|griddles?|cooktops?|hobs?)$',
]
# "X for Y" titles are already cut at "for" (head_cut), so accessories such as "Descaler for Coffee Machine" never reach this leaf. The exclude therefore lists only
# words that really sit in front of an appliance noun: toys, books and spares. "Single Serve Pod", "12-Cup", "Glass Carafe", "Filter" and "Stand Mixer" are appliances (the stress sweep).
exclude = ['\b(toys?|play|pretend|kids?|miniature|dollhouse|cookbooks?|recipes?|books?|replacement|spare|parts?|accessor(y|ies))\b']
host = "su"
scale = "box"
postprocess = ["cord_strip"]
dims = { h = [8, 60], l = [10, 80] }
flags = ["T", "Th"]
catalog = "Kitchen Appliances"

[[category]]
key = "bath_fixture"
family = "appliances"
label = "Toilets, bathtubs, showers, sinks, basins, faucets, towel rails and shower curtains (not built here: the fixtures library covers them)"
match = ['\b(toilets?|water closets?|commodes?|bidets?|urinals?|cisterns?|bath ?tubs?|tubs?|soaking tubs?|clawfoot tubs?|showers?|shower (enclosures?|screens?|doors?|trays?|stalls?|bases?|cabins?|cubicles?|panels?|kits?|systems?|curtains?)|(\w+ )*sinks?|wash ?basins?|hand ?basins?|basins?|faucets?|taps?|mixer taps?|towel (rails?|warmers?)|heated towel rails?)$']
exclude = ['\b(baby|infant|ice|beverage|storage|laundry|stock|plastic|dog|pet|cat|foot|feeding|party|drink|wine|hot|spa|swim|swimming|cooler|bucket|mat|rug|chair|stool|seat|bench|caddy|organi[sz]er|shelf|rack|toy|toys|pretend|play|lamp|light|replacement|spare|parts?|cleaner|cleaning|brush|hose|cartridge|filter)\b']
builder = "skip"
alt = "tripo"                            # only if a reviewer overrides the skip
quads = 2500
postprocess = []
dims = { h = [3, 230], l = [10, 220] }
flags = []
catalog = ""
na = true                                # DB "Bath" (142) is not allowed
```

### 4.4 Set detection, modifiers, proc gates, dims routes, triage, the `misc` family and `other`

This block holds the machinery that is not a leaf. Two fenced `toml` blocks follow (4.4a: sets and modifiers; 4.4b: gates, routes, parsing constants, triage, `other`). They concatenate onto 4.1 to 4.3g.

Vocabulary semantics (the words the loader validates and the reviewers read):

| Word | Meaning |
|---|---|
| `flatten_back` | flatten the MOUNTING face: the back for wall items, the top for ceiling items |
| `pivot_cb` / `pivot_top` / `pivot_back` | pivot at centre-bottom (the default) / at the canopy, ceiling point or curtain-rod top / at the back plate |
| `alt` | second-choice builder: used when the primary builder fails its gate or its job; for `skip` leaves it is the builder a reviewer can override to |
| `uniform_scale_match` | kept verbatim from v2: arc and adjustable lamps are sized uniformly by height even when the leaf scale is `box` |
| `cord_strip` | NEW: remove a trailing power cord or hose. It is the cord half of v2's `lamp` postprocess (the v2 label says "floor cord removed"), split out so appliances can use it. Proposal only |
| conditional steps | `net`, `weave`, `glass_top`, `glass_door`, `laf_raf` and `bed` in a leaf list run only when their detector fires on the chosen reference; a modifier can force them on |
| inheritance | a leaf's `postprocess` and `flags` REPLACE the family's lists (no merge), so an open-frame storage leaf says `postprocess = []` |
| `resizable` | the vendor-linked value, always false (the app's `buildAssetInput` writes `is_resizable:false`) |
| `resizable_house` | the house-built, no-vendor-link value for procedural builders; the harness checks it both ways (a leaf whose primary builder is `rug`, `art`, `box`, `lathe`, `drape`, `slab`, `cushion` or `cards` must set it, and a leaf that sets it must have such a primary builder or `alt`) |
| `set` | what a set of identical pieces does: `split` (default: one job per distinct piece the gallery shows alone, identical pieces dedupe to one job with the count stored), `first` (build one, store N), `keep` (the set is one product), `skip` (human queue) |
| `set_mixed` | the same choice for sets of DIFFERENT products (default `skip`; `split` where the pieces are clean) |
| `proc_gate` | boolean: the procedural primary builder runs only when its pre-check (`[proc_gate]`, 4.4b) passes; otherwise `alt` runs |
| `builder_by_head` | map of builder to head regexes; overrides the leaf builder for matching heads (used by `decor_small`) |
| `thickness_cm` | default thickness of a flat item when the listing has no depth |
| `catalog` | the DB category name, or a list of names in order of preference; at least one must be in the app's allow-list unless `na = true`, which means none of them is (5.5) |

Leaf keys the loader accepts (anything else is rejected as a typo): `key, family, label, match, match_low, match_ctx, match_title, exclude, ctx, builder, alt, host, scale, quads, postprocess, multi_image, views, dims, flags, catalog, na, resizable, resizable_house, set, set_mixed, bed_frame_photo, uniform_scale_match, thickness_cm, proc_gate, builder_by_head, front, pivot, on_hit`. `catalog` may be a string or a list. `on_hit = "queue"` (only `other` uses it) sends the job to the human queue instead of building.

Modifier keys the loader accepts: `on` (head, title, ctx, strip), `regex, gate, delegate, route, host, host_leaves, add_flags, add_flags_except_families, add_postprocess_by_leaf, add_postprocess_by_family, dims_by_leaf, dims_scale, dims_scale_except_families, thickness_cm, thickness_leaves, dim_pick, meta, note`. `on = "head"` tests the normalised head before set words are stripped; `ctx` is the title plus the last two breadcrumbs; `strip` fires when the set-word step removed something or `count_regex` matched.

Detection runs the head in two forms (the stripped head, then the head with its set words put back), so a pattern may still name its own set word (`bistro sets?`, `book sets?`), while "dining table set" routes as "dining table". A trailing "suite" is a set word except for the heads named by `keep_suite` ("chaise suite" and "corner suite" are one sectional; the AU "lounge suite" stays a set).

Set kind (what the orthogonal `set` flag means). A listing is a set when a set word was stripped (`trail_words`, `trail_regex`), when `count_regex` matched (an N-count phrase, or a room word followed by a set word in the middle of the title, "Bedroom Set Queen Bed Nightstand Dresser"), or, only for a leaf that declares `set_mixed`, when `mixed_join` matched. The kind is IDENTICAL when the title carries an explicit identical phrase ("set/pair/pack/lot/bundle of N", "N-pack", "N-pk", "pair", "duo" or "trio"), unless `mixed_join` also fires ("Set of 4 Dining Chairs and Table" is mixed). Without such a phrase it is MIXED when `mixed_words` matches the title, or when the leaf declares `set_mixed` and the marker is a bare set word or an N-piece count ("5-Piece Dining Set"). An explicit identical phrase therefore beats a room word: "Set of 2 Living Room Accent Chairs" is identical, "Living Room Set" is mixed. An identical set uses the leaf's `set` (default `split`, which dedupes identical pieces to one job and stores the count); a mixed set uses `set_mixed` (default `skip`: the human queue). `sectional` is exempt, so "3-Piece Sectional" stays one product.

```toml
# ---------------------------------------------------------------------------------------------------
# SET DETECTION: an orthogonal flag. It never changes the leaf; it changes how many jobs one listing makes.
# ---------------------------------------------------------------------------------------------------
[set_detect]
trail_words = ["set", "suite", "collection", "bundle", "ensemble", "package", "combo", "group", "pair", "duo", "trio"]
trail_regex = '\s(?:(?:set|pair|pack|lot|bundle) of (?:\d{1,2}|two|three|four|five|six|eight|ten|twelve)|\d{1,2}[- ]?(?:pc|pcs|piece|pieces|pack|pk))$'
count_regex = '\b(?:set|pair|pack|lot|bundle) of (\d{1,2}|two|three|four|five|six|eight|ten|twelve)\b|\b(\d{1,2})[- ]?(?:pc|pcs|piece|pieces|pack|pk)\b|\b(?:pair|duo|trio) of\b|\b(?:bedroom|living ?room|dining ?room|dining|patio|conversation|bistro|nursery|home office|entryway|bathroom|kitchen|deep seating)(?: furniture)? (?:set|suite|collection|ensemble|package|combo)\b'
keep_suite = '\b(?:chaise|corner|modular|l[- ]shaped|u[- ]shaped|curved|wedge|reversible)\s+suites?$'   # UK: "Chaise Suite" and "Corner Suite" are ONE sectional, so the trailing "suite" is kept; the AU "Lounge Suite" stays a set (sofa plus chairs)
exempt_leaves = ["sectional"]           # "3-piece sectional" is one product, built as one mesh
identical = "leaf.set"                  # every piece shares one head: use the leaf's `set` value (default "split")
mixed = "leaf.set_mixed"                # different heads or a room word: the leaf's `set_mixed` value (default "skip")
mixed_words = '\b(living ?room|bed ?room|dining ?room|patio|conversation|nursery|home office|entryway|kitchen|bathroom|porch|deep seating)\b'   # "outdoor" is NOT here: "Set of 2 Outdoor Chairs" is identical pieces
# a title that names a second, different piece after "and", "&", "+" or "with" is a MIXED set even without a set word ("Dining Table and 4 Chairs"); only leaves that declare `set_mixed` read it
mixed_join = '\b(?:and|&|\+|plus)\s+(?:(?:\d{1,2}|two|three|four|five|six|a|an|the|matching)\s+)*(?:[\w-]+\s+){0,2}(?:chairs?|armchairs?|stools?|benches|bench|loveseats?|sofas?|ottomans?|poufs?|tables?|desks?|nightstands?|dressers?|mirrors?|lamps?)\b|\bwith\s+(?:(?:\d{1,2}|two|three|four|five|six|a|an|the|matching)\s+)*(?:[\w-]+\s+)?(?:chairs?|armchairs?|stools?|benches|bench|ottomans?|poufs?|loveseats?|nightstands?)\b'

[set_detect.route]
art_framed = "art_set"                  # "Set of 3 Framed Prints" is a gallery set, built per panel

# ---------------------------------------------------------------------------------------------------
# MODIFIERS: flags set while the head phrase is parsed. They never add leaves. A modifier may gate patterns (`gate`),
# re-route a head (`route`), change the host (`host` + `host_leaves`), add postprocess steps or flags, move sanity
# ranges (`dims_by_leaf`, `dims_scale`), set a thickness, or only record `meta` on the job card.
# ---------------------------------------------------------------------------------------------------
[modifier.outdoor]
on = "ctx"
regex = '\b(outdoors?|patio|garden|alfresco|al fresco|poolside|pool ?side|deck|balcony|terrace|porch|veranda|verandah|backyard|all[- ]weather)\b'
gate = true                              # lets `match_ctx` of leaves with ctx = "outdoor" count; with no outdoor noun the title falls through to the indoor leaves
meta = { outdoor = true }

[modifier.kids]
on = "ctx"
regex = '\b(kids?|children|childrens|child|toddlers?|youth|nursery|baby|babies|infant|junior|teens?|tweens?)\b'
dims_scale = { h = [0.4, 1.0], l = [0.4, 1.0] }   # lower bounds shrink to 40 percent: a 60 cm kids bookcase is not "inches typed as cm"
dims_scale_except_families = ["kids"]
meta = { audience = "kids" }

[modifier.sleeper]
on = "head"
regex = '\b(sleepers?|pull[- ]?outs?|sofa[- ]?beds?|couch[- ]?beds?|futons?|convertible|click[- ]?clack)\b'
route = { bed = "sofa" }                 # "Futon Bed Frame" is a sofa frame: never a bed, so no mattress is added
meta = { build_state = "closed" }

[modifier.set]
on = "strip"
delegate = "set_detect"
meta = { set = true }

[modifier.tabletop]
on = "head"
regex = '\b(tabletop|table[- ]?top|desktop|desk[- ]?top|countertop|counter[- ]?top|benchtop|bench[- ]?top|vanity|makeup|make[- ]?up|shaving|magnifying|(table|desk) (fans?|heaters?|fireplaces?|fire ?pits?|mirrors?))\b'
host = "su"                              # "mini" is deliberately NOT a trigger: a mini fridge stands on the floor
host_leaves = ["mirror_floor", "fire_pit", "fireplace_electric", "fan_heater_purifier"]

[modifier.easel]
on = "title"
regex = '\b(easels?|(free[- ]?)?standing (frame|canvas|art)|(table|desk)[- ]?top (frame|art|canvas))\b'
host = "su"                              # UNVERIFIED in the app: the name and category heuristics may still class an easel print as a wall hanging (5.5)
host_leaves = ["art_framed", "art_set", "wall_decor_3d", "wall_textile", "mirror_wall"]   # "Easel Back Mirror" is a tabletop mirror whatever its head noun is
meta = { easel = true }

[modifier.unframed]
on = "title"
regex = '\b(unframed|un-framed|gallery[- ]?wrap(ped)?|stretched canvas|canvas only)\b'
thickness_cm = 3.8
thickness_leaves = ["art_framed", "art_set"]
meta = { frame = "none" }

[modifier.floating]
on = "head"                              # "TV with wall mount" is cut at "with", so it never triggers
regex = '\b(floating|wall[- ]?mounted|wall[- ]?hung|wall[- ]?hanging|wall mount)\b'
host = "wl"
host_leaves = ["tv", "fireplace_electric", "speaker_soundbar", "fan_heater_purifier", "planter", "hall_tree"]   # hall_tree: a "Wall Mounted Coat Rack" is a hook board, thin and wall-hung
meta = { floating = true }               # every other leaf (nightstand, tv_stand, vanity, desk) keeps host fl: the app has no elevated floor placement (UNVERIFIED) and a `wall-based` row is placed as a wall hanging (5.5)

[modifier.glass]
on = "title"
regex = '\b(glass|acrylic|lucite|perspex|crystal|clear|transparent|see[- ]through|mirrored|tempered)\b'
add_flags = ["T"]
add_postprocess_by_family = { tables = ["glass_top"], storage = ["glass_door"] }   # makes the conditional glass steps unconditional

[modifier.mesh]
on = "title"
regex = '\b(mesh|net|cane|caned|rattan|wicker|woven|webbed|slat(ted)?|perforated|lattice|openwork)\b'
add_flags = ["Ho"]
add_flags_except_families = ["rugs", "textiles", "wall_decor"]
add_postprocess_by_leaf = { office_chair = ["net"], accent_chair = ["weave"], dining_chair = ["weave"], bar_stool = ["weave"], outdoor_chair = ["weave"], outdoor_sofa = ["weave"], bench = ["weave"], chaise_lounge = ["weave"] }

[modifier.module]
on = "head"
regex = '\b(armless|wedge|add[- ]?on|(corner|middle|center|centre|end|chaise|ottoman|armchair|single) (module|unit|piece|seat)|modules?)\b'   # "modular" alone does not fire: a "modular sofa" is a whole sectional
dims_by_leaf = { sectional = { l = [60, 260] } }
meta = { module = true }                 # build one module, never the assembly

[modifier.ladder]
on = "head"
regex = '\b(ladder|leaning|leaner|lean[- ]?to)\b'
add_postprocess_by_leaf = { bookcase = ["tilt"], mirror_floor = ["tilt"] }   # bake a 5 to 8 degree lean; "ladder back chair" has no effect

[modifier.rocker]
on = "head"
regex = '\b(rockers?|rocking|gliders?)\b'
add_flags = ["Th"]
meta = { rocker = true }                 # informational: the curved runners are thin

[modifier.bar_height]
on = "head"
regex = '\b(bar[- ]?height|counter[- ]?height|pub[- ]?(height|table|set)|high[- ]?top|bar tables?|counter tables?|bistro tables?)\b'
dims_by_leaf = { dining_table = { h = [88, 115] }, outdoor_table = { h = [85, 115] } }
meta = { seat_class = "tall" }

[modifier.standing]
on = "head"
regex = '\b(standing|sit[- /]*(to[- ]?)?stand|height[- ]adjustable|adjustable[- ]height|stand[- ]up|variable[- ]height|(electric|motori[sz]ed|lift)( \w+)? (desks?|work ?stations?))\b'
route = { desk = "standing_desk" }
meta = { build_state = "lowest" }

[modifier.extension]
on = "head"
regex = '\b(extendable|extension|expandable|extending|drop[- ]leaf|gate[- ]?leg(ged)?|butterfly( leaf)?|expanding)\b'
dims_by_leaf = { dining_table = { l = [100, 420] }, outdoor_table = { l = [100, 420] } }
dim_pick = "min"                         # a listed range "66-84 in" is read at its closed (smaller) value
meta = { build_state = "closed" }
```

#### 4.4b Gates, dimension routes, parse constants, triage and the `other` fallback

`[proc_gate.*]` holds the pre-check of each procedural builder. `[[dims_route]]` runs after the parser has read W, D and H: `to` moves the job to another leaf, `host` only changes the host. `when` is a tiny expression over `h, w, d, lmax, lmin` (cm) joined by `and`; a route never fires when the dimensions are missing. `[triage]` holds the cheap image tests that run before any credit is spent (Section 6 explains why the top-15 categories need them). `other` is the last `[[category]]`: a hit means NO leaf matched in either pass, the breadcrumb, or the VLM, and the job goes to the human queue (`on_hit = "queue"`) instead of building on a guess.

```toml
# ---------------------------------------------------------------------------------------------------
# PROCEDURAL GATES. A leaf with `proc_gate = true` runs its procedural builder only when the pre-check for that builder passes on the
# chosen reference; otherwise `alt` runs. Every check is a mask or title test (no credits). The rug and art builders keep v2's own
# corner-finding check and always run it (`always = true`).
# ---------------------------------------------------------------------------------------------------
[proc_gate.lathe]
test = "radial_silhouette"       # the cut-out mask, mirrored about its vertical axis, must overlap itself
min_iou = 0.93
min_fill = 0.35                  # the object fills at least 35 percent of the frame, or the profile is too coarse to read
max_components = 1               # one connected blob: flowers or a lid knob outside the envelope fail the test
reject_title = '\b(handles?|handled|spouts?|pitchers?|jugs?|teapots?|watering cans?|lidded|with lids?|double[- ]handled?|ears?)\b'

[proc_gate.cushion]
test = "plain_texture"           # a rounded box with the reference texture projected on both faces
max_texture_std = 0.20           # standard deviation of the luminance inside the mask (0 to 1)
max_motif_area = 0.05            # a logo, face or large print over 5 percent of the face fails
reject_title = '\b(tufted|fringe[ds]?|tassels?|pom[- ]?poms?|ruffles?|ruffled|ruched|smocked|pleated|3d|sculpted|animal shaped|shaped)\b'

[proc_gate.box]
test = "rectangular_silhouette"  # TVs, speakers and white goods: a front elevation that is a clean rectangle
min_rect_fill = 0.80             # mask area over its minimum-area bounding rectangle (a stand or feet may take up to 20 percent)
max_skew_deg = 12                # perspective skew of the main quadrilateral

[proc_gate.rug]
always = true                    # v2 behaviour: four corners found, the rug fills the frame, nothing lies on it

[proc_gate.art]
always = true

# ---------------------------------------------------------------------------------------------------
# DIMENSION ROUTES. `only = "low"` limits a route to pass-2 (low-confidence) hits; `title_not` is a guard regex on the full title;
# `confidence = "low"` marks the result on the job card without queueing it.
# ---------------------------------------------------------------------------------------------------
[[dims_route]]
from = "table_lamp"
to = "floor_lamp"
when = "h >= 115"
title_not = '\b(table|desk|bedside|buffet|accent)\b'
note = "a bare 'lamp' or 'light' at floor height; a 'table lamp' that tall is a data error and takes the units warning instead"

[[dims_route]]
from = "pillow"
to = "bed_pillow"
when = "lmax >= 62 and lmin >= 40"
title_not = '\b(bolsters?|lumbar|floor|seat|chair|neck)\b'
note = "Euro 65x65, standard 50x75 and king 50x90 are sleeping pillows; decorative ones stop near 60 cm"

[[dims_route]]
from = "throw_blanket"
to = "bedding_set"
when = "lmax >= 200 and lmin >= 140"
note = "a 'king blanket' 230x275 is bedding; a throw stops near 150x200"

[[dims_route]]
from = "mirror_wall"
to = "mirror_floor"
when = "h >= 140 and lmin <= 90"
title_not = '\b(wall|hanging|hung|mounted|door|over)\b'
confidence = "low"
note = "a bare 'mirror' 160x60 is a leaner; the host matters (5.5: the app hangs any 'Mirrors' row on the wall)"

[[dims_route]]
from = "bar_stool"
to = "ottoman"
when = "h <= 55"
only = "low"
note = "a bare 'stool' at footstool height; 'bar stool' and 'counter stool' keep their leaf by name"

[[dims_route]]
from = "sofa"
to = "loveseat"
when = "lmax <= 170"
title_not = '\b(sectional|sleeper|chaise|daybed|futon|bench|settee|kids?|childrens?|toddlers?)\b'
confidence = "low"
note = "a '2 seater sofa' or 'apartment sofa' is a loveseat in the US catalog (6,000 quads instead of 12,000); a kids sofa stays a sofa (the kids modifier already lowers its size range)"

[[dims_route]]
from = "plant_potted"
to = "plant_tree"
when = "h >= 130"

[[dims_route]]
from = "plant_tree"
to = "plant_potted"
when = "h < 90"

# host-only routes: the leaf stays, the placement host changes (app gates: isStackableSize is height <= 80 and footprint <= 120 cm, see 5.5)
[[dims_route]]
from = "plant_potted"
when = "h <= 60"
host = "su"

[[dims_route]]
from = "planter"
when = "h <= 30"
host = "su"

[[dims_route]]
from = "vase"
when = "h >= 70"
host = "fl"

[[dims_route]]
from = "sculpture_object"
when = "h >= 70"
host = "fl"

[[dims_route]]
from = "candle_holder"
when = "h >= 60"
host = "fl"

[[dims_route]]
from = "speaker_soundbar"
when = "h >= 60"
host = "fl"

[[dims_route]]
from = "fan_heater_purifier"
when = "h <= 45"
host = "su"

# ---------------------------------------------------------------------------------------------------
# DIMENSION PARSE CONSTANTS (the full rule list is in 5.4)
# ---------------------------------------------------------------------------------------------------
[dims_parse]
in_to_cm = 2.54
ft_to_cm = 30.48
unitless = "range_guess"         # no unit: cm if it fits the leaf's `dims`, else inches if THAT fits, else flag the card (the Add products form already warns)
range_pick = "min"               # "66-84 in" reads as 66 (closed); only `extension` tables and `module` pieces ever need the other end
sheet_sizes = "locale"           # bed and rug size names resolve through the locale table in 5.4 (US full is not AU double; UK king is not US king)
tv = { w = 0.8716, h = 0.4903, aspect = "16:9", depth_cm = 6.0 }   # the number in a TV title is the DIAGONAL: w = diag x 16/sqrt(337), h = diag x 9/sqrt(337)

# ---------------------------------------------------------------------------------------------------
# TRIAGE: cheap image tests first, then ONE closed-set VLM question for any candidate that trips a test (Section 6).
# Starting values; tune on the first 200 jobs.
# ---------------------------------------------------------------------------------------------------
[triage]
cutout_border_white = 0.93       # share of border pixels within 8/255 of white (or transparent): a studio cut-out
min_fill = 0.30                  # foreground area over image area: below this the item is small in a scene
max_components = 1               # foreground blobs of at least 2 percent of the item area (more means props or a set shot)
max_border_touch = 0.02          # share of the border that is foreground: a figure cropped by the frame edge
max_ocr_density = 0.015          # text pixels over image area: dimension drawings and infographics
min_edge_px = 600                # Tripo needs 256 px; under 600 the texture is poor, so prefer the larger gallery image
aspect_range = [0.45, 2.2]       # width over height; outside it is a banner, a swatch strip or a collage
flat_leaves = ["rug_rect", "rug_round", "rug_shaped", "mat_small", "art_framed", "art_set", "wall_textile", "curtain", "blind_shade", "mirror_wall"]   # exempt from the aspect test; they get `rectify`
filename_reject = '(?i)(?:^|[_.\s-])(room|airoom|ai[_-]?room|dimensions?|dims?|lifestyle|scene|swatch|material|fabric|texture|infographic|feature|detail|closeup|zoom)(?:[_.\s-]|$)'
filename_prefer = '(?i)(?:^|[_.\s-])(signature|front|side|main|hero|primary|cutout|studio)(?:[_.\s-]|$)'   # Living Spaces tokens are verified in v2 [photos]; the other retailers' tokens are a guess
vlm_enum = ["cutout", "lifestyle", "multi_item", "detail", "infographic", "swatch"]
vlm_asks = ["item_count", "view", "props"]
ask_vlm_when = "any_test_trips or leaf_in_top15"

[triage.action]
lifestyle = "next_view"          # the next gallery image that passes the cheap tests
multi_item = "crop_matte"        # detector box on the item the head names, then re-matte; set leaves split first (4.4a)
detail = "next_view"
infographic = "drop"
swatch = "drop"
flat = "rectify"                 # flat leaves: homography to a front-on rectangle from the mask corners, never a crop of a room shot
transparent = "hybrid"           # leaf flag T: Tripo body plus procedural glass, never a transparent matte
no_view_passes = "queue"         # human queue with the 3 best candidates and their VLM labels

# Props that disqualify a candidate image (vocabulary: [vocab].props). Keys are leaf keys or family names; a leaf key replaces its family's list.
[triage.avoid]
_all = ["people", "pets"]
rugs = ["furniture", "plants", "decor", "lamps", "pillows", "throws", "toys"]
art_framed = ["furniture", "plants", "lamps", "decor", "pillows"]
art_set = ["furniture", "plants", "lamps", "decor", "pillows"]
mirror_wall = ["furniture", "plants", "decor", "lamps"]
mirror_floor = ["furniture", "plants", "decor", "lamps", "clothes"]
curtain = ["furniture", "plants", "lamps", "decor", "pillows"]
blind_shade = ["furniture", "plants", "lamps", "decor", "pillows"]
bedding_set = ["furniture", "lamps", "plants", "decor", "books", "clothes"]
pillow = ["furniture", "plants", "throws", "decor"]
bed_pillow = ["furniture", "plants", "throws", "decor"]
throw_blanket = ["furniture", "plants", "pillows", "decor"]
lighting = ["furniture", "plants", "decor", "books", "frames"]
tabletop = ["plants", "food", "dishes", "books", "furniture"]
plants = ["furniture", "decor", "books"]
bookcase = ["books", "decor", "plants", "frames", "lamps", "tv"]
display_cabinet = ["books", "decor", "plants", "frames", "lamps", "tv"]
wall_shelf = ["books", "decor", "plants", "frames", "lamps"]
tv = ["furniture", "decor", "plants", "lamps"]
speaker_soundbar = ["furniture", "decor", "plants", "tv"]
dining_table = ["dishes", "food", "plants", "decor", "lamps"]
kids_table_set = ["toys", "dishes", "food", "plants", "decor"]
bed = ["pillows", "throws", "clothes", "decor", "lamps", "plants"]
headboard = ["pillows", "throws", "decor", "lamps", "plants"]
sofa = ["pillows", "throws", "plants", "decor", "lamps"]
sectional = ["pillows", "throws", "plants", "decor", "lamps"]
loveseat = ["pillows", "throws", "plants", "decor", "lamps"]
outdoor = ["plants", "food", "dishes", "decor", "furniture"]

# ---------------------------------------------------------------------------------------------------
# THE LAST RESORT: the `misc` family and the `other` leaf. It matches everything, so it must stay the LAST [[category]].
# ---------------------------------------------------------------------------------------------------
[family.misc]
quads = 2500
flags = []

[[category]]
key = "other"
family = "misc"
label = "Other: no leaf matched in pass 1, pass 2, the breadcrumb or the VLM check (the human queue decides; Tripo 2,500 quads only after a reviewer confirms)"
match = ['.*']
builder = "tripo"
quads = 2500
set = "skip"
on_hit = "queue"
dims = { h = [3, 300], l = [5, 600] }
catalog = ""
na = true
```

### 4.5 Golden probes (the CI test for the router)

Every line below is one probe: `title [|| crumb > crumb] => leaf [; key=value ...]`. The harness (4.7, part C) routes the title through the v3 router and compares each key; `v2=` is checked against the v2 emulation, so every collision in Section 3 is machine-verified, not asserted from memory. Keys: `leaf`, `via` (match, ctx, title, low, crumb, other), `b` builder, `q` quads, `host`, `low` (0 or 1), `mods` and `post` and `flags` (each listed item must be present), `nomods` (none may fire), `set` (identical, mixed, none), `act` (split, first, keep, skip), `dims` (input only: `h90,w200,d95` in cm), `warn` (units or none), `head` (the stripped head phrase). Lines starting with `#` are comments. A probe is a regression test: when a pattern changes, the line either still passes or the change is wrong.

#### 4.5a Verified v2 collisions (`v2=` is what v2's first-match rule does today)

```golden
# --- furniture words that v2 reads as art, pillow, lamp, bed, sofa or stool ---
Art Deco Velvet Accent Chair => accent_chair; v2=art
Print Fabric Accent Chair => accent_chair; v2=art
Canvas Sling Chair => accent_chair; v2=art
Art Deco Sideboard => sideboard; v2=art
Oak Framed Sofa Table => console_table; v2=art
Sofa Table => console_table; v2=sofa
Lamp Table => side_table; v2=lamp
Cedar Blanket Chest => storage_chest; v2=pillow
Blanket Ladder => bookcase; v2=pillow
Daybed => daybed; v2=outdoor_daybed
Twin Daybed with Trundle => daybed; v2=outdoor_daybed
Upholstered Headboard => headboard; v2=bed
Bed Skirt => x_accessory; v2=bed
Bed Tray with Legs => x_accessory; v2=bed
Dog Bed => pet_bed; v2=bed
Orthopedic Dog Bed => pet_bed; v2=bed
Foot Stool => ottoman; v2=dining_chair
Step Stool => ottoman; v2=dining_chair
Console Table => console_table; v2=cabinet
Writing Desk => desk; v2=dining_table
L-Shaped Desk => desk; v2=sectional
Futon Bed Frame => sofa; v2=bed; mods=sleeper
Rug Pad 8x10 => x_accessory; v2=rug
Entryway Hall Tree with Bench and Storage => hall_tree; v2=small_table
Patio Sectional Sofa => outdoor_sofa; v2=sectional
# --- sets: v2 has no set concept ---
Kids Table and Chairs Set => kids_table_set; v2=accent_chair; set=mixed; act=split
Dining Table and 4 Chairs => dining_table; v2=accent_chair; set=mixed; act=split
5-Piece Dining Table Set => dining_table; v2=dining_table; set=mixed; act=split
# --- titles v2 sends to `other` that v3 routes ---
Love Seat => loveseat; v2=other
Chaise Lounge => chaise_lounge; v2=other
Pouffe => ottoman; v2=other
Settee => sofa; v2=other
Queen Mattress => mattress; v2=other
Crib => crib; v2=other
3 in 1 Convertible Crib => crib; v2=other; head=3 in 1 convertible crib
Rhet 5 Drawer Tallboy => chest_of_drawers; v2=other
KALLAX Shelf unit, white => bookcase; v2=other; head=shelf unit
Crystal Chandelier => chandelier; v2=other
Wall Sconce => wall_sconce; v2=other
52 inch Ceiling Fan with Light => ceiling_fan; v2=other
Faux Olive Tree => plant_tree; v2=other
Blackout Curtains => curtain; v2=other
Roman Shade => blind_shade; v2=other
55 Inch 4K Smart TV => tv; v2=other
French Door Refrigerator => appliance_large; v2=other
Treadmill => fitness_machine; v2=other
Freestanding Bathtub => bath_fixture; v2=other
```

#### 4.5b One probe per leaf (all 102 leaf keys are covered; a leaf with no probe fails the run)

```golden
# --- control and accessories ---
Slipcover for Sectional Sofa => x_accessory
Lamp Shade => x_accessory
Mattress Topper Queen => x_accessory
Table Runner => x_accessory
Curtain Rod => x_accessory
Replacement Cushion Cover => x_accessory
# --- compounds that must beat a generic head noun ---
Coat Rack => hall_tree
Foosball Table => game_table
Pool Table => game_table
Calming Dog Bed => pet_bed
Cat Tree Tower => pet_furniture
Wire Dog Crate => pet_furniture
Twin over Full Bunk Bed => kids_bed
Toddler Bed => kids_bed
Convertible Crib => crib
Baby Changing Table => changing_table
Kids Table and Chair Set => kids_table_set
High Chair => kids_table_set
# --- outdoor ---
Propane Fire Pit Table => fire_pit
Hammock Stand => hammock_swing
11 ft Patio Umbrella => patio_umbrella
Charcoal Grill => bbq_grill
Sun Lounger => outdoor_lounger
Outdoor Chaise Lounge => outdoor_lounger; via=ctx
Outdoor Daybed => outdoor_daybed; via=ctx
Adirondack Chair => outdoor_chair; via=match
Patio Dining Chair => outdoor_chair; via=ctx
Picnic Table => outdoor_table; via=match
Outdoor Dining Table => outdoor_table; via=ctx
# --- seating ---
Power Recliner => recliner
Sectional Sofa with Chaise => sectional
Modular Sofa => sectional
Corner Sofa => sectional
L-Shaped Sofa => sectional
Right Arm Facing Chaise => sectional
Loveseat => loveseat
2 Seater Sofa => loveseat
Twin Daybed => daybed
Chaise Lounge => chaise_lounge
3 Seater Sofa => sofa
Chesterfield Sofa => sofa
Sleeper Sofa => sofa
Bean Bag Chair => bean_bag
Ergonomic Office Chair => office_chair; v2=office_chair
Gaming Chair => office_chair
Dining Chair => dining_chair; v2=dining_chair
Parsons Chair => dining_chair
Counter Stool => bar_stool
Swivel Bar Stool => bar_stool
Armchair => accent_chair
Accent Chair => accent_chair
Wingback Chair => accent_chair
Storage Ottoman => ottoman
Pouf => ottoman
Entryway Bench => bench
Dining Bench => bench
# --- tables and desks ---
Lift-Top Coffee Table => coffee_table
End Table => side_table
Round Accent Table => side_table
Round Dining Table => dining_table
Electric Standing Desk => standing_desk
Makeup Vanity Table with Mirror => vanity_table
Dressing Table => vanity_table
# --- bedroom ---
Nightstand => nightstand; v2=nightstand
Bedside Table => nightstand; v2=nightstand
Queen Platform Bed Frame => bed
Sleigh Bed => bed
Storage Trunk => storage_chest
6 Drawer Dresser => chest_of_drawers
Chest of Drawers => chest_of_drawers
Armoire => wardrobe
Wardrobe Closet => wardrobe
Memory Foam Mattress => mattress
Box Spring => mattress
# --- storage and media ---
TV Stand for 65 Inch TV => tv_stand; head=tv stand
Media Console => tv_stand
Curio Cabinet => display_cabinet
Bookcase with Glass Doors => display_cabinet; via=title
5-Shelf Bookcase => bookcase
Etagere => bookcase
Lateral File Cabinet => file_cabinet
Sideboard => sideboard
Credenza => sideboard
Buffet Table => sideboard
Accent Cabinet => accent_cabinet
Storage Cabinet => accent_cabinet
Laundry Hamper => basket_bin
Storage Basket => basket_bin
Folding Room Divider => room_divider
# --- lighting ---
Vanity Light Bar => wall_sconce
Globe Pendant Light => pendant
Semi Flush Mount Ceiling Light => flush_mount
Arc Floor Lamp => floor_lamp
LED Desk Lamp => desk_lamp
Ceramic Table Lamp => table_lamp; v2=lamp
# --- rugs ---
Door Mat => mat_small
Bath Rug => mat_small; v2=rug
Cowhide Rug => rug_shaped
Round Rug => rug_round
Moroccan Area Rug 8x10 => rug_rect; head=moroccan area rug
Runner Rug => rug_rect
# --- wall decor ---
Wall Clock => clock_wall
Full Length Floor Mirror => mirror_floor
Round Wall Mirror => mirror_wall
Floating Shelves => wall_shelf
Set of 3 Framed Prints => art_set
Macrame Wall Hanging => wall_textile
Metal Wall Decor => wall_decor_3d
Framed Wall Art => art_framed
# --- tabletop and objects ---
Ceramic Vase => vase
Ginger Jar => vase
Decorative Bowl => bowl_tray
Serving Tray => bowl_tray
Candle Holder => candle_holder
Hurricane Lantern => candle_holder
Pillar Candle => candle
Abstract Sculpture => sculpture_object
Bookends => sculpture_object
Decorative Books => book_stack
Picture Frame => decor_small
Tabletop Clock => decor_small
# --- plants ---
Ceramic Planter => planter
Plant Pot => planter
Faux Eucalyptus Stems => stems_florals
Artificial Flowers => stems_florals
Fiddle Leaf Fig => plant_tree
Snake Plant => plant_potted
Faux Potted Plant => plant_potted
# --- textiles and window ---
Memory Foam Bed Pillow => bed_pillow
Velvet Throw Pillow => pillow
Lumbar Pillow => pillow
Chunky Knit Throw Blanket => throw_blanket; v2=pillow
Queen Comforter Set => bedding_set
Duvet Cover => bedding_set
# --- kitchen, bath, appliances ---
Bar Cart => bar_cart
Kitchen Island => kitchen_island
Bathroom Vanity with Sink => bath_vanity
Electric Fireplace => fireplace_electric
Fireplace Mantel => fireplace_electric
Soundbar => speaker_soundbar
Tower Fan => fan_heater_purifier
Air Purifier => fan_heater_purifier
Coffee Maker => small_appliance
Pedestal Sink => bath_fixture
# --- nothing matches: the human queue ---
Upright Piano => other; via=other
```

#### 4.5c Retailer-shaped titles, AU and UK words, breadcrumbs (what real feeds look like)

The titles below are the shapes the eight retailers actually publish. IKEA writes `NAME, type, colour, dimensions` (the head is the second comma segment) or `NAME Type, colour`; Living Spaces writes `Name Colour Material Dimension Type`; Temple & Webster and the UK retailers use `lounge`, `tallboy`, `doona`, `pouffe`, `standard lamp`; Wayfair and Crate & Barrel put the noun last. The product names are real examples taken from the retailer pages cited in Section 7; the colour and size tails are typical. A name-only title (`Ravenna`) can only be routed from the breadcrumb, and is always low confidence.

```golden
# --- IKEA: Form A "NAME, type, colour, size" and Form B "NAME Type, colour"; diacritics are ASCII-folded ---
BEKANT, Desk sit/stand, white, 160x80 cm => standing_desk; mods=standing; b=hybrid; q=2500; head=desk sit/stand
MALM, Bed frame, high, white/Luröy, 160x200 cm => bed; head=bed frame
MALM, Chest of 6 drawers, white, 80x123 cm => chest_of_drawers
LINNMON / ALEX, Desk, white, 120x60 cm => desk
PAX, Wardrobe, white, 100x58x201 cm => wardrobe
NORDEN, Gateleg table, birch, 26/89/152x80 cm => dining_table; mods=extension
POÄNG, Armchair, birch veneer/Knisa light blue => accent_chair
BESTÅ, TV bench, black-brown, 120x42x38 cm => tv_stand
SÖDERHAMN, 3-seat sofa, Tonerud grey => sofa
EKTORP, 3-seat sofa, Hakebo dark grey => sofa
KLIPPAN, Loveseat, Vissle grey => loveseat
GRÖNLID, Corner sofa, 4-seat, with chaise longue/Ljungen light grey => sectional
FRIHETEN Corner sofa-bed with storage, Skiftebo dark grey => sectional; mods=sleeper
ÄPPLARÖ, Bench, outdoor, brown stained => bench; mods=outdoor
VITTSJÖ, Shelf unit, black-brown/glass, 100x175 cm => bookcase; mods=glass
KNOPPÄNG, Plant pot, in/outdoor white, 12 cm => planter; b=lathe
HAVÖ, Coffee table, black, 100x55 cm => coffee_table
SKUBB, Box, white, 44x55x19 cm => other; via=other; low=1
# --- Living Spaces style: Name, colour, material, size, type (the page slugs are in Section 7) ---
Ashaway Grey Extendable 66-84 Inch Rectangular Dining Table => dining_table; mods=extension
Mathers Grey Brown Vegan Faux Leather Right Arm Facing Sofa Chaise => sectional
Harper Foam IV Natural Performance Fabric 3-Piece 157-Inch Sectional with Right Arm Facing Chaise => sectional; mods=set; set=none
Carlyle Sofa => sofa
Wilder Power Reclining Sofa => sofa
Kinsley 3-Piece Reclining Sectional => sectional; set=none
Sloane Accent Chair => accent_chair
Peyton Platform Bed => bed
Bryce 5-Drawer Chest => chest_of_drawers
Oslo TV Stand with Fireplace => tv_stand; head=oslo tv stand
Tula 8x10 Area Rug => rug_rect
# --- AU and UK vocabulary (Temple & Webster, Freedom, Oak Furniture Land, The Range) ---
Rhet 5 Drawer Tallboy => chest_of_drawers
Caila 5 Drawer Tallboy => chest_of_drawers
Dressing Table with Stool => vanity_table
Quilt Cover Set Queen => bedding_set; set=identical; act=keep
Bedside Cabinet => nightstand
TV Unit => tv_stand
Standard Lamp => floor_lamp
Scatter Cushion => pillow; b=cushion; q=600; host=su
Throw Cushion => pillow
Nest of Tables => side_table
Hall Table => console_table
Garden Sofa Set => outdoor_sofa; via=ctx; set=mixed; act=skip
3 Seater Lounge Suite => sofa; set=mixed; act=skip; head=3 seater lounge
# --- trailing colour and material words are not the head ---
Velvet Sofa Grey => sofa; head=velvet sofa
Corner Sofa Grey Fabric => sectional; head=corner sofa
Dining Table Walnut => dining_table; head=dining table
Accent Chair Navy Blue => accent_chair; head=accent chair
Bed Frame in Walnut => bed; head=bed frame
Sofa in Grey Velvet => sofa; head=sofa
Bed in a Bag Queen => bedding_set; head=bed in a bag
# --- name-only titles: the breadcrumb decides, and the result is always low confidence ---
Ravenna || Furniture > Living Room > Sofas => sofa; via=crumb; low=1
Aurora || Bedroom > Nightstands & Bedside Tables => nightstand; via=crumb; low=1
Selene || Home Decor > Wall Decor > Mirrors => mirror_wall; via=crumb; low=1
Hudson || Dining Room > Dining Chairs => dining_chair; via=crumb; low=1
Capri || Outdoor > Patio Furniture > Outdoor Sofas => outdoor_sofa; via=crumb; mods=outdoor
Bali || Rugs > Area Rugs => rug_rect; via=crumb; low=1
Mila || Lighting > Floor Lamps => floor_lamp; via=crumb; low=1
```

#### 4.5d Dimension routes, modifiers and set kinds

A `dims=` key is the retailer's listed size in cm (input only). A route that fires on dimensions alone is always low confidence, so it goes to the VLM check; a host-only route changes the placement and never the leaf. `warn=units` is the inches-typed-as-cm check of Section 5.4.

```golden
# --- dims routes (leaf changes) ---
Brass Lamp => floor_lamp; dims=h160,w35,d35
Brass Lamp => table_lamp; dims=h60,w30,d30; host=su
Euro Pillow => bed_pillow; dims=h10,w65,d65
Decorative Pillow => pillow; dims=h12,w45,d45
Throw Blanket => bedding_set; dims=w230,d170
Throw Blanket => throw_blanket; dims=w130,d170
Mirror => mirror_floor; dims=h170,w60,d3; low=1; host=fl
Wall Mirror => mirror_wall; dims=h170,w60,d3
Stool => bar_stool; dims=h75,w40,d40; via=low
Stool => ottoman; dims=h45,w40,d40
Bar Stool => bar_stool; dims=h45,w40,d40; warn=units
Sofa => loveseat; dims=w150,d85; low=1
Sofa => sofa; dims=w210,d90
Faux Plant => plant_tree; dims=h150
Faux Plant => plant_potted; dims=h80
# --- dims routes (host only) ---
Potted Plant => plant_potted; dims=h45; host=su
Planter => planter; dims=h20; host=su
Vase => vase; dims=h80; host=fl
Sculpture => sculpture_object; dims=h90; host=fl
Candle Holder => candle_holder; dims=h70; host=fl
Soundbar => speaker_soundbar; dims=h65; host=fl
Air Purifier => fan_heater_purifier; dims=h40; host=su
Kids Bookcase => bookcase; dims=h80,w60,d30; warn=none
# --- modifiers: placement, postprocess and flags change, the leaf does not ---
Floating TV Stand => tv_stand; mods=floating; host=fl
Wall Mounted Planter => planter; host=wl
Tabletop Mirror => mirror_floor; host=su
Easel Back Framed Print => art_framed; host=su
Unframed Canvas Print => art_framed; host=wl; mods=unframed
Glass Top Coffee Table => coffee_table; mods=glass; post=glass_top
Mesh Office Chair => office_chair; mods=mesh; post=net
Modular Sofa Corner Module => sectional; mods=module
Armless Chair Module => sectional; mods=module
Ladder Bookcase => bookcase; post=tilt
Leaning Mirror => mirror_floor; post=tilt
Rocking Chair => accent_chair; mods=rocker
Bar Height Dining Table => dining_table; mods=bar_height
Counter Height Dining Table => dining_table; mods=bar_height
Standing Desk => standing_desk
Height Adjustable Desk => standing_desk
Extendable Dining Table => dining_table; mods=extension
Kids Sofa => sofa; dims=w90,d60; low=0
# --- set kinds: identical units split or count, a mixed set is split or queued ---
Set of 2 Dining Chairs => dining_chair; set=identical; act=split
Set of 4 Dining Chairs => dining_chair; set=identical; act=split
Dining Chairs Set of 2 => dining_chair; set=identical; act=split
Dining Chair Set of 2 Black => dining_chair; set=identical; act=split
Pair of Table Lamps => table_lamp; set=identical; act=split
Set of 3 Nesting Tables => coffee_table; set=identical; act=split
Hazel 3-Piece Nesting Tables => coffee_table; set=mixed; act=split
Set of 2 Outdoor Chairs => outdoor_chair; via=ctx; set=identical; act=split
2 Pack Throw Pillows => pillow; set=identical; act=first
Set of 3 Framed Prints => art_set; set=identical; act=split
3 Piece Triptych Canvas Print => art_set; set=identical; act=split
Triptych Wall Art => art_set
Triptych Mirror => mirror_wall
Gallery Wall Set of 6 Frames => art_set; via=low
Dining Set Table and 4 Chairs => dining_table; set=mixed; act=split
Living Room Set Sofa and Loveseat => sofa; set=mixed; act=skip
Bedroom Set Queen Bed Nightstand Dresser => chest_of_drawers; set=mixed; act=skip
2-Piece Living Room Set => other; via=other; low=1; set=mixed; act=skip
3 Piece Living Room Set => other; via=other; low=1; set=mixed; act=skip
Patio Conversation Set => other; set=mixed; act=skip
5 Piece Patio Dining Set => other; set=mixed; act=skip
Dumbbell Set => fitness_machine; set=identical; act=split
```

#### 4.5e Other retailers' shapes, the head-noun rule and a stress sample

Wayfair prefixes a brand and writes `Name 82'' Square Arm Sofa`; West Elm puts the size range in parentheses; Crate & Barrel and Article write `Name Colour Noun`; CORT writes `Noun - Style - Colour`. The `with` collisions are the main reason for the head-noun rule: v2 reads the accessory after `with` as the product.

```golden
# --- other retailers' shapes ---
Mercury Row® Kingsbury 82'' Square Arm Sofa => sofa
Wade Logan® Ayan 53'' Wide Tufted Loveseat => loveseat
Brayden Studio® Faulkner 7 Drawer Dresser => chest_of_drawers
Rosalind Wheeler Henshaw 48'' Console Table => console_table
Sand & Stable™ Ethan 24'' Round Side Table => side_table
Joss & Main Linden Velvet Sofa => sofa
Crate & Barrel Peyton Accent Chair => accent_chair
Latitude Run® Chelsea 3 - Piece Living Room Set => other; set=mixed; act=skip
Andes Sofa (72"–112") => sofa; head=andes sofa
Mid-Century Platform Dresser (6-Drawer) => chest_of_drawers
Harmony Modular Sectional => sectional
Terrace Outdoor Dining Table => outdoor_table; via=ctx
Basque Honey Dining Table 60" => dining_table
Peyton Accent Chair => accent_chair
Sven Charme Tan Sofa => sofa
Timber Charcoal Sofa => sofa
Sofa - Modern Fabric - Grey => sofa; head=sofa
# --- the head-noun rule: the accessory after "with" is not the product ---
Dresser with Mirror => chest_of_drawers; v2=mirror
Bathroom Vanity with Mirror => bath_vanity; v2=mirror
Sofa with Throw Pillows => sofa; v2=pillow
Accent Chair with Pillow => accent_chair; v2=pillow
Console Table with Lamp => console_table; v2=lamp
Bed with Nightstands => bed; v2=nightstand
# --- a stress sample of realistic marketplace titles ---
Pavilion Round Coffee Table => coffee_table
Ottoman Coffee Table => coffee_table
Ellis Floor Lamp => floor_lamp
Sienna Console Table => console_table
Weston Counter Height Stool => bar_stool
Aria Wall Mirror => mirror_wall
Baxter Bar Cart => bar_cart
Harlow Kitchen Island => kitchen_island
Wyatt Dining Bench => bench
Storage Ottoman Bench => bench
Kids Twin Loft Bed => kids_bed
Bunk Bed with Desk => kids_bed
Dune Round Pouf => ottoman
Faux Fiddle Leaf Fig Tree => plant_tree
Abstract Canvas Wall Art => art_framed
Ceramic Table Vase => vase; host=su
Woven Basket with Lid => basket_bin; mods=mesh
Cotton Bath Mat => mat_small
Pendant Light => pendant; host=ce
Globe Chandelier => chandelier
Gas Patio Heater => fire_pit
Porch Swing => hammock_swing
Outdoor Rocking Chair => outdoor_chair
Gaming Desk => desk
Computer Desk with Hutch => desk
Shoe Cabinet => accent_cabinet
Umbrella Stand => hall_tree
Magazine Rack => basket_bin
Folding Screen => room_divider
Floating Shelf Set of 3 => wall_shelf; host=wl
Humidifier => fan_heater_purifier
Floor Standing Fan => fan_heater_purifier
Electric Fireplace Insert => fireplace_electric
55 inch Smart TV => tv
Refrigerator => appliance_large
Washing Machine => appliance_large
Dishwasher => appliance_large
Toilet => bath_fixture
Shower Curtain => bath_fixture
Bathroom Vanity 36 inch with Sink => bath_vanity
Crib Mattress => mattress
Kids Play Table => kids_table_set
Cat Tree => pet_furniture
Ping Pong Table => game_table
King Bed Frame => bed
Queen Mattress => mattress
# --- gaps found by the stress runs and fixed (each line is a regression test for one pattern) ---
Black Out Curtain Panels 84 inch Set of 2 => curtain; set=identical; act=first; head=black out curtain panels
Vanity Desk with Mirror => vanity_table; head=vanity desk
Makeup Desk => vanity_table
Wine Rack => bookcase
Wall Mounted Wine Rack => wall_shelf; host=wl
Wine Glass Rack => other; via=other
Room Divider Screen 4 Panel => room_divider
Folding Screen 6 Panel => room_divider
Wall Sconce Plug In => wall_sconce; host=wl
Plug In Wall Sconce => wall_sconce; host=wl; head=plug in wall sconce
Wall Sconce Battery Operated => wall_sconce
Dog Crate Furniture => pet_furniture
Canvas Wall Art 3 Panel => art_set
Built In Bookcase => bookcase; head=built in bookcase
Walk In Closet Organizer => other; via=other
Yoga Mat => other; via=other
```

#### 4.5f The stress sweep (forms that were wrong, were fixed, and are now regression tests)

About 320 realistic titles were routed after 4.5a to 4.5e passed, and every miss was fixed on the merits (the pattern or the expectation, whichever was wrong). The survivors below pin a decision: a farmhouse or extendable side table is a side table; coffee makers, mixers and food processors are small appliances; "3 in 1", "only" and a trailing door or drawer count are not part of the head; a bare set name that names no piece goes to the human queue; string lights never become a lamp build.

```golden
# --- side tables: style words are not excludes ---
Rustic Farmhouse End Table => side_table
Farmhouse Side Table with Storage => side_table; head=farmhouse side table
Extendable Side Table => side_table; mods=extension
Pedestal Side Table => side_table
Pedestal Table => dining_table; via=low; low=1
Plant Stand => side_table
# --- counter-top appliances are small_appliance (host su); toys and dishwashers are not ---
KitchenAid Artisan 5 Qt Stand Mixer => small_appliance; host=su
Ninja 12-Cup Programmable Coffee Maker => small_appliance; host=su
Keurig K-Mini Single Serve Pod Coffee Maker => small_appliance
Hamilton Beach Glass Carafe Coffee Maker => small_appliance
Filter Coffee Machine => small_appliance
Nespresso Capsule Coffee Machine => small_appliance
Cuisinart 14-Cup Food Processor => small_appliance
Kids Pretend Play Coffee Maker => other; via=other
Portable Dishwasher => other; via=other
Countertop Dishwasher => other; via=other
# --- trailing words that are not the head: multi-use counts, "only", door and drawer counts ---
Convertible Crib 3 in 1 => crib; head=convertible crib
Queen Headboard Only => headboard
Wardrobe 3 Door => wardrobe; head=wardrobe
Dresser 6 Drawer => chest_of_drawers; head=dresser
Sofa 3 Seater => sofa; head=sofa
Chest of 5 Drawers => chest_of_drawers; head=chest of 5 drawers
# --- outdoor, plants and things that are not furniture ---
Hammock Chair Stand => hammock_swing
Gas BBQ Grill => bbq_grill
Fire Pit Table => fire_pit
Folding Chair => dining_chair
Papasan Chair => accent_chair
Monstera Deliciosa => plant_potted
Sansevieria in Pot => plant_potted
Planter Pot => planter; via=low; low=1
Pot Stand => other; via=other
Pergola => other; via=other
Gazebo => other; via=other
# --- hosts ---
Wall Mounted Coat Rack => hall_tree; host=wl
Easel Back Mirror => mirror_wall; host=su
Leaning Floor Mirror => mirror_floor; mods=ladder
# --- accessories and lights that must not become furniture ---
TV Wall Mount => x_accessory
Euro Sham => x_accessory
Placemat Set => x_accessory
String Lights => other; via=other
Fairy Lights => other; via=other
# --- storage, bath, bedroom ---
Shoe Cabinet with 3 Flip Drawers => accent_cabinet; head=shoe cabinet
Bar Cabinet with Wine Rack => display_cabinet; head=bar cabinet
Double Vanity 72 Inch => bath_vanity
Vanity Stool => ottoman
Vanity => vanity_table; low=1
Tallboy => chest_of_drawers
KALLAX Shelf unit => bookcase
Bar Trolley => bar_cart
# --- AU and UK words ---
Chaise Longue => chaise_lounge
Single Mattress => mattress
Doona => bedding_set
Quilt Cover => bedding_set
Roman Blind => blind_shade; host=wl
Barstool => bar_stool
Loveseat Recliner => recliner
Floor Cushion => bean_bag
Futon => sofa; mods=sleeper
Day Bed => daybed
Bunk Bed => kids_bed
Cat Scratching Post => pet_furniture
# --- bare set names that name no piece go to the human queue (the kind label can be either; the action is skip) ---
Marlow 5 Piece Dining Set => other; act=skip
Pub Set => other; act=skip
Dining Room Set => other; set=mixed; act=skip
Patio Dining Set => other; set=mixed; act=skip
```

#### 4.5g Shadowing fixes (the pattern-liveness sampler, 2026-10-22)

A generator that builds one sample string from every pattern of every leaf (4.6) found 133 strings, out of 5,794, that a different leaf won. Most were intended overlaps ("nest of coffee tables" is a coffee table); the lines below pin the ones that were real shadowing bugs, each fixed in the leaf named in its comment.

```golden
# --- seating: "rise and recline" was unreachable (head cut), "chaise suite" lost its suite, "sleeper loveseat" is a loveseat ---
Rise & Recline Chair => recliner; via=title
Rise and Recline Lift Chair => recliner; via=title
Zero Gravity Chair => outdoor_lounger
Zero Gravity Massage Chair => recliner
Chaise Suite => sectional
Corner Suite => sectional
Lounge Suite => sofa; set=mixed; act=skip
Sleeper Loveseat => loveseat; mods=sleeper
Headboard Bench => bench
# --- tables and bedroom ---
Nest of Coffee Tables => coffee_table
Nest of 3 Tables => side_table
Craft Table => desk
Kids Craft Table => kids_table_set
China Closet => display_cabinet
Jewelry Armoire => accent_cabinet
Shoe Closet => accent_cabinet
Armoire => wardrobe
Chiffonier => chest_of_drawers
# --- storage ---
Display Unit => display_cabinet
Display Shelving Unit => bookcase
Storage Unit => bookcase
Storage Cube => basket_bin
Cube Ottoman => ottoman
Floating Cabinet => wall_shelf; host=wl
Kitchen Island Bench => kitchen_island
Island Cabinet => kitchen_island
Wall Unit => other
# --- bath ---
Bathroom Vanity Cabinet => bath_vanity
Vanity Unit => bath_vanity
Sink Cabinet => bath_vanity
Vanity Cabinet => bath_vanity
Vanity Set => vanity_table; via=low; low=1
# --- lighting, wall decor, tabletop ---
Reading Lamp => table_lamp
Reading Light => desk_lamp; via=low; low=1
Adjustable Desk Lamp => desk_lamp
Picture Frame => decor_small
Collage Picture Frame => art_framed; via=low; low=1
Tabletop Plaque => decor_small
# --- plants, textiles, kitchen ---
Raised Garden Bed => planter
Garden Bed => planter
Vegetable Garden Bed => planter
Hanging Basket => planter
Plant Basket => planter
Laundry Basket => basket_bin
Bed Linen => bedding_set
Bed Throw => throw_blanket
Quilt in a Box => bedding_set
Bedding in a Bag => bedding_set
Bed in a Box => mattress
Slow Cooker => small_appliance
Rice Cooker => small_appliance
Multi Cooker => small_appliance
Range Cooker => appliance_large
```

<!-- GOLDEN-HERE -->

### 4.7 The executable reference router and checker

The `python harness` fences below are ONE program, written in three parts (A: loader and schema checks; B: the v3 router and the v2 emulation; C: the golden runner and reports). It needs Python 3.11 or newer (`tomllib`) and the standard library only. It reads this report and v2's `rules.toml` read-only and writes nothing; it is meant to run from stdin so no script file is created. The bootstrap joins the fences and executes them:

```text
import re
REPORT = r'<path to this report>'
V2_RULES = r'<path to AssetAutoGenerator_v2\rules.toml>'
t = open(REPORT, encoding='utf-8').read()
exec(compile('\n'.join(re.findall(r'^```python harness\n(.*?)^```', t, re.S | re.M)), 'harness', 'exec'))
```

Run it as `python -I - [--v2] [--dead] [--leaves] [--set]` with the bootstrap on stdin (PowerShell: pipe a here-string; bash: a heredoc). No flag prints the schema check and the golden results; `--v2` prints the v2-versus-v3 table of Section 3; `--leaves` prints one resolved row per leaf; `--dead` lists patterns that no golden probe ever hit; `--set` prints the set-kind decisions.

```python harness
# ---- A. loader, constants and schema checks (Python 3.11+, stdlib only; run with `python -I`) ----
import re, sys, tomllib, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ARGV = sys.argv[1:]
TEXT = open(REPORT, encoding='utf-8').read()          # REPORT and V2_RULES come from the bootstrap
FENCE = re.compile(r'^```([\w-]+)([^\n]*)\n(.*?)^```[ \t]*$', re.S | re.M)
def fences(text, lang, tag=None):
    return [m.group(3) for m in FENCE.finditer(text) if m.group(1) == lang and (tag is None or m.group(2).strip() == tag)]
S4 = TEXT[TEXT.index('\n## 4. Proposed v3'):]
S4 = S4[:S4.index('\n### 4.5')] if '\n### 4.5' in S4 else S4      # only 4.1 to 4.4b hold the v3 rules.toml fences
CFG = tomllib.loads('\n'.join(fences(S4, 'toml')))
CAT, FAM, VOC, DEF, DET = CFG['category'], CFG['family'], CFG['vocab'], CFG['defaults'], CFG['detect']
SD, MODS = CFG['set_detect'], CFG['modifier']
BYKEY = {c['key']: c for c in CAT}
PROC = {'rug', 'art', 'box', 'lathe', 'drape', 'slab', 'cushion', 'cards'}      # house-built primary builders
SETV = {'split', 'first', 'keep', 'skip'}
ACTIONS = {'next_view', 'crop_matte', 'drop', 'rectify', 'hybrid', 'queue'}
LEAF_KEYS = set('key family label match match_low match_ctx match_title exclude ctx builder alt host scale quads postprocess multi_image views dims flags catalog na resizable resizable_house set set_mixed bed_frame_photo uniform_scale_match thickness_cm proc_gate builder_by_head front pivot on_hit'.split())
FAM_KEYS = set('host quads flags postprocess scale builder resizable resizable_house views multi_image set front pivot thickness_cm'.split())
MOD_KEYS = set('on regex gate delegate route host host_leaves add_flags add_flags_except_families add_postprocess_by_leaf add_postprocess_by_family dims_by_leaf dims_scale dims_scale_except_families thickness_cm thickness_leaves dim_pick meta note'.split())
TOP_KEYS = set('schema_version detect vocab host_map defaults family category set_detect modifier proc_gate dims_route dims_parse triage'.split())
# snapshot of ALLOWED_CATEGORIES in src/api/assetsAPI.js (21 supers, 166 names, 2026-10-22)
ALLOWED = set('''Beds|Bunk Beds|Full Size Beds|Kids & Toddlers Beds|King Size Beds|King Bed|Loft Beds|Queen Size Beds|Queen Bed|Super King Size Beds|Twin Beds|Twin Bed|Double Bed|Queen Headboard|Twin Headboard|Mattress - Queen Size|Mattress - Twin Size|Box Spring and Frame - Queen Size|Bedroom Benches|Dining Benches|Outdoor Benches|Storage Benches|Coffee Tables|Coffee Table|Coffee & Side Tables|Side Tables|End Table|Outdoor Coffee Table|Outdoor Side Table|Dining Tables|Outdoor Dining Tables|Oval Dining Tables|Rectangular Dining Tables|Round Dining Tables|Square Dining Tables|Bar Tables|Outdoor Bar Tables|Table|Desks|Writing Desk|Home Office|Office Chairs|Task Chair|Office Accessories|Accent Chair|Armchairs|Living Room Chairs|Recliner|Rocking Chairs|Nod Chairs|Chair|Dining Chairs|Dining Chair|Dining Room Chairs|Bar & Counter Stools|Bar Stool|Counter Height Chair|Folding Chairs|Outdoor Chairs|Outdoor Dining Chairs|Outdoor Bar Stools|Stools|Dressers & Chests|Dresser|Accent Chests|Chest of Drawers|Nightstands|Nightstand|Plants|Terrace Outdoor|2 Seat Sofas|3 Seat Sofas|Apartment Sofas|Day Beds|Futons & Sleeper Sofas|Sectional Sofas|Sofas|Sofa|Loveseat|Sleeper Sofa|Outdoor Sofas|Long Sofas|Poufs|Footstools|Console Tables|TV Console|Bookcases|Buffets and Credenzas|Cabinets|Closets|Filling Cabinets|Shelving Units|Shelving|Storage|Wall Shelves|Wardrobe|Shoe Racks|Room Divider|Kitchen Islands|Kitchen & Dining Carts|Entryway & General|Rugs|Rug|Area Rugs|Kids' Rugs|Kitchen Mats|Curtains|Drape|Shades|Window Treatments|Sheets and Blankets|Pillows|Cushions|Throws|Ceiling Lighting|Floor Lamp|Lamps|Lighting|Standing Lamps|Table Lamps|Table Lamp|Desk Lamps|Desk Lamp|Wall Lighting|Kitchen & Dining Lighting|Artwork|Paintings & Pictures|Wall Art|Wall Decor|Wall Decor Misc|Decorations|Decor|Decorative Objects|Mirrors|Mirror|Sculptures & Figurines|Table Frames|Vases & Jars|Clocks|Living Room Accessories|Accessory|General Accessories|Other|Design Misc|Bedroom Accessories|Kitchen Accessories|Dining Room Accessories|Outdoor|Living Room|Bedroom|Room Shape|Standing TVs|TVs|TV(50 and larger)|TV (32 - 43)|TV(32 - 43)|Entertainment|Computers|Gaming|Refrigerators|Washing Machines|Kitchen Appliances|Toys|Kids Bedroom Accessories|Pets|Clothing'''.split('|'))

def resolve(c):
    """Leaf over family over defaults. Lists REPLACE, they never merge."""
    r = dict(DEF); r.update(FAM.get(c.get('family'), {})); r.update(c); return r

ERR = []
def err(m): ERR.append(m)
def rx(p, where):
    try: return re.compile(p)
    except re.error as e: err(f'{where}: bad regex {p!r}: {e}')
def chk_vals(w, r):
    for b in ('builder', 'alt'):
        if b in r and r[b] not in VOC['builders']: err(f'{w}: {b}={r[b]!r} not in vocab.builders')
    if 'host' in r and r['host'] not in VOC['hosts']: err(f'{w}: host {r["host"]!r}')
    if 'scale' in r and r['scale'] not in VOC['scales']: err(f'{w}: scale {r["scale"]!r}')
    for key, voc in (('flags', 'flags'), ('postprocess', 'postprocess'), ('views', 'views')):
        for x in r.get(key, []):
            if x not in VOC[voc]: err(f'{w}: {key} entry {x!r} not in vocab.{voc}')

def validate():
    for k in CFG:
        if k not in TOP_KEYS: err(f'top-level key {k!r}')
    if CFG.get('schema_version') != 3: err('schema_version must be 3')
    for k in ('head_cut', 'tail_strip', 'trail_finish', 'brand_strip'): rx(DET[k], 'detect.' + k)
    for k in ('hosts', 'builders', 'scales', 'props', 'views', 'postprocess', 'flags'):
        if k not in VOC: err(f'vocab.{k} missing')
    for fam, f in FAM.items():
        for k in f:
            if k not in FAM_KEYS: err(f'family.{fam}: unknown key {k}')
        chk_vals(f'family.{fam}', f)
    seen = set()
    for i, c in enumerate(CAT):
        k = c.get('key', f'#{i}')
        if k in seen: err(f'{k}: duplicate key')
        seen.add(k)
        for x in c:
            if x not in LEAF_KEYS: err(f'{k}: unknown leaf key {x!r}')
        if c.get('family') not in FAM: err(f'{k}: unknown family {c.get("family")!r}')
        chk_vals(k, c)
        r = resolve(c)
        for fld in ('match', 'match_low', 'match_ctx', 'match_title', 'exclude'):
            for p in c.get(fld, []): rx(p, f'{k}.{fld}')
        if not any(c.get(f) for f in ('match', 'match_low', 'match_ctx', 'match_title')): err(f'{k}: no matcher')
        if c.get('match_ctx') and not c.get('ctx'): err(f'{k}: match_ctx without ctx')
        if c.get('ctx') and c['ctx'] not in MODS: err(f'{k}: ctx {c["ctx"]!r} is not a modifier')
        for fld in ('set', 'set_mixed'):
            if fld in r and r[fld] not in SETV: err(f'{k}: {fld} {r[fld]!r}')
        if r['builder'] != 'skip' and 'dims' not in c: err(f'{k}: dims missing')
        for ax in ('h', 'l'):
            v = c.get('dims', {}).get(ax)
            if 'dims' in c and not (isinstance(v, list) and len(v) == 2 and 0 <= v[0] < v[1]): err(f'{k}: dims.{ax} {v!r}')
        if not isinstance(r['quads'], int) or not (0 if r['builder'] == 'skip' else 1) <= r['quads'] <= 25000: err(f'{k}: quads {r["quads"]!r}')
        if r['builder'] in PROC and not r.get('resizable_house'): err(f'{k}: builder {r["builder"]} but resizable_house is not set')
        if r.get('resizable_house') and r['builder'] not in PROC and r.get('alt') not in PROC: err(f'{k}: resizable_house with no procedural builder or alt')
        if c.get('proc_gate') and 'alt' not in r: err(f'{k}: proc_gate needs alt')
        gated = {r['builder']} | set(c.get('builder_by_head', {}))          # `decor_small` gates only its lathe clocks
        if c.get('proc_gate') and not gated & {'lathe', 'cushion', 'box'}: err(f'{k}: proc_gate on builder {sorted(gated)}')
        if r['builder'] in ('lathe', 'cushion') and not c.get('proc_gate'): err(f'{k}: {r["builder"]} primary needs proc_gate')
        if r['builder'] == 'box' and 'alt' in r and not c.get('proc_gate'): err(f'{k}: box primary with alt needs proc_gate')
        for b in (r['builder'], r.get('alt')):
            if c.get('proc_gate') and b in ('lathe', 'cushion', 'box') and b not in CFG['proc_gate']: err(f'{k}: no [proc_gate.{b}]')
        cat = c.get('catalog'); names = [cat] if isinstance(cat, str) else list(cat or [])
        okn = [n for n in names if n in ALLOWED]
        if c.get('na') and okn: err(f'{k}: na = true but {okn} is allowed')
        if not c.get('na') and not okn and not (r['builder'] == 'skip' and 'catalog' not in c): err(f'{k}: catalog {names} has no allowed name (set na = true if none exists)')
    if CAT[-1]['key'] != 'other' or CAT[-1]['match'] != ['.*']: err('the last [[category]] must be `other` with match [".*"]')
    for name, m in MODS.items():
        w = f'modifier.{name}'
        for x in m:
            if x not in MOD_KEYS: err(f'{w}: unknown key {x}')
        if m.get('on') not in ('head', 'title', 'ctx', 'strip'): err(f'{w}: on {m.get("on")!r}')
        if m.get('on') != 'strip' and 'regex' not in m: err(f'{w}: no regex')
        if 'regex' in m: rx(m['regex'], f'{w}.regex')
        for fld in ('host_leaves', 'thickness_leaves'):
            for x in m.get(fld, []):
                if x not in BYKEY: err(f'{w}.{fld}: unknown leaf {x}')
        if 'host' in m and (m['host'] not in VOC['hosts'] or not m.get('host_leaves')): err(f'{w}: host needs a valid value and host_leaves')
        for a, b in m.get('route', {}).items():
            if a not in BYKEY or b not in BYKEY: err(f'{w}.route: {a}->{b}')
        for fld in ('add_postprocess_by_leaf', 'dims_by_leaf'):
            for x in m.get(fld, {}):
                if x not in BYKEY: err(f'{w}.{fld}: unknown leaf {x}')
        for x, lst in m.get('add_postprocess_by_leaf', {}).items():
            for p in lst:
                if p not in VOC['postprocess']: err(f'{w}: postprocess {p}')
        for x, lst in m.get('add_postprocess_by_family', {}).items():
            if x not in FAM: err(f'{w}: unknown family {x}')
            for p in lst:
                if p not in VOC['postprocess']: err(f'{w}: postprocess {p}')
        for f in m.get('add_flags', []):
            if f not in VOC['flags']: err(f'{w}: flag {f}')
        for x in m.get('add_flags_except_families', []) + m.get('dims_scale_except_families', []):
            if x not in FAM: err(f'{w}: unknown family {x}')
        if m.get('dim_pick') not in (None, 'min', 'max'): err(f'{w}: dim_pick')
    for f in ('trail_regex', 'count_regex', 'mixed_words', 'mixed_join', 'keep_suite'): rx(SD[f], f'set_detect.{f}')
    for x in SD.get('exempt_leaves', []):
        if x not in BYKEY: err(f'set_detect.exempt_leaves: {x}')
    for a, b in SD.get('route', {}).items():
        if a not in BYKEY or b not in BYKEY: err(f'set_detect.route: {a}->{b}')
    for i, dr in enumerate(CFG.get('dims_route', [])):
        w = f'dims_route[{i}] {dr.get("from")}'
        if dr['from'] not in BYKEY or ('to' in dr and dr['to'] not in BYKEY): err(f'{w}: unknown leaf')
        if 'to' not in dr and 'host' not in dr: err(f'{w}: needs `to` or `host`')
        if 'host' in dr and dr['host'] not in VOC['hosts']: err(f'{w}: host')
        try: eval(dr['when'], {'__builtins__': {}}, dict(h=1, w=1, d=1, lmax=1, lmin=1))
        except Exception as e: err(f'{w}: when: {e}')
        if 'title_not' in dr: rx(dr['title_not'], w)
        if dr.get('only') not in (None, 'low') or dr.get('confidence') not in (None, 'low'): err(f'{w}: only/confidence')
    T = CFG['triage']
    for f in ('filename_reject', 'filename_prefer'): rx(T[f], 'triage.' + f)
    for x in T['flat_leaves']:
        if x not in BYKEY: err(f'triage.flat_leaves: {x}')
    for x, lst in T.get('avoid', {}).items():
        if x != '_all' and x not in BYKEY and x not in FAM: err(f'triage.avoid: {x} is neither a leaf nor a family')
        for p in lst:
            if p not in VOC['props']: err(f'triage.avoid.{x}: prop {p}')
    for a, v in T['action'].items():
        if v not in ACTIONS: err(f'triage.action.{a}: {v}')

validate()
```

```python harness
# ---- B. the v3 router (the reference implementation of 5.1 to 5.3) and the v2 emulation ----
_RX = {}
def R(p):
    if p not in _RX: _RX[p] = re.compile(p)
    return _RX[p]
_FRAC = {'½': '.5', '¼': '.25', '¾': '.75', '⅓': '.33', '⅔': '.67', '⅛': '.125'}

def fold(s):
    """5.1 step 2: drop (TM)/(R)/(C), ASCII-fold, lowercase, drop apostrophes; 60" becomes 60 in and 8' becomes 8 ft."""
    s = s.replace(' ', ' ')
    s = re.sub(r'\((?:tm|r|c)\)', '', s, flags=re.I)
    for ch in '™®©': s = s.replace(ch, '')
    for a, b in _FRAC.items(): s = s.replace(a, b)
    s = s.replace('×', 'x').replace('–', '-').replace('—', '-')
    s = re.sub(r'(?<=\d)\s*["″”]', ' in ', s)
    s = re.sub(r"(?<=\d)\s*['′’](?=\s*(?:x\b|\d|$))", ' ft ', s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = s.lower().replace("'", '').replace('"', '')
    return re.sub(r'\s+', ' ', s).strip()

def ikea_strip(t):
    """5.1 step 1, on the ORIGINAL-case title. Form A "BEKANT, Desk sit/stand, white, 160x80 cm"; Form B "KALLAX Shelf unit, white"."""
    W = r"[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'&-]{2,}"             # an IKEA name word: 3+ capitals ("PAX", "POANG" with umlaut, "BESTA")
    ACR = r"(?!(?:LED|USB|HDMI|LCD|MDF|PVC|LAF|RAF|LHF|RHF|XXL|KING|TWIN|FULL|QUEEN)\b)"           # acronyms and size words are not IKEA names
    segs = [x.strip() for x in t.split(',')]
    s0 = segs[0]
    if len(segs) >= 2 and re.fullmatch(rf"{ACR}{W}(?: (?:/ )?{W}){{0,2}}", s0) and re.search(r'[a-z]', segs[1]):      # "LINNMON / ALEX" is one name; "HAVÖ, Side table" has two segments
        return ', '.join(segs[1:]), 'A'
    m = re.match(rf"{ACR}(?:{W} )+(?=[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿ])", t)
    return (t[m.end():], 'B') if m else (t, None)

UNIT, NUM = r'(?:cm|mm|m|in|inch|inches|ft|feet|foot|yd)', r'\d+(?:\.\d+)?'
DIMS_TAIL = re.compile(rf'[\s,-]+(?:{NUM}(?:\s*{UNIT})?(?:\s*(?:x|by|-|to)\s*{NUM}(?:\s*{UNIT})?)+|{NUM}\s*{UNIT})(?:\s*(?:w|d|h|l|dia|diameter))?$')
SIZE_TAIL = re.compile(r'\s+(?:twin xl|full xl|twin|full|double|queen|king|california king|cal king|super king|king single|single|small double)(?:\s+sized?)?$')

def head_of(t):
    """5.1 steps 3 to 5, looped until stable: cut at head_cut, drop trailing dims and size words, drop "in <finish>"."""
    h = t
    for _ in range(8):
        p = h
        m = R(DET['head_cut']).search(h)
        if m and h[:m.start()].strip(): h = h[:m.start()]
        for rg in (DIMS_TAIL, SIZE_TAIL, R(DET['tail_strip']), R(DET['trail_finish'])):
            m = rg.search(h)
            if m and h[:m.start()].strip(): h = h[:m.start()]
        h = h.strip(' ,.;:/-')
        if h == p: break
    return h

def strip_sets(h):
    """5.1 step 6: trailing set words and "set of N" (not a `keep_suite` head such as "chaise suite"); returns (head, markers)."""
    marks, tw, ks = [], '|'.join(SD['trail_words']), SD.get('keep_suite')
    for _ in range(4):
        p = h
        for rg in (R(SD['trail_regex']), re.compile(rf'\s(?:{tw})s?$')):
            m = rg.search(h)
            if m and h[:m.start()].strip() and not (ks and R(ks).search(h)): marks.append(m.group(0).strip()); h = h[:m.start()].rstrip()
        h = h.strip(' ,.;:/-')
        if h == p: break
    return h, marks

def head_info(title):
    t, shape = ikea_strip(title.strip())
    ft = fold(t); hf = head_of(R(DET['brand_strip']).sub('', ft, count=1)); hs, marks = strip_sets(hf)
    for _ in range(3):                                    # "curtain panels 84 inch set of 2": the dims only end the head once the set words are gone
        h2 = head_of(hs)
        if h2 == hs: break
        hs, m2 = strip_sets(h2); marks += m2
    return dict(title=ft, head_full=hf, head=hs, marks=marks, count=bool(R(SD['count_regex']).search(ft)), shape=shape)

def fire_mods(info, ctx):
    out = {}
    for name, m in MODS.items():
        on = m['on']
        ok = bool(info['marks'] or info['count']) if on == 'strip' else bool(R(m['regex']).search({'head': info['head_full'], 'title': info['title'], 'ctx': ctx}[on]))
        if ok: out[name] = m
    return out

def excl(c, head):
    return [j for j, x in enumerate(c.get('exclude', [])) if R(x).search(head)]

EXC_HITS = set()
def leaf_match(c, head, title, fired, first, pas):
    """One leaf against one head form. Returns (field, index) or None. exclude is tested on the head and never on match_title."""
    if pas == 1:
        pats = [('match', i, p) for i, p in enumerate(c.get('match', []))]
        if c.get('ctx') in fired and MODS[c['ctx']].get('gate'): pats += [('match_ctx', i, p) for i, p in enumerate(c.get('match_ctx', []))]
        for fld, i, p in pats:
            if R(p).search(head):
                ex = excl(c, head)
                if ex: EXC_HITS.update((c['key'], 'exclude', j) for j in ex); continue
                return fld, i
        if first:
            for i, p in enumerate(c.get('match_title', [])):
                if R(p).search(title): return 'match_title', i
    else:
        for i, p in enumerate(c.get('match_low', [])):
            if R(p).search(head):
                ex = excl(c, head)
                if ex: EXC_HITS.update((c['key'], 'exclude', j) for j in ex); continue
                return 'match_low', i
    return None

def crumb_segments(crumbs):
    out = []
    for cr in list(crumbs)[-DET['breadcrumb_depth']:][::-1]:                 # most specific crumb first
        out += [s.strip() for s in re.split(r'\s+(?:&|and)\s+|[,/]', fold(cr)) if s.strip()]
    return out

HITS = set()
def record_hits(c, form, title):
    for fld in ('match', 'match_ctx', 'match_low'):
        for i, p in enumerate(c.get(fld, [])):
            if R(p).search(form): HITS.add((c['key'], fld, i))
    for i, p in enumerate(c.get('match_title', [])):
        if R(p).search(title): HITS.add((c['key'], 'match_title', i))

IDENT = re.compile(r'\b(?:set|pair|pack|lot|bundle) of (?:\d{1,2}|two|three|four|five|six|eight|ten|twelve)\b|\b\d{1,2}[- ]?(?:pack|pk)\b|\b(?:pair|duo|trio)\b')
def set_kind(leaf, info):
    """Set kind and action for the chosen leaf (4.4 "Set kind"): returns (kind, action) or None."""
    c = BYKEY[leaf]; r = resolve(c)
    if leaf in SD['exempt_leaves']: return None
    mj = 'set_mixed' in c and bool(R(SD['mixed_join']).search(info['title']))
    if not (info['marks'] or info['count'] or mj): return None
    ident = bool(IDENT.search(info['title']))                      # an explicit identical phrase beats a room word, never a mixed join
    mixed = mj or (not ident and (bool(R(SD['mixed_words']).search(info['title'])) or 'set_mixed' in c))
    return ('mixed', r.get('set_mixed', 'skip')) if mixed else ('identical', r['set'])

def eval_when(expr, v):
    try: return bool(eval(expr, {'__builtins__': {}}, v))
    except TypeError: return False                    # a missing dimension (None) never fires a route

def dim_vars(dims):
    d = dims or {}; wd = [x for x in (d.get('w'), d.get('d')) if x is not None]
    return dict(h=d.get('h'), w=d.get('w'), d=d.get('d'), lmax=max(wd) if wd else None, lmin=min(wd) if len(wd) == 2 else None)

def route(title, crumbs=(), dims=None):
    """The reference router: head phrase, modifiers, pass 1 (stripped head, then unstripped head), pass 2, breadcrumb, `other`; then
    modifier routes, set kind, dims routes and attribute resolution. Returns a dict."""
    info = head_info(title)
    fired = fire_mods(info, fold(' '.join([title] + list(crumbs)[-DET['breadcrumb_depth']:])))
    forms = [info['head']] + ([info['head_full']] if info['head_full'] != info['head'] else [])
    hit = None
    for pas in (1, 2):
        for fi, form in enumerate(forms):
            for c in CAT[:-1]:
                h = leaf_match(c, form, info['title'], fired, fi == 0, pas)
                if h: hit = (c, h, pas, form, {'match': 'match', 'match_ctx': 'ctx', 'match_title': 'title', 'match_low': 'low'}[h[0]]); break
            if hit: break
        if hit: break
    if not hit:
        for seg in crumb_segments(crumbs):
            for pas in (1, 2):
                for c in CAT[:-1]:
                    h = leaf_match(c, seg, info['title'], fired, False, pas)
                    if h: hit = (c, h, 3, seg, 'crumb'); break
                if hit: break
            if hit: break
    if hit:
        c, (fld, idx), pas, form, via = hit; record_hits(c, form, info['title']); leaf = c['key']; pat = c[fld][idx]
    else:
        leaf, via, pas, pat = 'other', 'other', 4, None
    low = pas >= 2
    for m in fired.values():                                                  # modifier routes: sleeper bed -> sofa, standing desk -> standing_desk
        leaf = m.get('route', {}).get(leaf, leaf)
    sk = set_kind(leaf, info)
    if sk and leaf in SD['route']: leaf = SD['route'][leaf]
    vars_, hops = dim_vars(dims), 0
    while hops < 3:                                                           # dims routes, up to three hops
        for dr in CFG.get('dims_route', []):
            if dr['from'] != leaf or 'to' not in dr: continue
            if dr.get('only') == 'low' and not low: continue
            if 'title_not' in dr and R(dr['title_not']).search(info['title']): continue
            if eval_when(dr['when'], vars_):
                leaf = dr['to']; low = low or dr.get('confidence') == 'low'; hops += 1; break
        else: break
    c = BYKEY[leaf]; r = resolve(c)
    host, post, flags = r['host'], list(r.get('postprocess', [])), list(r.get('flags', []))
    rng = {k: list(v) for k, v in c.get('dims', {}).items()}; thick = None          # a `skip` leaf (x_accessory) carries no dims
    for name, m in fired.items():
        if 'host' in m and leaf in m.get('host_leaves', []): host = m['host']
        for f in m.get('add_flags', []):
            if r['family'] not in m.get('add_flags_except_families', []) and f not in flags: flags.append(f)
        for p in m.get('add_postprocess_by_leaf', {}).get(leaf, []) + m.get('add_postprocess_by_family', {}).get(r['family'], []):
            if p not in post: post.append(p)
        if 'dims_scale' in m and r['family'] not in m.get('dims_scale_except_families', []):
            for k, (a, b) in m['dims_scale'].items():
                if k in rng: rng[k] = [rng[k][0] * a, rng[k][1] * b]
        for k, v in m.get('dims_by_leaf', {}).get(leaf, {}).items(): rng[k] = list(v)
        if leaf in m.get('thickness_leaves', []): thick = m['thickness_cm']
    for dr in CFG.get('dims_route', []):                                      # host-only routes run on the final leaf
        if dr['from'] == leaf and 'to' not in dr and eval_when(dr['when'], vars_): host = dr['host']
    warn = None
    if dims and rng and ((vars_['h'] is not None and not rng['h'][0] <= vars_['h'] <= rng['h'][1]) or (vars_['lmax'] is not None and not rng['l'][0] <= vars_['lmax'] <= rng['l'][1])): warn = 'units'
    return dict(leaf=leaf, via=via, pat=pat, pas=pas, low=low, mods=sorted(fired), set=sk, builder=r['builder'], alt=r.get('alt'), host=host,
                quads=r['quads'], post=post, flags=flags, dims=rng, thick=thick, warn=warn, head=info['head'], head_full=info['head_full'], marks=info['marks'])

# v2 emulation: v2's own rules.toml, first category whose match hits (title plus breadcrumb, lowercase) and none of whose exclude patterns hit
V2 = tomllib.load(open(V2_RULES, 'rb'))
def v2_route(title, crumbs=()):
    text = (title + ' ' + ' '.join(crumbs)).lower()
    for c in V2['category']:
        if any(re.search(p, text) for p in c['match']) and not any(re.search(p, text) for p in c.get('exclude', [])): return c['key']
V2_MAP = {k: set(v.split()) for k, v in {
    'rug': 'rug_rect rug_round rug_shaped mat_small', 'mirror': 'mirror_wall mirror_floor', 'art': 'art_framed art_set wall_textile wall_decor_3d',
    'pillow': 'pillow throw_blanket bed_pillow', 'office_chair': 'office_chair', 'outdoor_daybed': 'outdoor_daybed', 'lamp': 'table_lamp floor_lamp desk_lamp',
    'nightstand': 'nightstand', 'bed': 'bed kids_bed', 'sectional': 'sectional', 'loveseat': 'loveseat', 'sofa': 'sofa', 'dining_chair': 'dining_chair bar_stool',
    'accent_chair': 'accent_chair recliner', 'dining_table': 'dining_table',
    'cabinet': 'tv_stand display_cabinet bookcase file_cabinet sideboard accent_cabinet chest_of_drawers wardrobe storage_chest',
    'small_table': 'coffee_table side_table ottoman bench', 'other': 'other'}.items()}
def v2_class(v2, leaf):
    if leaf in V2_MAP.get(v2, ()): return 'same'
    if resolve(BYKEY[leaf])['builder'] == 'skip': return 'v3 skips'         # v2 would have built a model of an accessory, a pad, a shade, a topper
    if v2 == 'other': return 'v3 adds a leaf'
    if leaf == 'other': return 'v3 queues'
    return 'DIFFERS'
```

```python harness
# ---- C. the golden runner (reads every ```golden fence of 4.5) and the reports ----
def parse_golden(text):
    """Line grammar: <title> [|| crumb > crumb] => <leaf> [; key=value ...]. `#` lines are comments."""
    out = []
    for blk in fences(text, 'golden'):
        for raw in blk.splitlines():
            s = raw.strip()
            if not s or s.startswith('#'): continue
            left, sep, right = s.partition(' => ')
            if not sep: err(f'golden: no " => " in {s!r}'); continue
            title, _, cr = left.partition(' || ')
            parts = [x.strip() for x in right.split(';')]
            exp = {'leaf': parts[0]}
            for kv in parts[1:]:
                k, _, v = kv.partition('=')
                exp[k.strip()] = v.strip()
            out.append((title.strip(), [x.strip() for x in cr.split(' > ')] if cr else [], exp))
    return out

def parse_dims(s):
    """`h90,w200,d95` in cm; an absent axis is simply missing."""
    return {m.group(1): float(m.group(2)) for m in re.finditer(r'([hwd])(\d+(?:\.\d+)?)', s or '')} or None

def check(title, crumbs, exp):
    got, v2, bad = route(title, crumbs, parse_dims(exp.get('dims'))), v2_route(title, crumbs), []
    def want(k, val):
        if k in exp and exp[k] != str(val): bad.append(f'{k}: expected {exp[k]!r}, got {val!r}')
    for k, val in (('leaf', got['leaf']), ('via', got['via']), ('b', got['builder']), ('q', got['quads']), ('host', got['host']), ('v2', v2), ('head', got['head']),
                   ('warn', got['warn'] or 'none'), ('set', got['set'][0] if got['set'] else 'none'), ('act', got['set'][1] if got['set'] else 'none'), ('low', int(got['low']))):
        want(k, val)
    for k, have in (('mods', got['mods']), ('post', got['post']), ('flags', got['flags'])):
        bad += [f'{k}: missing {x!r} (have {have})' for x in exp.get(k, '').split(',') if x and x not in have]
    bad += [f'nomods: {x!r} fired' for x in exp.get('nomods', '').split(',') if x and x in got['mods']]
    return got, v2, bad

PROBES = parse_golden(TEXT)
RES = [(t, c, e) + check(t, c, e) for t, c, e in PROBES]               # (title, crumbs, exp, got, v2, bad)
FAILS = [r for r in RES if r[5]]
COVERED = {r[2]['leaf'] for r in RES}
UNCOVERED = sorted(set(BYKEY) - COVERED)
UNKNOWN = sorted(COVERED - set(BYKEY))

print(f'schema: {len(CAT)} categories, {len(FAM)} families, {len(MODS)} modifiers, {len(CFG["dims_route"])} dims routes, {len(ERR)} errors')
for e in ERR: print('  ERR', e)
print(f'golden: {len(RES)} probes, {len(FAILS)} failed; leaves covered {len(set(BYKEY) & COVERED)}/{len(BYKEY)}')
for t, c, e, g, v2, bad in FAILS:
    print(f'  FAIL {t!r} -> {g["leaf"]} via {g["via"]} ({g["pat"]!r}); head {g["head"]!r}')
    for b in bad: print('       ', b)
if UNCOVERED: print('  leaves with no probe:', ' '.join(UNCOVERED))
if UNKNOWN: print('  probes name unknown leaves:', ' '.join(UNKNOWN))

if '--v2' in ARGV:
    print('\n| Title | v2 category | v3 leaf | Class |\n|---|---|---|---|')
    tally = {}
    for t, c, e, g, v2, bad in RES:
        k = v2_class(v2, g['leaf']); tally[k] = tally.get(k, 0) + 1
        if k != 'same': print(f'| {t} | `{v2}` | `{g["leaf"]}` | {k} |')
    print('\nclass counts:', tally)
if '--leaves' in ARGV:
    print('\n| Leaf | Family | Builder (alt) | Quads | Host | Scale | Postprocess | Flags | Set | Catalog |\n|---|---|---|---|---|---|---|---|---|---|')
    for c in CAT:
        r = resolve(c); cat = c.get('catalog'); cat = '/'.join([cat] if isinstance(cat, str) else cat or []) or ('NA' if c.get('na') else '-')
        print(f'| `{c["key"]}` | {c["family"]} | {r["builder"]}{" (" + r["alt"] + ")" if r.get("alt") else ""} | {r["quads"]} | {r["host"]} | {r["scale"]} | '
              f'{",".join(r.get("postprocess", [])) or "-"} | {",".join(r.get("flags", [])) or "-"} | {r["set"]}/{r.get("set_mixed", "skip")} | {cat} |')
if '--set' in ARGV:
    print()
    for t, c, e, g, v2, bad in RES:
        if g['set'] or g['marks']: print(f'{t!r}: marks {g["marks"]} -> {g["set"]}')
if '--heads' in ARGV:
    print()
    for t, c, e, g, v2, bad in RES: print(f'{t!r}: head {g["head"]!r} | full {g["head_full"]!r}')
if '--dead' in ARGV:
    dead = [(c['key'], f, i, p) for c in CAT for f in ('match', 'match_ctx', 'match_low', 'match_title') for i, p in enumerate(c.get(f, [])) if (c['key'], f, i) not in HITS]
    deadx = [(c['key'], 'exclude', i, p) for c in CAT for i, p in enumerate(c.get('exclude', [])) if (c['key'], 'exclude', i) not in EXC_HITS]
    print(f'\n{len(dead)} patterns and {len(deadx)} excludes never hit by any probe')
    for k, f, i, p in dead + deadx: print(f'  {k}.{f}[{i}] {p}')
sys.exit(1 if ERR or FAILS or UNCOVERED or UNKNOWN else 0)
```

### 4.6 Harness results and the pattern-liveness sampler (written after section 4, 2026-10-22)

This subsection was written after the rest of section 4 was frozen. Sections 3, 5, 6 and 7 follow it. It reports what the 4.7 harness printed when it ran against the 4.1 to 4.4b rules and the 4.5 probes in this same file, and it prints the pattern-liveness sampler that 4.5g refers to. Everything in the tables was produced by running code, not asserted from memory; the "Reading" columns are judgement and are marked as such.

#### 4.6a Run results

The harness was run from stdin with the bootstrap line quoted in 4.7 (`python -I -`, no file written, no network, no credit spent). The v2 `rules.toml` was read read-only for the `--v2` comparison.

```text
schema: 102 categories, 17 families, 16 modifiers, 15 dims routes, 0 errors
golden: 514 probes, 0 failed; leaves covered 102/102
```

What the schema line means: 100 leaves, `other` and the `x_accessory` control entry make 102 categories. The 17 families are the 15 content families of section 2 plus `control` and `misc` (`other`). The 16 modifiers and 15 `[[dims_route]]` tables are those of 4.4 and 4.4b. "0 errors" means every `to`, `route`, `delegate`, `host_leaves`, `thickness_leaves`, `dims_by_leaf` and `exclude` reference resolves, every regex compiles, every vocabulary word is declared in `[vocab]`, and `other` is the last `[[category]]`. "Leaves covered 102/102" means no category lacks a probe.

The `--v2` run compares each probe title with the v2 first-match router (`rules.py` `category()` over `rules.toml`, 18 categories). Of the 514 probes, 309 differ from "same as v2" in some way:

| v2 comparison class | Probes | Meaning |
|---|---|---|
| same | 205 | v3 gives the leaf that v2's category name stands for (a sofa title is `sofa` in both) |
| v3 adds a leaf | 197 | v2 said `other`; v3 names a leaf. Mostly appliances, planters, bedding, mattresses, bookcases, baskets and potted plants (`small_appliance` 11, `planter` 8, `bedding_set` 7, `mattress` 6, `bookcase` 6, `basket_bin` 6, `plant_potted` 6 are the largest) |
| DIFFERS | 94 | v2 and v3 disagree about a title v2 did classify. Every one is listed in section 3 with its cause |
| v3 skips | 18 | v3 builds nothing and queues the job with a reason: `x_accessory` 12 (bed skirt, bed tray, rug pad, slipcover, lamp shade, mattress topper, table runner, curtain rod, cushion cover, TV wall mount, Euro sham, placemat set), `bath_fixture` 4 (bathtub, pedestal sink, toilet, shower curtain), `bbq_grill` 2 (charcoal and gas grill) |

Reading (judgement): the 94 DIFFERS rows are the value of the head-noun router. They are not regressions; each is a title where v2's first substring match picked the wrong word ("Art Deco Velvet Accent Chair" is not art). Section 3 turns them into a collision table.

#### 4.6b Dead patterns and excludes (the `--dead` report)

A pattern is "dead" here when no probe in this file hit it. That does not prove the pattern can never match: it proves nobody has pinned its behaviour. The report is a to-do list for the golden probes, not a bug list.

| Field | Patterns never hit by any probe |
|---|---|
| `match` | 127 |
| `match_low` | 17 |
| `match_ctx` | 4 |
| `match_title` | 1 |
| total patterns | 149 |
| `exclude` entries | 41 |

The leaves with the most unprobed patterns are `bookcase` (8), `crib` (7), `pet_furniture` (6), `hammock_swing` (6) and `vase` (6), then `bed`, `display_cabinet`, `file_cabinet`, `flush_mount`, `art_set`, `wall_decor_3d` and `book_stack` with 4 each. Most of these are synonym tails of long alternations (a regional word, a plural, a rare type) that the author added from the vocabulary tables of 1.4 rather than from a real listing.

Policy for the rules author (adopted for v3, not yet applied to the file):

1. A dead `match` that is a regional word (AU "cot", UK "wardrobe", AU "tallboy") gets one probe, because regional words are exactly what a US-trained author forgets.
2. A dead `exclude` gets a probe that would have gone to the wrong leaf without it. If the author cannot write one, delete the exclude: an exclude with no failing case is dead weight and slows the reading of every leaf.
3. A dead `match_low` is acceptable until the first 200 real jobs have run; `match_low` is the fallback pass and most titles should not reach it.
4. CI prints the dead list on every run and fails only when the count grows. Writing the probe is the fix; the harness already supports it (`--dead` flag, 4.7).

The full list of 190 lines (149 patterns plus 41 excludes) is not reproduced here; rerun `--dead` to regenerate it.

#### 4.6c The pattern-liveness sampler

The sampler answers a different question from the golden probes: not "does this title go where I expect" but "does every pattern of a leaf still win the title it was written for". For each `match` and `match_low` regex of every leaf except `other`, it expands the regex into sample strings (literals, character classes, alternations and bounded repeats, using Python's `re._parser`), keeps a sample only if the regex still matches it, runs the full `route()` on it, and reports a disagreement when the routed leaf is not the pattern's owner. A disagreement is a clue, never a verdict. The code is printed in full (a plain `python` fence: the harness does not extract it).

```python
import re, re._parser as sp                      # run after the 4.7 bootstrap has defined CAT and route()
CAP = 12                                         # samples kept per pattern
def gen(p):                                      # one list of strings per parsed regex
    out = ['']
    for op, av in p:
        n = str(op)
        if n == 'LITERAL': opts = [chr(av)]
        elif n == 'IN':                          # first three members of a class; digits become '3'
            ch = []
            for o, a in av:
                if str(o) == 'LITERAL': ch.append(chr(a))
                elif str(o) == 'RANGE': ch.append(chr(a[0]))
                elif str(o) == 'CATEGORY': ch.append('3' if 'DIGIT' in str(a) else 'x')
            opts = ch[:3] or ['x']
        elif n == 'SUBPATTERN': opts = gen(av[3])
        elif n == 'BRANCH': opts = [s for b in av[1] for s in gen(b)]
        elif n in ('MAX_REPEAT', 'MIN_REPEAT'):
            lo, hi, sub = av; so = gen(sub); opts = []
            if lo == 0: opts.append('')
            if hi >= 1: opts += so
            if hi >= 2 and lo <= 2: opts += [a + b for a in so[:2] for b in so[:2]]
        elif n in ('ANY', 'NOT_LITERAL', 'CATEGORY'): opts = ['x']
        else: opts = ['']                        # AT, ASSERT, GROUPREF: contribute nothing
        out = [a + b for a in out for b in opts][:400]
    return out
def samples(pat):
    try: s = gen(sp.parse(pat))
    except Exception: return []
    s = [re.sub(r'\s+', ' ', x).strip() for x in s]
    return [x for x in dict.fromkeys(s) if x and re.search(pat, x)][:CAP]
dis = []
for c in CAT[:-1]:                               # every category but the last, `other`
    for fld in ('match', 'match_low'):
        for i, p in enumerate(c.get(fld, [])):
            for s in samples(p):
                g = route(s)
                if g['leaf'] != c['key']: dis.append((c['key'], fld, i, s, g['leaf'], g['via']))
```

Results on the final rules of this file (2026-10-22), by the number of samples kept per pattern:

| CAP | Samples | Disagree | What the extra samples add |
|---|---|---|---|
| 12 | 2,591 | 3 | plus `standing_desk` read as `other` for "desk sit - stand" |
| 40 | 5,969 | 12 | plus `kitchen_island` against `bench` and `accent_cabinet`; mostly nonsense joins made by the generator ("islands bench") |
| 400 | 23,304 | 145 | exhaustive on short patterns; dominated by 73 `small_appliance` strings and 22 `decor_small` strings |

At CAP 400 the 145 disagreements group as follows.

| Owner leaf | Won by | Count | Example | Reading (judgement) |
|---|---|---|---|---|
| small_appliance | appliance_large | 73 | "microwave oven" | Intended overlap: a bare "microwave oven" is a box in the `appliance_large` leaf; "countertop microwave oven" is `small_appliance` with the `tabletop` modifier (host `su`). The `small_appliance` alternation lists words that the larger leaf also owns; harmless but misleading |
| decor_small | bowl_tray | 22 | "desktop tray" | `desktop` fires the `tabletop` modifier, and a tray is a `bowl_tray` (lathe, host `su`). Intended |
| bookcase | display_cabinet | 14 | "display unit" | Ambiguous in the real world: a display unit with glass doors is a `display_cabinet`, an open one is a bookcase. Open item for the rules author |
| stems_florals | decor_small | 14 | "faux centerpiece" | "centerpiece" is a `decor_small` head; a faux-flower centerpiece should be `stems_florals`. Open item |
| kitchen_island | bench | 6 | "islands bench" | Generator artifact (a join of two alternation branches that no title contains) |
| kitchen_island | accent_cabinet | 6 | similar join | Generator artifact |
| standing_desk | other | 2 | "desk sit - stand" | Real but rare. `head_cut` cuts at a spaced hyphen (" - "), so the title is cut before "stand". "BEKANT, Desk sit/stand" (IKEA Form A) is handled; the spaced-hyphen spelling is not. Open item: a `strip` rule for "sit - stand" ahead of `head_cut`, or accept the queue |
| desk | game_table | 2 | "gaming table" | Intended: a gaming table is `game_table` (family pet_fitness: board-game and pool tables). A "gaming desk" stays a `desk` |
| basket_bin | storage_chest | 2 | "toy chest" | Intended: a toy chest is a chest |
| bedding_set | mattress | 2 | "bed in a box" | The routing is right (a bed-in-a-box is a mattress), but the `bedding_set` alternation still lists a pattern that can never win that string. Open item: delete or narrow it |
| small_appliance | bbq_grill | 2 | "pizza oven" | Intended: a pizza oven is an outdoor oven (`bbq_grill`, skipped) |

Only four of the eleven groups are actionable (display unit, faux centerpiece, the spaced hyphen, the `bed in a box` pattern), each a one-line change in the 4.3 leaf it names. None was made here because this appendix may not edit the rules; they are open items for the rules author.

Limits of the sampler, stated so nobody over-reads it:

- It does not sample lookarounds, back-references or the `$` anchor, so a pattern that depends on them contributes fewer strings.
- It checks `match` and `match_low` only; `match_ctx`, `match_title` and `exclude` are covered by the golden probes.
- It knows no real titles: a clean run says the author's patterns do not shadow each other, nothing about vocabulary the author never wrote down. Only real feeds test that (the first 200 pilot jobs, A4).
- Historical figure: 4.5g quotes "133 strings out of 5,794" from an earlier sampler run, before the 4.5g fixes. That generator was not kept, so the figure cannot be reproduced; treat the 133 as the pre-fix state and the 12 disagreements at CAP 40 as the comparable post-fix state (an **[ESTIMATE]**, because the sample counts differ, 5,794 against 5,969). The table above is measured.

---

## 3. Mapping the 18 v2 categories onto the v3 leaves, and the verified collisions

This section was written after section 4 and 4.6; it relies on the `V2_MAP`, `v2_route` and `v2_class` functions of the 4.7 harness and the `v2=` keys of the 4.5 probes. v2's router is `rules.py` `category()` over `rules.toml`: the first category (in file order) whose `match` list hits the title or breadcrumb wins, `exclude` can veto one, and `other` is the fallback. The 18 categories are rug, mirror, art, pillow, office_chair, outdoor_daybed, lamp, nightstand, bed, sectional, loveseat, sofa, dining_chair, accent_chair, dining_table, cabinet, small_table, other. v2 builds `rug` and `art` procedurally and every other category on Tripo P2 (`[modes]` p2, up to 25,000 quads; read-only `rules.toml`).

### 3.1 How to read the tables

- "Same" means the v3 leaf is one of the leaves `V2_MAP` assigns to the v2 category (one v2 category usually becomes several leaves).
- "Collision" means a title that v2 routes to category X and v3 to a leaf outside `V2_MAP[X]`, machine-verified by a probe with `v2=X` or a `--v2` row; the 94 DIFFERS rows of 4.6a are all of them.
- Causes (Section 5 stages): **head** (the head noun decides), **set**, **mod** (a modifier changed route or host), **dims** (a `[[dims_route]]` fired), **crumb**, **accessory** (stage 1 control), **ctx** (outdoor gating).
- The per-category counts add to 94: art 5, sofa 11, lamp 2, pillow 5, outdoor_daybed 3, bed 15, dining_chair 6, cabinet 9, dining_table 11, sectional 2, small_table 3, accent_chair 14, mirror 4, loveseat 2, nightstand 2. `rug` and `office_chair` have none in the probe set.

### 3.2 The mapping

| v2 category | v2 first-match words (summary, from the v2 `match` lists) | v3 leaves it splits into (`V2_MAP`) | Builder change | Net |
|---|---|---|---|---|
| `rug` | rug, runner, mat, carpet (`RUG_RE`) | `rug_rect`, `rug_round`, `rug_shaped`, `mat_small` | procedural rug builder kept; `mat_small` (doormat, bath mat) is a new leaf | split, plus an accessory guard: "Rug Pad 8x10" is `x_accessory` (v2 built a rug from it) |
| `mirror` | mirror | `mirror_wall`, `mirror_floor` | both `hybrid`; the floor mirror gets a leaning tilt | split; "mirror" counts only as the head noun (4.5a) |
| `art` | art, print, canvas, framed, poster, tapestry | `art_framed`, `art_set`, `wall_textile`, `wall_decor_3d` | procedural art builder kept for `art_framed` and `art_set`; `wall_textile` is a drape builder; `wall_decor_3d` is Tripo | split; v2's "art" also swallowed furniture (3.3) |
| `pillow` | pillow, cushion, throw, blanket | `pillow`, `throw_blanket`, `bed_pillow` | cushion builder for pillows, drape builder for the throw | split; a king-size blanket re-routes to `bedding_set` by dims |
| `office_chair` | office chair, task chair, desk chair, gaming chair | `office_chair` | Tripo | one to one |
| `outdoor_daybed` | outdoor daybed, patio daybed | `outdoor_daybed` | Tripo | one to one; an indoor daybed is the new `daybed` leaf (seating family) |
| `lamp` | lamp, light | `table_lamp`, `floor_lamp`, `desk_lamp` | Tripo with the lamp rules of 2.5 | split by head noun and by the `h >= 115` dims route; a wall sconce is `wall_sconce`, a lamp shade is `x_accessory` |
| `nightstand` | nightstand, bedside table, night table | `nightstand` | Tripo | one to one |
| `bed` | bed, bedframe, headboard | `bed`, `kids_bed` | Tripo | split; a headboard is now `headboard`, and "bed" no longer matches a dog bed, a garden bed or bed linen |
| `sectional` | sectional, L-shaped, corner | `sectional` | Tripo | one to one; "L-Shaped Desk" is a `desk`; a module title re-routes through the `module` modifier |
| `loveseat` | loveseat, love seat, settee | `loveseat` | Tripo | one to one; "2 seater sofa" is a `loveseat` by name |
| `sofa` | sofa, couch | `sofa` | Tripo | one to one; the sofa words are head-noun-only, so "Sofa Table" is a `console_table` |
| `dining_chair` | dining chair, stool, bar stool, side chair | `dining_chair`, `bar_stool` | Tripo | split; foot stools and step stools leave for `ottoman` |
| `accent_chair` | accent chair, armchair, chair | `accent_chair`, `recliner` | Tripo | split; "chair" alone was a catch-all in v2 and now needs a type |
| `dining_table` | dining table, table, desk | `dining_table` | Tripo | one to one; desks leave for the tables family (`desk`, `standing_desk`, `vanity_table`) |
| `cabinet` | cabinet, dresser, bookcase, shelf, tv stand, wardrobe, chest, credenza | `tv_stand`, `display_cabinet`, `bookcase`, `file_cabinet`, `sideboard`, `accent_cabinet`, `chest_of_drawers`, `wardrobe`, `storage_chest` | Tripo (`display_cabinet` is hybrid with the glass modifier) | nine-way split; the biggest gain in routing precision |
| `small_table` | coffee table, side table, end table, ottoman, bench | `coffee_table`, `side_table`, `ottoman`, `bench` | Tripo | four-way split |
| `other` | (everything else) | `other` | none | in v3 a hit is a queue item with three candidate leaves (Section 5), no longer a silent catch-all |

The "first-match words" column summarises the v2 definitions; the exact lists are in v2 `rules.toml` (**[UNVERIFIED]** as a complete list: the collision rows of 3.3 are the verified part).

The 17 v2 categories other than `other` cover 42 of the 100 v3 leaves (4+2+4+3+1+1+3+1+2+1+1+1+2+2+1+9+4). The other 58 have no v2 ancestor: every title reaching them was an `other` in v2 (the 197 "v3 adds a leaf" probes of 4.6a, led by `small_appliance`, `planter`, `bedding_set`, `mattress`, `bookcase`, `basket_bin`, `plant_potted`).

### 3.3 Verified collisions, by v2 category

Every row below is a probe of 4.5 or a `--v2` row of 4.6a; the harness checks the v3 column on every run.

**v2 `art` (5).** Furniture whose name contains "art", "print", "canvas" or "framed".

| Title | v3 leaf | Cause |
|---|---|---|
| Art Deco Velvet Accent Chair | `accent_chair` | head: "art" is a style word before the head noun |
| Print Fabric Accent Chair | `accent_chair` | head |
| Canvas Sling Chair | `accent_chair` | head |
| Art Deco Sideboard | `sideboard` | head |
| Oak Framed Sofa Table | `console_table` | head |

**v2 `sofa` (11).** The word "sofa" appears in many other product names.

| Title | v3 leaf | Cause |
|---|---|---|
| Sofa Table | `console_table` | head: the pattern ends in "table" |
| Modular Sofa, Corner Sofa, Corner Sofa Grey Fabric, Modular Sofa Corner Module | `sectional` | head: "corner" and "modular" name the sectional form |
| GRONLID, Corner sofa, 4-seat, with chaise longue/Ljungen light grey (IKEA Form A) | `sectional` | head after the IKEA strip (4.7 `ikea_strip`) |
| Mathers Grey Brown Vegan Faux Leather Right Arm Facing Sofa Chaise | `sectional` | head: "sofa chaise" with LAF/RAF |
| 2 Seater Sofa | `loveseat` | head: "2 seater" |
| Sofa (dims w150, d85) | `loveseat` | dims: `sofa` to `loveseat` when lmax <= 170 (confidence low) |
| Garden Sofa Set | `outdoor_sofa` | ctx: "garden" opens the outdoor stage; the set is mixed in kind |
| Capri (breadcrumb Outdoor > Patio Furniture > Outdoor Sofas) | `outdoor_sofa` | crumb: a name-only title is routed from its breadcrumb at low confidence |

**v2 `lamp` (2).**

| Title | v3 leaf | Cause |
|---|---|---|
| Lamp Table | `side_table` | head |
| Console Table with Lamp | `console_table` | head: `head_cut` at "with" removes the accessory |

Not a DIFFERS row but the same kind of mistake: "Lamp Shade" is `x_accessory`, a v3 skip.

**v2 `pillow` (5).**

| Title | v3 leaf | Cause |
|---|---|---|
| Cedar Blanket Chest | `storage_chest` | head |
| Blanket Ladder | `bookcase` | head, plus the `ladder` modifier (adds a tilt) |
| Throw Blanket | `bedding_set` | the probe carries a bedding-sized dims value, so the dims route (lmax >= 200 and lmin >= 140) moves `throw_blanket` to `bedding_set` |
| Sofa with Throw Pillows | `sofa` | `head_cut` at "with" |
| Accent Chair with Pillow | `accent_chair` | `head_cut` at "with" |

**v2 `outdoor_daybed` (3).** v2 listed "daybed" under the outdoor category only.

| Title | v3 leaf | Cause |
|---|---|---|
| Daybed, Twin Daybed, Twin Daybed with Trundle | `daybed` | the indoor `daybed` leaf exists; the `outdoor` modifier (patio, garden, ...) selects `outdoor_daybed` |

**v2 `bed` (15).** "Bed" is a head noun only when it is the last word of the head.

| Title | v3 leaf | Cause |
|---|---|---|
| Upholstered Headboard, Queen Headboard Only | `headboard` | head: a headboard is not a bed |
| Dog Bed, Orthopedic Dog Bed, Calming Dog Bed | `pet_bed` | head |
| Raised Garden Bed, Garden Bed, Vegetable Garden Bed | `planter` | head (a garden bed is a planting box) |
| Bed in a Bag Queen, Bed Linen | `bedding_set` | head |
| Bed in a Box | `mattress` | head: a bed-in-a-box is a mattress |
| Futon Bed Frame | `sofa` | mod: the `sleeper` modifier routes bed to sofa (a futon frame is a sofa frame) |
| FRIHETEN Corner sofa-bed with storage, Skiftebo dark grey | `sectional` | mod: `sleeper`, plus head ("corner sofa-bed") |
| Day Bed | `daybed` | head |
| Headboard Bench | `bench` | head: the last noun |
| Bed Skirt, Bed Tray with Legs | `x_accessory` | accessory (v3 skips) |

**v2 `dining_chair` (6).**

| Title | v3 leaf | Cause |
|---|---|---|
| Foot Stool, Step Stool, Stool, Vanity Stool | `ottoman` | head: only "bar stool" and "counter stool" stay with `bar_stool`; a bare "Stool" is a `bar_stool` at 75 cm tall (pass 2) and an `ottoman` at 45 cm (the dims route fires at h <= 55) |
| Patio Dining Chair | `outdoor_chair` | ctx: the outdoor modifier |
| Dressing Table with Stool | `vanity_table` | `head_cut` at "with" |

**v2 `cabinet` (9).**

| Title | v3 leaf | Cause |
|---|---|---|
| Console Table, Sienna Console Table, Rosalind Wheeler Henshaw 48'' Console Table (Wayfair brand prefix) | `console_table` | head (and the brand strip for the Wayfair form) |
| Bathroom Vanity Cabinet, Sink Cabinet, Vanity Cabinet | `bath_vanity` | head: the bathroom word decides |
| Bedside Cabinet | `nightstand` | head: UK/AU word |
| Floating Cabinet | `wall_shelf` | head; the `floating` modifier sets host `wl` only for the leaves in its `host_leaves` list |
| Island Cabinet | `kitchen_island` | head |

**v2 `dining_table` (11).** v2 treated every "table" and "desk" as a dining table.

| Title | v3 leaf | Cause |
|---|---|---|
| Writing Desk, Gaming Desk, Computer Desk with Hutch, LINNMON / ALEX, Desk, white, 120x60 cm (IKEA Form A) | `desk` | head |
| Standing Desk, Electric Standing Desk, Height Adjustable Desk, BEKANT, Desk sit/stand, white, 160x80 cm | `standing_desk` | mod: `standing` routes desk to standing_desk (build_state lowest) |
| Outdoor Dining Table, Terrace Outdoor Dining Table | `outdoor_table` | ctx |
| Makeup Desk | `vanity_table` | mod: `tabletop` (makeup), plus head |

**v2 `sectional` (2).**

| Title | v3 leaf | Cause |
|---|---|---|
| L-Shaped Desk | `desk` | head: "L-shaped" is a shape word, the noun is "desk" |
| Patio Sectional Sofa | `outdoor_sofa` | ctx |

Also a v3 skip: "Slipcover for Sectional Sofa" is cut at "for" and becomes `x_accessory`.

**v2 `small_table` (3).**

| Title | v3 leaf | Cause |
|---|---|---|
| Entryway Hall Tree with Bench and Storage | `hall_tree` | `head_cut` at "with": the head is "entryway hall tree" |
| BESTA, TV bench, black-brown, 120x42x38 cm (IKEA Form A) | `tv_stand` | head after the IKEA strip: a "TV bench" is a low media unit |
| Kitchen Island Bench | `kitchen_island` | head (AU "bench" means worktop) |

**v2 `accent_chair` (14).** "Chair" was a catch-all, so any title ending in "chair" landed here.

| Title | v3 leaf | Cause |
|---|---|---|
| Kids Table and Chairs Set, Kids Table and Chair Set, High Chair | `kids_table_set` | set (mixed kind) plus the `kids` modifier; the high chair belongs to the same kids leaf |
| Dining Table and 4 Chairs, Dining Set Table and 4 Chairs | `dining_table` | set: mixed kind, action `split` (the table is the piece that is built; the chairs are a separate job) |
| Adirondack Chair, Set of 2 Outdoor Chairs, Outdoor Rocking Chair | `outdoor_chair` | head and ctx; the `rocker` modifier adds flag Th |
| Bean Bag Chair | `bean_bag` | head (cushion builder) |
| Parsons Chair, Folding Chair | `dining_chair` | head |
| Armless Chair Module | `sectional` | mod: `module` (build one module) |
| Hammock Chair Stand | `hammock_swing` | head |
| Zero Gravity Chair | `outdoor_lounger` | head (an indoor "zero gravity massage chair" is a `recliner`, 4.5g) |

**v2 `mirror` (4), `loveseat` (2) and `nightstand` (2).**

| Title | v2 | v3 leaf | Cause |
|---|---|---|---|
| Makeup Vanity Table with Mirror, Vanity Desk with Mirror | mirror | `vanity_table` | `head_cut` at "with" |
| Dresser with Mirror | mirror | `chest_of_drawers` | `head_cut` at "with" |
| Bathroom Vanity with Mirror | mirror | `bath_vanity` | `head_cut` at "with" |
| Living Room Set Sofa and Loveseat | loveseat | `sofa` | set: mixed kind, the first piece; the action is `skip`, so the job is queued, not built |
| Loveseat Recliner | loveseat | `recliner` | head: the last noun |
| Bedroom Set Queen Bed Nightstand Dresser | nightstand | `chest_of_drawers` | set: mixed; an unseparated list takes its last noun, and `set_mixed = skip` queues the job. A known weak spot |
| Bed with Nightstands | nightstand | `bed` | `head_cut` at "with" |

### 3.4 What the collisions teach the rules (five patterns)

1. **Substring matching is wrong for nouns that modify.** Many of the 94 collisions are one mistake: a v2 type word is a modifier in the title ("sofa table", "bed in a bag", "art deco chair"). The head-noun rule (4.1) fixes all of them and is the largest single gain.
2. **A trailing "with X" is an accessory.** About a dozen collisions are "X with Y" where v2 matched Y. `head_cut` removes the clause; "Dresser with Mirror" loses the mirror, correct for the 3D model, wrong for a shelf listing.
3. **Outdoor and kids are contexts.** `outdoor_*` and `kids_*` leaves come through the `outdoor` and `kids` modifiers (4.4), so a patio sectional no longer lands on `sectional`.
4. **Sets are not pieces.** v3 detects the set and splits it, takes the first piece or skips it (5.3).
5. **The accessory guard.** v2 built a lamp from a lamp shade, a rug from a rug pad, a bed from a bed skirt; `x_accessory` stops such titles reaching a builder.

### 3.5 Migration notes for already-built v2 assets

- Nothing is rebuilt. A v2 asset keeps its model; only its **category** is remapped through the v3 router, offline, in a dry run that prints (v2 category, v3 leaf, changed or not). The collision list predicts which rows change; a human confirms them before any write.
- v2's quad budget (up to 25,000 for every category) is not the v3 default (2,500, `face_limit = 2 x quads`). Existing models stay; new jobs use per-leaf quads. **[UNVERIFIED]** whether the load cost of the old high-quad models justifies re-decimation; A4 owns throughput.
- The `Catalog` column of 2.1 to 2.14 names each leaf's DB category. About 30 DB categories are not in `ALLOWED_CATEGORIES` (5.5); a leaf marked `NA` cannot be filed until the list is extended, so the dry run reports it and writes nothing.

---

## 5. The routing algorithm, the output record, dimension rules and app gates

This section is the reference for the v3 router. Everything in 5.1 to 5.3 describes what the harness of 4.7 executes (`route(title, crumbs, dims)`), so a statement can be re-checked by running a title through it. What the harness does not yet implement (numeric confidence, the URL-slug pass, label-aware dimension parsing) is marked **[PROPOSAL]** or **[ESTIMATE]**. 5.4 holds the dimension rules and 5.5 the app gates and known gaps.

### 5.1 The routing steps, in order

One call routes one product. The inputs are the product title (as published), the breadcrumb (a list of category names, outermost first) and optionally the listed dimensions in cm. The output is the record in 5.3.

| # | Step | What it does | Config key | Why |
|---|---|---|---|---|
| 1 | IKEA strip | On the ORIGINAL-case title. Form A `BEKANT, Desk sit/stand, white, 160x80 cm`: the second comma segment becomes the title, but only when the first segment is an all-caps name of 1 to 3 words and the second contains a lower-case letter. Form B `KALLAX Shelf unit`: the leading all-caps word is dropped. An acronym guard (LED, USB, HDMI, LCD, MDF, PVC, LAF, RAF, LHF, RHF, XXL, KING, TWIN, FULL, QUEEN) stops an acronym being taken as a name | `[detect] ikea_style` | IKEA puts the noun in the second segment; without this the head would be the invented name (`kivik`, `bekant`) and match nothing |
| 2 | Fold | Remove (TM) (R) (C); remove vulgar fractions; turn `x` and dashes into plain separators; `60"` becomes `60 in` and `8'` becomes `8 ft`; ASCII-fold accents; lower-case; drop apostrophes | `fold_ascii` | One alphabet for the patterns; `Sand & Stable Ethan 24'' Round` must not be derailed by a stray quote |
| 3 | Brand strip | Once, anchored at the start: remove a brand whose own name contains a head-cut separator (`sand & stable`, `joss & main`, `crate & barrel`, `better homes & gardens`, `hearth & hand`, `stone & beam`, `room & board`, `bed bath & beyond`, `mack & milo`, `isabelle & max`, `ophelia & co`, `viv + rae`, `lulu & georgia`, `drew & jonathan`) | `brand_strip` | Without it the head cut at `&` leaves the head `sand` |
| 4 | Head cut loop | Cut at the first `head_cut` separator (`with`, `w/`, `including`, `featuring`, `by`, `for`, `from`, `plus`, `and`, `&`, `+`, comma, colon, bracket, semicolon, pipe, spaced hyphen). Then repeat, up to 8 times, until nothing changes: strip a trailing dimension tail, a size word (twin, king, ...), an `in <finish>` tail, trailing colour or material words (`trail_finish`), a multi-use count (`3 in 1`), `only`, and a count of doors, drawers, shelves or seats. At least one word always survives | `head_cut`, `strip_trailing_dims`, `tail_strip`, `trail_finish` | The noun phrase is at the END of the head, so every pattern is anchored with `$` |
| 5 | Strip sets | Remove trailing set words and `set of N`, unless the head is a `keep_suite` head (`chaise suite`). The removed words are recorded as marks (the strip), and the loop of step 4 runs again on what is left | `[[modifier]] set`, `delegate = set_detect` | A set is a count and an action, not a different noun |
| 6 | Fire modifiers | The 16 modifiers are evaluated, each on its own scope: the head (`sleeper`, `tabletop`, `floating`, `module`, `ladder`, `rocker`, `bar_height`, `standing`, `extension`), the whole title (`easel`, `unframed`, `glass`, `mesh`), the context (title plus the last two crumbs: `outdoor`, `kids`), or the strip (`set`) | `[[modifier]]` | A modifier never picks a leaf; it changes the host, the flags, the post-process or the dimension range of the leaf that wins |
| 7 | Pass 1: `match` | Forms tried in order: the head, then the full head (before the loop cut it) if different. For each form, every leaf in FILE order except `other`: `match`; then `match_ctx` (only if the leaf's `ctx` modifier fired and the leaf has a gate); then `match_title` on the first form only. A leaf's `exclude` is tested on the head only and vetoes the leaf | `match`, `match_ctx`, `match_title`, `exclude` | File order is the only tie-break between leaves (5.2) |
| 8 | Pass 2: `match_low` | The same scan with the weaker patterns (a bare `mats?$`, a bare `pillows?$`, and so on). A hit is a low-confidence hit | `match_low` | Cheap recall; the VLM check or a human confirms |
| 9 | Pass 3: breadcrumb | Take the last two crumbs, most specific first; split each on `&`, `and`, `,` and `/`; run passes 1 and 2 on each segment (no `match_title`). A hit is low confidence | `[detect] breadcrumb_depth = 2` | A name-only title (`Ravenna`) can only be routed from the crumbs |
| 10 | Pass 4: `other` | Nothing matched. The leaf is `other`, the builder is tripo at 2,500 quads, `on_hit = queue` | `[[category]] key = "other"` | Default-deny: unknown goes to a human, never to the generator |
| 11 | Post-route | In this order: (a) the modifier `route` (sleeper bed becomes sofa; standing desk becomes `standing_desk`); (b) the set kind and action (4.4a) and the set route (`art_framed` becomes `art_set` for a gallery set); (c) the `dims_route` hops (up to 3 hops; a row may carry `only = "low"` or a `title_not` guard; a hop marked `confidence = "low"` makes the result low); (d) attribute resolution; (e) the host-only `dims_route` rows; (f) the `warn = units` check | `[[dims_route]]`, `[defaults]` | Dimensions can only correct a leaf the text left uncertain; they never override a confident name |
| 12 | Attribute resolution | Host (a modifier `host` if the leaf is in its `host_leaves`; else the leaf's, the family's, the default); flags (family, leaf, modifier `add_flags`); post-process (the leaf's list, else the family's, plus modifier additions); `dims_scale` (kids 0.4 to 1.0); `dims_by_leaf`; `thickness_cm` | `[defaults]`, `[family.*]` | A leaf's list REPLACES its family's list (4.1), so every record is the full answer, not a diff |

Two facts about the table that are easy to get wrong:

1. The harness matches on the HEAD, not the title. `Haven Sofa (60"-108")` has the head `haven sofa`; `Ashaway Grey Extendable 66-84 Inch Rectangular Dining Table` keeps its whole title as the head because nothing in it is a separator. `match_title` (four patterns in the whole file) exists for the rare leaves whose cue lives outside the head phrase.
2. `exclude` is tested on the head only. A word elsewhere in the title cannot veto a leaf; a modifier or `match_title` does that job.

**The head-final noun rule.** Because nearly every pattern ends in `$`, the LAST noun of the head decides. `Kilim Pillow Cover 20 x 20` has the head `kilim pillow cover`; the rug pattern `kilims?$` does not match it (the head ends in `cover`), the pillow pattern `(pillow|cushion) covers?$` does. This is the mechanism that routes the over-matching words of the app's `RUG_RE` (see 5.5: "runner", "mat", "kilim") away from the rug leaves. It is also its weakness: a title that puts the leaf word first and a colourway noun last (`Pillow Cover Kilim`, see the gaps in 5.2) matches the wrong leaf.

**The stage order, as it appears in the file.** The leaf order IS the algorithm, because step 7 takes the first leaf that matches:

| Stage | Contents | Why it comes here |
|---|---|---|
| 1 Control | `x_accessory`: not a 3D product (cover, topper, pad, skirt, runner, rod, shade, mount, part, swatch, card), so a table runner, a rug pad or a mattress topper | Must win against `rug_*`, `mattress` and the tabletop leaves that would otherwise take the same words |
| 2a Compound heads | Leaves whose last word is also another leaf's head noun (bed, table, chair, tree, bench): `hall_tree`, `game_table`, `fitness_machine`, `pet_bed`, `pet_furniture`, `kids_bed`, `crib`, `changing_table`, `kids_table_set` | A pet bed is not a bed and a kids table is not a table; these must win before the family leaves |
| 2b Outdoor | `fire_pit`, `hammock_swing`, `patio_umbrella`, `bbq_grill`, `outdoor_lounger`, `outdoor_daybed`, `outdoor_sofa`, `outdoor_chair`, `outdoor_table`. Each has strong patterns for the explicit words (`patio umbrella`) and a `match_ctx` list for the bare noun, which fires only when the `outdoor` modifier fired (`hammock_swing` has none) | An outdoor sofa must never reach `sofa`, and a bare `sofa` must never reach `outdoor_sofa` |
| 3 Families | The remaining leaves of the content families, in the family order of 4.1 (seating, tables, bedroom, storage, lighting, rugs, wall decor, tabletop, plants, textiles, then the rest), as the file lists them | The ordinary single-noun leaves |
| Last | `other` | Matches everything; must remain the last `[[category]]` |

**The traps of section 1.5 as parser rules.** Each trap is handled by exactly one step or rule, so a reviewer can find it:

| Trap (1.5) | Handled by | Rule |
|---|---|---|
| Lamps: listed W x D is the base | 5.4 axis table | Width and depth are the larger of the shade and the base; when only the base is listed the record should carry a warning **[PROPOSAL]** |
| Plants: height with or without the pot | 5.4 axis table | Height is total height including the pot; a "plant only" height is combined with the pot height in the `plant_pot_combine` step |
| Wall art: W x H ambiguity; framed against art size | 5.4 axis table | Reconcile with the image aspect; take the FRAMED size |
| TVs: the diagonal | 5.4 and `[dims_parse] tv` | W = diag x 0.8716, H = diag x 0.4903 |
| Stools: seat height | `dims_route` `bar_stool` to `ottoman`, `bar_height` modifier | Compare the seat height, not the overall height |
| LAF / RAF | `module` modifier, `laf_raf` post-process | Facing is judged standing in front of the piece; mirror the model if the photo disagrees |
| Rugs and mattresses by size name | 5.4 locale table | The locale comes from the retailer, never from the word alone |

### 5.2 Confidence, tie-breaks and the fallback

**Confidence.** The harness reports a boolean `low` and the way the leaf was found (`via`). The `[detect]` block fixes `vlm_min_confidence = 0.80` and `queue_below = 0.80`, so the rest of the pipeline needs a number. The mapping below is a **[PROPOSAL]**; the values are **[ESTIMATE]** and are to be calibrated on the first 200 jobs. The harness guarantees the ordering, not the numbers.

| `via` | Meaning | Proposed confidence [ESTIMATE] | Goes to |
|---|---|---|---|
| `match` (pass 1, head) | A strong pattern matched the noun phrase | 0.95 | Accept the leaf; the Section 6 cheap tests still run |
| `ctx` | A strong pattern matched because a context modifier fired (outdoor, kids) | 0.95 | Accept |
| `title` | `match_title` fired on the whole title | 0.90 | Accept |
| `low` (pass 2) | `match_low` only | 0.70 | Below 0.80: the VLM leaf question of Section 6 |
| `crumb` | Only the breadcrumb matched | 0.65 | Below 0.80: the VLM leaf question |
| any hit changed by a low `dims_route` | The size, not the name, chose the leaf | capped at 0.75 | Below 0.80: the VLM leaf question |
| `other` | Nothing matched | 0.00 | Human queue with the top-3 candidates |

A `set` result adds a separate flag, not a lower confidence: a mixed set is certain to be a set, and the action (`skip` by default) is what matters.

**Tie-breaks.** Several leaves can match the same head. From first to last:

1. **Control first.** An `x_accessory` match ends the search (builder `skip`).
2. **File order.** The first leaf whose `match` fires and whose `exclude` does not fire wins. This is why the compound heads sit before the families and why `other` is last. A new pattern is therefore tested twice: that it matches what it should, and that it does not shadow a leaf further down (the 4.6 sampler automates the second test).
3. **Head before full head.** The loop-cut head is tried before the uncut head, and a match on the shorter head wins.
4. **Strong before weak.** All `match` and `match_ctx` patterns of all leaves run before any `match_low`, so a weak pattern of an early leaf can never beat a strong pattern of a later leaf.
5. **Name before size.** A `dims_route` runs after the name is settled and can change a leaf only along the 15 declared routes (a row with `only = "low"` fires on low hits only).
6. **Title before breadcrumb.** The crumbs are consulted only when nothing in the title matched.

**Fallback to `other`.** When pass 4 is reached the job is NOT built. The record carries the top-3 candidate leaves (taken from the crumbs and the VLM question of Section 6, not from the title) and the human queue shows them (6.5). Tripo at 2,500 quads is used only after a reviewer confirms a leaf. Measured on the live harness:

| Title (crumb) | Result | Why this is the right outcome |
|---|---|---|
| `Kilim Pillow Cover 20 x 20` | `pillow` (cushion, 600 quads, host su) | The head ends in `cover`, not `kilim` |
| `Yoga Mat`, `Mouse Mat Desk Pad` | `other` (queue) | `mat_small` excludes them; a human decides, and they are not home-design assets |
| `Door Mat Coir` | `other` (queue) | The trailing material word is unknown to `trail_finish` (a gap, see below), but the result is the safe one |
| `Ravenna` (crumb `Furniture > Living Room > Sofas`) | `sofa`, `via=crumb`, low | Pass 3; below 0.80, so the VLM question runs |

**Known routing gaps found while writing this section.** Each was measured on the live harness. None is fixed here, because the rules are read-only for this report; each is a candidate golden probe for the rules author.

- `Pillow Cover Kilim` (the colourway word last) routes to `rug_rect`, not `pillow`. The head is `pillow cover kilim`, which the rug pattern `kilims?$` matches. Proposal: add `pillow` and `cushion` to the `exclude` list of `rug_rect`.
- `Door Mat Coir`, `Bathmat` and `Kitchen Mat Anti Fatigue` go to `other`, not `mat_small`. The first and third carry a trailing word that `trail_finish` does not know (`coir`, `fatigue`); `bathmat` has no space. All three end in the safe outcome (the human queue), but these are common products. Proposal: add `coir`, `jute`, `sisal`, `rubber` and `foam` to `trail_finish`, and `bathmats?` to the `mat_small` patterns.
- The comment on `breadcrumb_depth = 2` in `[detect]` says "then the URL slug", and the harness does not implement a URL-slug pass. A pass-3 hit on the slug is therefore a **[PROPOSAL]**: split the slug on `-`, drop the SKU and the colour tail, and run passes 1 and 2 on the rest.

### 5.3 The output record, the pseudo-code, the cost and the golden-probe design

#### 5.3a The output record

`route()` returns one record per product. The generator, the sheet writer and the review page read only this record. The harness returns the keys in the first column; the second column says what the app or the sheet does with it.

| Key | Type | Meaning | Consumer |
|---|---|---|---|
| `leaf` | string | The routed leaf (one of 100, plus `other` and `x_accessory`) | sheet `Category` (through the leaf's `catalog` name), `Asset Family` |
| `family` | string | The leaf's family; read from the leaf, not returned as its own key by the harness | sheet `Asset Family`; the triage lists in `[triage.avoid]` |
| `via` | string | `match`, `ctx`, `title`, `low`, `crumb` or `other`: how the leaf was found | confidence (5.2), the reasons list |
| `pat`, `pas` | string, int | The winning pattern and the pass number (1 to 4) | the review page ("matched `\bsofas?$` in pass 1") |
| `low` | bool | True when pass is 2 or more, or a low `dims_route` fired | the VLM leaf question (Section 6) |
| `mods` | list | The modifiers that fired (`outdoor`, `kids`, `set`, ...) | review page chips |
| `set` | pair or null | `(kind, action)`: kind is `identical` or `mixed`; action is `split`, `first`, `keep` or `skip` | the batch writer (5.4 set-of-N) |
| `builder` | string | `tripo`, `rug`, `art`, `box`, `lathe`, `drape`, `slab`, `cushion`, `cards`, `hybrid` or `skip` | the build dispatcher |
| `alt` | string or null | The fallback builder when a procedural gate fails (`lathe`, `cushion`, `box` gates in 4.1) | the build dispatcher |
| `host` | string | `fl`, `wl`, `ce` or `su`; written through `[host_map]` | sheet `host`, the app (5.5) |
| `quads` | int | The quad budget | the generator call |
| `post` | list | Post-process steps (`pivot_cb`, `flatten_back`, `fold`, `close_back`, ...) | the post-process queue |
| `flags` | list | `T` transparent, `Th` thin structure, `S` soft goods, `Em` emissive, `Ho` hollow, `Fu` foliage (4.1) | R1 profile flags (A1), Section 6 |
| `dims` | pair of ranges | The plausible height `h` and longest side `l` in cm for this leaf | the `warn = units` check, the size sanity check |
| `thick` | number or null | Thickness in cm for thin leaves (5.4 table) | the slab and art builders |
| `warn` | string or null | `units` when the listed size falls outside `dims` | REF_UNITS_SUSPECT (6.4) |
| `head`, `head_full`, `marks` | strings, list | What the routing saw, and the set words that were stripped | the review page (so a reviewer sees why) |
| `reasons` | list | **[PROPOSAL]** a flat list of reason strings assembled from the keys above, for the review page and the log: `pass 1 match`, `modifier outdoor`, `dims route sofa -> loveseat (low)` | the review page, A1 R9 logging |
| `confidence` | number | **[PROPOSAL]** the number of 5.2 | Section 6 |
| `scale` | string | **[PROPOSAL]** The scale rule of the leaf or family (`box`, `uniform_height`, `uniform_width`, `thickness`, `footprint`); the harness resolves it internally and does not return it | the scale step |
| `mode` | string | **[PROPOSAL]** How the asset is made, derived from `builder`: `proc` (rug, art, box, lathe, drape, slab, cushion, cards), `p2` (tripo; v2's `mode_for` returns `p2`, `smart` or `hd`, and since 2026-10-06 returns `p2` for every category), `hybrid` or `skip` | the build dispatcher, the sheet |

A real record from the live harness (shortened to the keys a reader needs):

```text
Kivik Sofa 3-Seat Grey Fabric
  leaf=sofa via=match pas=1 low=false mods=[] set=null builder=tripo host=fl quads=12000
  post=[pivot_cb] flags=[S,Th] dims={h:[55,125], l:[140,340]} head="kivik sofa"
```

A record is complete: every attribute is resolved from the leaf, the family and the defaults, so a consumer never walks the rules file itself.

#### 5.3b Pseudo-code, close to `rules.py` style

The harness implements this in about 250 lines; the sketch keeps the structure and drops the bookkeeping, with `scan()` (one pattern pass over the leaves in file order, `exclude` checked first) left out. It is plain Python in a fence that is NOT tagged as part of the harness, so it is never executed.

```python
def route(title, crumbs=(), dims=None):
    raw = ikea_strip(title)                       # step 1: original case, all-caps name rule
    t = fold(raw)                                 # step 2
    t = brand_strip(t)                            # step 3
    head, head_full, marks = head_of(t)           # steps 4 and 5: cut, loop to 8, strip sets
    mods = fire_mods(head, head_full, title, crumbs, marks)   # step 6

    hit = scan(forms=[head] + ([head_full] if head_full != head else []),
               mods=mods, with_title=True, weak=False)         # step 7
    if hit is None:
        hit = scan(forms=[head], mods=mods, with_title=False, weak=True)   # step 8
    if hit is None:
        for seg in segments(crumbs[-2:][::-1]):    # step 9: most specific first
            hit = scan([fold(seg)], mods, with_title=False, weak=False) \
               or scan([fold(seg)], mods, with_title=False, weak=True)
            if hit: hit.via = "crumb"; break
    if hit is None:
        hit = Hit(leaf="other", via="other", pas=4)            # step 10

    rec = resolve(hit, mods, marks)                # step 12 (attribute resolution)
    rec = apply_modifier_routes(rec, mods)          # step 11a
    rec = apply_set_route(rec, marks, title)        # 11b
    rec = apply_dims_routes(rec, dims, title, hops=3)           # 11c
    rec = apply_host_routes(rec, dims)              # 11e
    rec.warn = "units" if dims and out_of_range(rec, dims) else None   # 11f
    rec.low = rec.pas >= 2 or rec.low
    return rec
```

The shape matters more than the lines. (1) There is no scoring: a hit is the first leaf in file order, so the router is deterministic and explainable by one pattern and one pass number. (2) The passes are separate loops, so a strong pattern anywhere beats a weak pattern earlier in the file. (3) Everything after the match is a pure function of the record and the config, which makes golden probes cheap to write.

#### 5.3c Complexity and cost

- **Patterns.** 428 in total: 317 `match`, 13 `match_ctx`, 33 `match_low`, 4 `match_title` and 61 `exclude`. A pass-1 scan is at most 317 regex searches per form and usually stops far earlier.
- **Worst case.** About 6 x 350 short regex searches on strings of 30 to 80 characters; linear in the pattern count, independent of catalogue size.
- **Measured.** 514 probes in 0.095 s: 0.19 ms per title on average, 0.42 ms for a title that falls to `other`, 0.83 ms with two breadcrumb segments (Windows, one core, Python `re`). A 100,000-product catalogue routes in under a minute; one generation costs seconds of GPU time and $0.30 to $1.30 (A1 Section 1G).

#### 5.3d Golden-probe test design

The probes of 4.5 are the CI test of the router. The design below is what the existing 514 probes follow, written down so that a new probe is easy to add and a dead pattern is easy to find.

**Probe table format.** One line per probe, in a fenced block tagged `golden` inside Section 4 (this section deliberately contains none):

```text
title [|| crumb > crumb] => leaf [; key=value ...]
```

The keys: `leaf` (left of `=>`), `via`, `b` (builder), `q` (quads), `host`, `low` (0 or 1), `mods`, `post` and `flags` (each listed item must be present), `nomods`, `set` (identical, mixed, none), `act` (split, first, keep, skip), `dims` (input only, cm, for example `h90,w200,d95`), `warn`, `head` and `v2` (the v2 emulation class). Only the keys a probe lists are compared.

**What each probe must cover.** Every leaf has at least one positive probe, and every leaf with an `exclude` has one negative probe. The coverage check fails the run when a leaf has no probe; today it is 102 of 102. A trap of 1.5 is named in its probe's comment.

**Dead-pattern reporting.** `--dead` lists every pattern no golden probe matches, with its leaf and kind. 4.6b counts 149 dead patterns plus 41 dead excludes (of 428). A dead pattern is untested code, not necessarily a bug; the aim is to shrink the count by probing the common words, not to reach zero. The 4.6c sampler is the second net.

**Regression rule.** A probe is a regression test. When a pattern changes, the probe either still passes or the change is wrong; it is never edited to make a change pass without a comment that names the title, the old leaf and the reason (the comment is the audit trail). A new bug found in the wild becomes a new probe in the same commit as its fix.

**The v2 column.** The `v2=` key compares the v3 result with the v2 emulation (`--v2`). It is how Section 3 is machine-verified: every collision listed there is a probe whose `v2=` class is `DIFFERS`.

**How to run it.** The harness reads the report on stdin and writes no files (4.7). With no flag it prints the schema check and the golden results; `--v2` prints the v2-versus-v3 table of Section 3; `--leaves` prints one resolved row per leaf (including its `scale` rule); `--dead` lists untested patterns; `--set` prints set-kind decisions; `--heads` prints the head of every probe. Current result: `schema: 102 categories, 17 families, 16 modifiers, 15 dims routes, 0 errors` and `golden: 514 probes, 0 failed; leaves covered 102/102`. The same command is the CI step and exits non-zero on a schema error, a failed probe, an uncovered leaf or an unknown key.

**Where the probe set is thin.** Each measured gap of 5.2 deserves a probe in the same commit as its pattern fix (`Pillow Cover Kilim`, `Door Mat Coir`, `Bathmat`, `Kitchen Mat Anti Fatigue`). IKEA form A is case-sensitive by design: `BEKANT, Desk sit/stand, white, 160x80 cm` routes to `standing_desk`, but a title-cased scrape (`Bekant, ...`) loses the all-caps cue and falls to `other`. The batch writer must pass the title as published; add the title-cased form as a documented `other`.

### 5.4 Dimension rules

The catalogue stores `width`, `depth` and `height` in cm (sheet columns `Width (cm)`, `Depth (cm)`, `Height (cm)`). Every product is scaled to those three numbers, so a wrong number is a wrong asset that looks right. The rules below say which listed number is which axis, how units are read, and what happens when the listing and the generated geometry disagree. The harness implements the `[dims_parse]` constants, the per-leaf `dims` ranges, the 15 `dims_route` rows and the `warn = units` check; the label-aware parser is a **[PROPOSAL]**.

#### 5.4.1 Which axis is which, per family

W is the app's X axis (side to side as the piece faces the viewer), D is Z (front to back), H is Y (up). "Overall" means the outermost extent including back, arms, handles and legs, in the state the asset is modelled (assembled, closed, upright, open for an umbrella).

| Family or leaf | W | D | H | Trap and rule |
|---|---|---|---|---|
| Sofa, loveseat, accent chair, recliner, bench, ottoman | Side to side, overall (arms included) | Front to back, overall | Top of the back, NOT the seat height | The listing often shows seat height, arm height and seat depth as extra fields; ignore them for the box and keep them in the notes. A recliner is modelled closed and upright |
| Sectional | The longer side of the assembled bounding box | The other side of the bounding box | Top of the back | An L is boxed by its two arms; LAF and RAF are judged standing in front of the piece. A per-piece listing (`Left Arm Facing Loveseat`) is the piece, never the whole |
| Bar stool, counter stool | Seat or base diameter | Same | Overall height | The `bar_height` modifier compares the SEAT height (counter 24 to 27 in, bar 28 to 32 in, 1.5); the box uses the overall height |
| Office chair | Base diameter or arm span, the larger | Same | Overall height, minimum of the adjustable range | Height-adjustable chairs list a range; pick the minimum (`range_pick = min`) |
| Dining, coffee, side, console, desk | The longer horizontal side | The shorter horizontal side | Top surface | Round and oval: a round table has W = D = diameter. Rectangular tables list L x W; L is the app's W |
| Extension table | Closed length (`dim_pick = min`, `build_state = closed`) | Width | Top surface | Living Spaces lists Closed / Open / Leaf; take Closed. `66-84 in` is read as 66 |
| Bed | Across the head, frame included | Head to foot, frame included | Top of the headboard | The mattress size is not the frame size; the frame is about 8 to 15 cm wider and longer (UNVERIFIED, typical). Use the listed frame size; see 5.4.5 for names |
| Mattress | Width (the short side) | Length (the long side) | Thickness | Locale table (5.4.5) |
| Nightstand, dresser, wardrobe, bookcase, sideboard, tv_stand, cabinets | Side to side | Front to back, drawers closed | Top | Depth with open doors or drawers pulled out is not the depth |
| Floor lamp | The larger of base and shade | Same | Overall height to the top of the shade | The listed W x D is often the BASE (1.5); compare it with the shade diameter in the title or the image, and if only the base is known, scale the width by the image ratio rather than the listing **[PROPOSAL]** |
| Table lamp, desk lamp | Shade diameter (the larger of shade and base) | Same | Overall height including the shade | A listing "height to the top of the shade" is overall; a listing "base height" is not |
| Pendant, chandelier | Diameter | Diameter | The fixture body, NOT the adjustable drop | The listing "overall height 60 in" often includes cord or chain. Chain and cord are `chain` and `cord_strip` post-processes |
| Rug, mat | The first listed number (shorter side, as published `5 x 8`) | The second number (longer side) | Thickness from the table in 5.4.4 | Round: W = D = diameter. A runner is aspect 2.5 or more. The builder uses the footprint exactly |
| Art, framed art, mirror_wall, wall shelf | Width, FRAMED | Thickness from 5.4.4 | Height, FRAMED | "W x H" order is ambiguous in a listing; reconcile with the image aspect. Framed size differs from art size; take the framed size |
| Floor mirror | Width | Lean depth: height x sin(5 to 8 degrees) for a leaner (about 15 to 24 cm at 170 cm tall) [ESTIMATE], the stand depth for a cheval | Height | `mirror_floor` is a floor item with a mirror in its name, so see 5.5 for the app trap |
| Vase, candle holder, sculpture | Maximum diameter | Same | Height | The `uniform_height` rule: the generator output is scaled to the listed HEIGHT, and W and D follow |
| Plants (potted) | Spread, or the pot diameter if the spread is not listed | Same | Total height INCLUDING the pot | If the listing says "plant only" add the pot (the `plant_pot_combine` step). The `plant_potted` and `plant_tree` `dims_route` rows move a 130 cm or taller potted plant to `plant_tree` and a tree below 90 cm to `plant_potted` |
| Pillow | Width | Loft (10 cm [ESTIMATE]) | Height of the flat face | A pillow lists W x H as flat sizes (`20 x 20 in`) |
| Curtain panel, blind | Width of ONE panel | Thickness (5.4.4) | The drop (length) | Width is per panel, never the window; a listing "2 panels" is a set (5.4.3) |
| TV | Diagonal x 0.8716 | 6 cm (the `[dims_parse] tv` depth) | Diagonal x 0.4903 | 5.4.7. A listed W x D x H overrides the diagonal |
| Other leaves (chaise, standing desk, headboard, sconce, ceiling fan, clock, soundbar, fireplace, umbrella, kids bed, crib, throw, refrigerator) | Width (clock, ceiling fan: the diameter) | Depth (sconce: the projection; headboard: the thickness; chaise: the chaise length; standing desk: the top depth) | Height (standing desk: the LOWEST height; umbrella: open) | The overall-extent rule; a refrigerator's depth is without the handle if both are listed (UNVERIFIED which the app expects); plausibility is the leaf's own `dims` range in 4.4 |

#### 5.4.2 Parsing rules (the traps of section 1.5, as parser rules)

The rule that settles every ordering question is: **read the labels, never the position.** The retailer orders differ (Section 7 lists them): Living Spaces writes W x D x H; Wayfair, Article and Temple & Webster write H x W x D; CORT writes Length x Depth x Height.

1. **Tokens.** A number followed or preceded by a letter group is labelled: `W`, `Wide`, `Width`, `Overall Width` give W; `D`, `Deep`, `Depth`, `Front to Back` give D; `H`, `High`, `Height`, `Tall`, `Top to Bottom` give H; `L`, `Length`, `Long` give the long side (W for furniture, D for rugs, 5.4.1); `Dia` and `Diameter` give W = D. `32.5'' H X 73'' W X 31.5'' D` is H = 32.5 in, W = 73 in, D = 31.5 in.
2. **Unlabelled triples.** `84 x 36 x 33 in` with no labels is read W x D x H, which is the common US furniture order and the order the v2 parser assumes (`DIM_RE` requires the three labels W, D, H after the numbers, in that order). The result is low confidence and the review page shows it.
3. **Units.** In this order: an explicit label on the number (`cm`, `mm`, `m`, `in`, `"`, `''`, `ft`, `'`), then the batch `unit` column, then the retailer's locale (a `.com` US site is inches, `.com.au` and `.co.uk` and IKEA outside the US are cm), then `range_guess` (the last resort, 5.4.8). Feet and inches (`7'2"`) combine: 7 x 30.48 + 2 x 2.54 = 218.4 cm.
4. **Both systems in one string.** IKEA and some US pages print `60x80 cm (24x31 in)`. When both are present, take the metric pair and check the inch pair against it within 2%; a mismatch beyond that is a `CATALOGUE_DIM_WRONG` candidate.
5. **Fractions.** `38 1/2`, `38-1/2`, `38.5` and a vulgar fraction are the same number. (The title fold of 5.1 removes fractions from the HEAD only; the dimension parser reads the unfolded string.)
6. **Ranges.** `66-84 in` and `28 to 48 in` read as the minimum (`range_pick = min`); only `extension` tables and `module` pieces ever need the other end.
7. **Packaging and component dimensions.** `Box Dimensions`, `Shipping`, `Package`, `Carton`, `Shelf Dimensions` and similar labels are never the product. They are discarded before parsing (Article prints Box Dimensions beside General Dimensions; IKEA prints packaging).
8. **Set listings.** See 5.4.3.
9. **mm.** An unlabelled number is not read as mm: if all three values are 100 or more and the longest side is outside the leaf's `dims.l` as cm but inside it after dividing by 10, the record gets `warn = units` with the hint "mm?" **[PROPOSAL]**. An explicit `mm` label is honoured (some Australian listings use mm, 1.5).
10. **What the v2 parser does.** `rules.py` `DIM_RE` accepts `<n> W x <n> D x <n> H` only, so a Wayfair, Article or Temple & Webster `H x W x D` string does not match and the product is skipped with "no listed size". The batch contract (A1, Section 7) lets the manifest carry `w_in`, `d_in`, `h_in` or `w_cm`, `d_cm`, `h_cm` explicitly, which is the safest path: the scraper maps the labels, the generator never guesses.

#### 5.4.3 Sets, and counts of N

The set action is a leaf attribute (4.4a): `split`, `first`, `keep` or `skip`. The dimension rules per action are:

| Case | Dimensions | Example |
|---|---|---|
| Identical set, action `split` (nesting tables, pillows, side tables sold as a pair) | Per piece. One size for the set ("Set of 2 side tables, 24 x 18 x 26 in") is per piece; sizes per piece (nest of 3) go to each piece. N is recorded and the sheet writes N rows or one row with `units = N` | `Set of 2 Nightstands` |
| Identical set, action `first` | The first piece only | a pair of wall sconces |
| Identical set, action `keep` | The OVERALL box of the arrangement when listed (a three-panel gallery set `36 x 24 in overall`), else the per-piece size plus the layout spacing | an art set |
| Mixed set (`mixed`, default `skip`) | No dimensions are used; the job is skipped with `REF_SET_MIXED` and a human splits it | a dining table and four chairs sold together; a living-room set of sofa and loveseat |
| Sectional | Never split: the leaf is exempt from the set logic (`exempt_leaves`), and the size is the assembled bounding box | `3-Piece Sectional` |
| Bedding set | Mattress size by name (5.4.5) | `Queen Comforter Set` |
| Rental sets (CORT) | CORT is a rental catalogue where "set" is the norm: take each piece's own listing line, never the package | a `<Name> Sofa Package` page (structure UNVERIFIED, Section 7) |

#### 5.4.4 Thin items and the thickness table

Thin items have a listed W and H and no usable depth. The builders take the thickness from the table below (the leaf's `thickness_cm`); a listed depth within a factor of 0.5 to 2 of it replaces it, anything else is ignored with a warning **[PROPOSAL]**.

Thickness in cm, from the leaf's `thickness_cm` in 4.4: `mat_small` 1.2, `rug_shaped` 1.5, `rug_round` and `rug_rect` 1.0, `clock_wall` 4.0, `mirror_wall` 3.0, `art_framed` and `art_set` 3.0 (3.8 with the `unframed` modifier, for canvas on a stretcher), `wall_textile` 2.0, `curtain` 5.0, `blind_shade` 6.0, `tv` 6.0 (`[dims_parse] tv`).

The app's 40 cm minimum-dimension rule (5.5) means a wall leaf whose three dimensions are all 40 cm or more is NOT hung on the wall even if its host says so; the thicknesses above keep every thin leaf far below it.

#### 5.4.5 Locale table for bed and rug names

A size NAME is not a size: `king` is 193 cm wide in the US, 152 cm in the UK and 183 cm in Australia. The name resolves through the retailer's locale (the domain, or the IKEA path `/us/en/`, `/au/en/`), never from the word alone. When the title carries dimensions, they win and the table is a cross-check.

Mattress sizes, width x length, in cm (metric figures from [Wikipedia: Bed size](https://en.wikipedia.org/wiki/Bed_size), fetched during this research; inch figures from 1.5). They differ by 1 to 3 cm because inch sizes are rounded; match a listing to the NEAREST row within about 3 cm per axis [ESTIMATE].

| Name | US | UK | AU | NZ | EU |
|---|---|---|---|---|---|
| Single / twin | twin 98 x 189 (38 x 75 in) | single 91 x 191 (36 x 75 in) | single 92 x 188 (36 x 74 in) | single 92 x 188 | 90 x 200 |
| Twin XL | 98 x 202 | n/a | n/a | n/a | n/a |
| King single / small double | n/a | small double 122 x 191 | king single 107 x 203 (42 x 80 in) | king single 107 x 203 | 120 x 200 |
| Full / double | full 136 x 189 (54 x 75 in) | double 137 x 191 (53 x 75 in imperial figure) | double 138 x 188 (54 x 74 in) | double 135 x 188 | 140 x 200 |
| Queen | queen 152 x 202 (60 x 80 in) | n/a | queen 153 x 203 (60 x 80 in) | queen 150 x 203 | 160 x 200 |
| King | king 193 x 202 (76 x 80 in) | king 152 x 198 (59 x 79 in) | king 183 x 203 (72 x 80 in) | king 165 x 203 | 180 x 200 |
| California king | 183 x 212 (72 x 84 in) | n/a | n/a | n/a | n/a |
| Super king | n/a | 183 x 198 (71 x 79 in) | 204 x 204 | 183 x 203 | 200 x 200 (UNVERIFIED) |

Collisions: US `full` and UK, AU and NZ `double` are within 3 cm (one row for the four); the three `queen` sizes are within 3 cm (one row); `king` has FOUR widths (193, 183, 165, 152) and `super king` two (183, 204); a US `twin` (98) and a UK `single` (91) differ by 7 cm and are NOT one row. The review page shows the locale it assumed.

Rug sizes (feet x 30.48): 2 x 3 ft is 61 x 91 cm, 3 x 5 is 91 x 152, 5 x 8 is 152 x 244, 6 x 9 is 183 x 274, 8 x 10 is 244 x 305, 9 x 12 is 274 x 366; a 2.5 x 8 runner is 76 x 244. A size NAME in a title (`5x8`) is NOMINAL: the real rug is often a few cm smaller (UNVERIFIED, typical; take an `Actual size` field when present). Australian rugs are sold in cm bands (small 80 x 150 to 120 x 170, medium 160 x 230 to 200 x 300, large 250 x 350 to 300 x 400, 1.5); a band is a hint, never a size, so a band name with no numbers goes to the queue as `REF_DIMS_MISSING`. A round rug's single number is the diameter.

#### 5.4.6 Listed against measured

The scale step multiplies the generated mesh to the listed box. A hallucinated depth is then silently squashed and the asset looks right and is wrong. The rules:

1. **Keep the source and a confidence with every number.** A number read from a labelled spec block is the best; from a labelled title next; from an unlabelled title next; derived from a name (the locale table, the TV diagonal) is next, with about 3 cm of uncertainty; read from the image is last.
2. **Compare before scaling.** After generation, compare the native bounding-box ratios (W:D, W:H) with the listed ratios. A deviation beyond tolerance means a bad generation, a wrong catalogue number, or an extendable, modular or set product. A1 starts the tolerance at about 12 to 15 percent [I from A1, to be calibrated]. Show the reviewer BOTH numbers.
3. **Rugs and art are exact.** A rug or art item is built to the listed W x D, so the check is on the RECTIFIED photo: reject the image when its rectified aspect differs from the listed aspect by more than about 5 percent [I from A1].
4. **Uniform scale for round and tall things.** `uniform_height` leaves (lamps, vases, plants) scale to the listed height and let W and D follow, so a wrong width does not distort the shape; `uniform_width` ceiling leaves scale to the diameter.
5. **A wrong listing is a reject code, not a rescale.** `CATALOGUE_DIM_WRONG` (A1) is the reject; the fix is a corrected `batch.csv` row, not a hand edit in the 3D file.

#### 5.4.7 TV sizes

A TV title's number is the screen DIAGONAL, so the parser derives the box when no W x D x H is listed. For 16:9, W = diag x 0.8716 and H = diag x 0.4903, with a bare depth of 6 cm (`[dims_parse] tv`). Worked (1 in = 2.54 cm): 55 in gives 121.8 x 68.5 cm; 65 in gives 143.9 x 80.9. A listing with `with stand` dimensions overrides the derived box. `Fits TVs up to 65 inch` on a stand is a capacity, not a width. A 55 in TV (121.8 cm) exceeds the app's 120 cm stackable footprint (5.5), so it rests on a stand through the relative rule, never on a table through the absolute one.

#### 5.4.8 Units, `range_guess` and `warn = units`

`unitless = "range_guess"` means: with no unit anywhere, three numbers are read as cm if they fit the leaf's `dims`, else as inches if THAT fits, else the card is flagged. It works for large pieces (84 x 36 x 33 on a `sofa` fits in inches only) and fails for small ones (`28 x 18 x 22` fits `side_table` in either unit). Hence the order of 5.4.2 item 3: label, then the batch `unit` column, then the retailer's locale, and only then `range_guess`. `warn = units` runs AFTER the unit is known and fires when the final size is outside the leaf's range (a 36 cm sofa, a 360 cm side table). It never changes a number; it adds `REF_UNITS_SUSPECT` (6.4). The 15 `dims_route` rows refine a LOW-confidence leaf (a `sofa` under 170 cm becomes a `loveseat`; a bare `stool` at 55 cm or lower is an `ottoman`) or move the host (a potted plant of 60 cm or lower rests on a surface); they never override a confident name.

### 5.5 App gates and known gaps

The generator must not produce an asset the app will then mishandle. The gates below are read from the web app's source (read-only, `src/`); a line number is given where it matters, and anything not verified in the code is marked UNVERIFIED. None of this section changes the app: each gap is a note for the person who owns it.

**Gate 1: is it a wall hanging? (`isWallHangingData`, `src/utils/assetClassification.js`).** The decision, in order:

1. The asset `host` (or `base_type`) contains the text `wall` (case-insensitive): wall.
2. Else `is_on_wall` is true: wall.
3. Else the category NAME matches the heuristic `isWallHangingAsset`: the words `artwork`, `art work`, `painting(s)`, `picture(s)`, `poster(s)`, `tapestr`, `mirror(s)` and `sconce(s)`, or `wall` followed by `art`, `decor`, `hanging(s)`, `lamp(s)`, `clock`, `mount(ed)` or `piece(s)`. It tests the CATEGORY name only, never the title.
4. A wall verdict is then cancelled when the category is on the floor-only list (`FLOOR_ONLY_SUPER_CATEGORIES`: Beds, Sofas, Accent Chairs, Dining Chairs, Dining Tables, Coffee Tables, Desks, Dressers, Nightstands, Benches, Poufs, Rugs, Plants, Terrace Outdoor, and their members), or when ALL THREE dimensions are known and the smallest exceeds 40 cm (`WALL_HANGING_MAX_THICKNESS_CM`).

**Gate 2: can it rest on something? (`wallBinding.js`).** `isStackableSize` is true when height is 80 cm or less and the longer horizontal side is 120 cm or less, with a missing dimension defaulting to 100 (so a product with no height is NOT stackable: it must always carry one). In-scene stacking uses the relative gate `canRestOnHost`: the dragged item may be at most 1.05 times the host in footprint area AND longest side; a host cannot be a floor covering, wall hanging or wall fixture. The router's `su` host therefore means "the app decides from the size", not "pinned to a surface".

**Gate 3: is the category allowed? (`ALLOWED_CATEGORIES`).** 21 super-categories and 166 names. About 30 database categories are not on the list. Each leaf's `catalog` name in Section 4 uses the closest allowed name until the list is extended.

**Known gaps, each with the exposure and a recommended mitigation:**

| # | Gap | Exposure for v3 | Mitigation |
|---|---|---|---|
| 1 | **A floor mirror is hung on the wall.** Any category whose name contains `mirror` is a wall hanging, and an explicit floor host does not cancel it | `mirror_floor` (host `fl`, catalog `Mirrors`) would be placed as a wall item; the thickness guard does not help (a 170 x 60 x 15 cm mirror has a 15 cm smallest side) | Hold `mirror_floor` out of automatic publication, or ask the app owner to honour an explicit non-wall `host` in `isWallHangingData`. UNVERIFIED which the owner prefers |
| 2 | **`tapestr\b` cannot match `tapestry` or `tapestries`** (the next letter is `y` or `i`) | `wall_textile` rows filed under `Tapestries` hang only if their `host` carries `wall` | Write `host = wall-based` (gap 4) or file under `Wall Decor` |
| 3 | **The category heuristic is the fallback for 18 of the 619 assets in the wall categories** (comment in `assetsAPI.js`, not re-counted); the rest carry a wall host | Wrong for any wall asset written without a host | Always write the host |
| 4 | **The v2 sheet has no host column, and the Add-products path writes the VENDOR HOSTNAME into `host`.** `COLUMNS` in `sheet.py` has no placement column; `buildAssetInput` (`assetWriteAPI.js`) sets `host: p.vendor_host` | The `[host_map]` value `wall-based` cannot be written by those two paths. Whether the asset-upserter can is UNVERIFIED | Add a placement column to the sheet or batch, and decide where the vendor hostname goes (`web_page` already carries the URL) |
| 5 | **No ceiling placement.** `[host_map]` maps `ce` to `ceiling-based`, and a grep of `src/` found no ceiling-host logic | `chandelier`, `pendant`, `ceiling_fan`, `flush_mount` (all `ce`) are placed as ordinary floor items; what the user sees is UNVERIFIED | Do not publish the four `ce` leaves automatically until the app places them; keep them as drafts |
| 6 | **No elevated floor placement.** A `floating` nightstand, tv_stand, vanity or desk is a floor item; a `wall-based` row is placed as a wall hanging. UNVERIFIED | `floating` leaves would sit on the floor or hang flat on the wall | Keep their host `fl` (the rules do) |
| 7 | **Curtain hosting is UNVERIFIED.** `curtain` has host `wl`, but `curtain` is not in the heuristic words, so it hangs only if the host says `wall` (gap 4) | Curtains may drop on the floor | Hold `curtain` and `blind_shade` for a manual check |
| 8 | **An easel print may be classed as a wall hanging.** The `easel` modifier (4.4) sets host `su`, but the category name (`Paintings`, `Pictures`) matches the heuristic and the host does not cancel it | A print on an easel would hang on the wall | UNVERIFIED; same fix as gap 1 |
| 9 | **`RUG_RE` over-matches by name.** `\brug\b|\brugs\b|carpet|floor\s*mat|\bmat\b|\brunner\b|\bkilim\b` makes anything with those words collision-exempt | A `kilim pillow`, `table runner` or `yoga mat` in the catalogue would be treated as a floor covering | The control stage and the head-final rule (5.1) keep the first two out; `Yoga Mat` goes to `other` (the queue) |

**What each leaf needs from the app:** floor leaves need the right category and a height; the `su` leaves need a height of 80 cm or less and a footprint of 120 cm or less to be stackable at all; the `wl` leaves need `host = wall-based` or a category the heuristic knows, and one dimension below 40 cm; the `ce` leaves wait for app support (gap 5). About 30 DB categories are missing from the allow-list (`Vanity Stands & Tables`, `Outdoor Accessories`, `Bath`, `TV (50 and larger)`, ...): a leaf then files under the closest allowed category (its `catalog` field). A 55 in TV (121.8 cm) exceeds the 120 cm stackable footprint and rests on a stand through `canRestOnHost`. Section 6.5 lists the leaves held in the review queue for this reason.

---

## 6. Image triage: cheap tests first, then one closed-set VLM question

This section turns the `[triage]` block of 4.4b into a procedure. It is the A3 side of A1's gate G0 and of the R1 profile, and agrees with A1 on four points: the checks run BEFORE any generation credit is spent; the router stays a table, not a prompt; the default is deny (an unclear product goes to a human queue with a "needs better image" state, not to the generator); and `is_ai_rendered` caps auto-accept while `is_lifestyle` always sends the image through the sanitiser (A1 R2). All thresholds are starting values [ESTIMATE] to be tuned on the first 200 jobs.

### 6.1 The ordered tests

Each product has a gallery of candidate images. Tests run cheapest first; the first image that passes every test is the reference, and a failure moves to the next candidate (`next_view`). Tests 1 to 4 read text, free; tests 5 to 11 are image statistics, milliseconds on CPU [ESTIMATE]; test 12 needs the VLM answer of 6.2.

| # | Test | Config | Trips when | Reason code |
|---|---|---|---|---|
| 1 | Router verdict | `on_hit` | leaf is `other` | `REF_LEAF_UNKNOWN` |
| 1b | Skip leaf | builder `skip` (`x_accessory`, `bbq_grill`, `bath_fixture`) | any | none: a skip, not a rejection |
| 2 | Set kind | `set_mixed` with action `skip` | mixed set | `REF_SET_MIXED` |
| 3 | Size present and sane | 5.4 | no size, or `warn = units` | `REF_DIMS_MISSING`, `REF_UNITS_SUSPECT` |
| 4 | Filename | `filename_reject` (room, airoom, dimensions, dims, lifestyle, scene, swatch, material, fabric, texture, infographic, feature, detail, closeup, zoom); `filename_prefer` (signature, front, side, main, hero, primary, cutout, studio) | a reject token | by token: `REF_LIFESTYLE`, `REF_DETAIL`, `REF_INFOGRAPHIC`, `REF_SWATCH` |
| 5 | Resolution | `min_edge_px = 600` (Tripo needs 256) | shorter edge below 600 | `REF_LOW_RES` |
| 6 | Aspect | `aspect_range = [0.45, 2.2]`, exempt for `flat_leaves` | outside the range | `REF_ASPECT` |
| 7 | Cut-out border | `cutout_border_white = 0.93` (share of border pixels near white or transparent) | below 0.93 | none alone: asks the VLM |
| 8 | Fill | `min_fill = 0.30` | below 0.30 | `REF_LIFESTYLE` |
| 9 | Blobs | `max_components = 1` (blobs of 2 percent of the item or more) | more than 1 | `REF_MULTI_ITEM` |
| 10 | Border touch | `max_border_touch = 0.02` | above 0.02 | `REF_CROPPED` |
| 11 | Text density | `max_ocr_density = 0.015` | above 0.015 | `REF_TEXT_HEAVY` |
| 12 | Avoided props | `[triage.avoid]` (`_all` = people, pets; plus per-family and per-leaf lists) | a listed prop visible | `REF_LIFESTYLE` |

Notes. Only the Living Spaces filename tokens are verified (v2 `[photos]`); others are a guess. `flat_leaves` (`rug_rect`, `rug_round`, `rug_shaped`, `mat_small`, `art_framed`, `art_set`, `wall_textile`, `curtain`, `blind_shade`, `mirror_wall`) are exempt from test 6 and get `rectify` instead. A leaf key in `[triage.avoid]` REPLACES its family's list. Transparent leaves (flag `T`) skip tests 7 and 8 (glass has no clean border) and go to `hybrid`, never rejected.

Why the top-15 categories need these tests (TL;DR 6): rugs, wall art, mirrors, curtains, bedding, pillows, lamps, tabletop decor, plants, styled shelves (bookcases, display cabinets), TVs, dining sets, beds, sofas and outdoor furniture usually ship lifestyle scenes, several items per frame, or props. Tests 7 to 12 and the VLM question are their default path.

### 6.2 The single VLM question

If every cheap test passes and the router confidence is 0.80 or more (5.2), NO model call is made. `ask_vlm_when = "any_test_trips or leaf_in_top15"`: the model is asked when a test tripped and the image may still be usable (7, 12, a borderline fill), or when the leaf is on a short list of high-volume leaves where props are the usual failure (not defined in 4.4b; fix it from the first batches [PROPOSAL]). A1 specifies ONE structured call per product, folded into G0; this is it. The model writes no free text and never chooses among all 100 leaves:

```text
{ "images": [ { "index": integer,
                "image_type": enum [cutout, lifestyle, multi_item, detail, infographic, swatch],
                "item_count": integer,
                "view": enum [signature, side, front, back, top, detail],
                "props": array of enum [tv, books, decor, plants, pillows, throws, lamps, dishes,
                                        food, clothes, toys, people, pets, monitor, mirror, frames, furniture],
                "has_text": boolean, "ai_rendered": boolean } ],
  "best_index": integer or null,
  "leaf": enum [candidate_1, candidate_2, candidate_3, none] }   // only when router confidence < 0.80
```

The enums are `[triage] vlm_enum` and `[vocab] views, props`, so the schema is generated from the rules file and cannot drift. The three candidates are the router's leaf, the leaf the next pass or the `dims_route` would give, and the next sibling in the family [PROPOSAL]. Structured output with a JSON-Schema `enum` is documented for Gemini at https://ai.google.dev/gemini-api/docs/structured-output ; that the same setting works with several image parts in one request is expected but UNVERIFIED on that page and needs a 20-product pilot before this section is relied on. No model version or price is named here: both are configuration, and one small call is negligible against a $0.30 to $1.30 generation (A1 Section 1G) [I]. Temperature 0, as in A1 G4.

### 6.3 What the answers do, and the thresholds

| Answer | Action (`[triage.action]`) |
|---|---|
| `lifestyle` or `detail` | `next_view` |
| `multi_item` | `crop_matte` (detector box on the item the head names, then a re-matte); a set leaf splits first |
| `infographic` or `swatch` | `drop` the image |
| `cutout`, no listed prop | accept |
| `ai_rendered = true` | allowed, but caps auto-accept and always queues a human glance (A1 R1) |
| `best_index = null` | `no_view_passes`: queue with the three best candidates and their VLM labels |
| `leaf` is not candidate 1 | change the leaf, rerun the post-route steps of 5.1, mark `via = vlm` |

Thresholds: every number of 6.1 is [ESTIMATE] except the 256 px floor (Tripo guidance, A1). The router cut-off is `vlm_min_confidence = queue_below = 0.80`. Post-generation tolerances (A1 G2: about 12 to 15 percent bounding box, about 5 percent rug aspect [I from A1]) are in 5.4.6. Calibrate on 200 labelled jobs; move a threshold only when it changes at least five decisions, and record the change next to the value.

### 6.4 Reason codes

Every rejection carries one code. All 14 roll up to A1's `BAD_REFERENCE`; the two dimension codes also feed `CATALOGUE_DIM_WRONG` when the number is wrong rather than missing.

`REF_LIFESTYLE` (scene or props around the product, or the product small in frame); `REF_MULTI_ITEM` (more than one product); `REF_DETAIL` (a close-up of a part); `REF_INFOGRAPHIC` (a dimension drawing or feature graphic); `REF_SWATCH` (a colour or material swatch); `REF_LOW_RES` (shorter edge under 600 px); `REF_CROPPED` (the product touches the border); `REF_ASPECT` (a banner or collage shape); `REF_TEXT_HEAVY`; `REF_NO_VIEW_PASSES` (no gallery image passed); `REF_LEAF_UNKNOWN` (the router returned `other`); `REF_SET_MIXED` (different products sold together); `REF_DIMS_MISSING` (no usable size); `REF_UNITS_SUSPECT` (size outside the leaf's plausible range, 5.4.8).

### 6.5 What goes to the human queue, and what is skipped

**Queue** (default-deny, A1 R1): `REF_NO_VIEW_PASSES`, `REF_LEAF_UNKNOWN`, `REF_SET_MIXED`, `REF_DIMS_MISSING`, `REF_UNITS_SUSPECT`, any VLM `leaf = none`, any `ai_rendered = true` below confidence 0.95 [ESTIMATE], and the leaves with an app gap (5.5): `mirror_floor` (gap 1), the four ceiling leaves `chandelier`, `pendant`, `ceiling_fan`, `flush_mount` (gap 5), and `curtain`, `blind_shade` (gap 7), until the app side is confirmed. Each queue item carries the top-3 candidate leaves, the three best images with their VLM labels, the router record (5.3), and the dimensions with source and assumed unit.

**Skipped, no credit spent.** The three `skip` leaves; `other`; a mixed set with action `skip`; any product with no usable size; any product with no passing image. A job bills only after the image tests pass. With no VLM (no key, quota or outage) the router fails closed: a candidate that tripped a test is queued as `REF_NO_VIEW_PASSES`; one that passed everything at confidence 0.80 or more continues, because it needed no call.

### 6.6 How the review page shows it

Per product: the chosen image and next two candidates, each with chips showing test number and threshold (`fill 0.41 / 0.30 OK`), the router record (5.3), the size with its source, assumed unit and any `warn`, and reason codes. Below 0.80 confidence the top-3 leaves appear as one-click buttons; a click re-runs the post-route steps and logs a golden-probe candidate. "Needs better image" sends the product back with its code. A1's tiers review built assets, not this page.

---

## 7. Retailer field guide: where each field lives, and what a batch.csv row needs

Scope. For the eight retailers of the first catalogue wave this section gives the URL pattern, where name, colour, material, size, SKU and price live, and how the size is written. It is a field guide, not a scraping licence: A4 owns the access rules, and **livingspaces.com was not fetched for this report** (it blocks bots and the team respects that); that row comes from the v2 tooling. Other facts come from public search snippets or single page fetches; anything no page confirmed is **UNVERIFIED**. Markup changes without notice, so re-check each row on the day.

### 7.1 URL patterns and field locations

| Retailer | Product URL pattern | Name, colour, material | SKU | Price |
|---|---|---|---|---|
| Living Spaces | `https://www.livingspaces.com/pdp-<slug>-<sku>` (for example `...-412611`) | Title is "Name Colour Material Type". Image filenames carry `<id>_<colour>_<material>_<type>_<view>_<nn>.jpg` (v2 `[photos]`) | "Additional Details" block (UNVERIFIED which label) | UNVERIFIED |
| Wayfair | `https://www.wayfair.com/furniture/pdp/<brand-name-slug>-<sku>.html`; SKU like `w006470368` | Title is "Brand Name Type"; colour and material in the title and a specifications block (UNVERIFIED) | in the URL tail | UNVERIFIED |
| CORT | `https://www.cort.com/furniture-rental/<Category>/<Subcategory>/<Type>/P<digits>` | page is JS-rendered, no static Product JSON-LD (A4); field locations UNVERIFIED | `P<digits>` in the URL (UNVERIFIED that it is the SKU) | rental price, not a purchase price |
| Temple & Webster | `https://www.templeandwebster.com.au/<Name-Words>-TMPL<digits>.html`; category pages end `-C<digits>.html` | Title carries the seater count ("3 Seater"); other fields UNVERIFIED | `TMPL<digits>` in the URL | AUD; location UNVERIFIED |
| IKEA US | `https://www.ikea.com/us/en/p/<name-variant>-<s?><8 digits>/`; the slug code is the article number without dots (`s39440593` is 394.405.93) | Title Form A "NAME, type, colour, size" or Form B "NAME type"; colour in the variant slug and title | article number (the frame and the cover are separate articles) | USD |
| West Elm | `https://www.westelm.com/products/<slug>-<h or g><digits>/` (for example `oliver-sofa-h6962`); `?sku=3088364` selects a variant | Title carries a size range ("Haven Sofa (60"-108")") | `?sku=` is the variant SKU; the slug code is the product | UNVERIFIED (the site returned 403 to the research fetch, not circumvented) |
| Crate & Barrel | `https://www.crateandbarrel.com/<slug>/s<digits>` (one product) or `/f<digits>` (family with size options) | inches in the title; colour and material UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Article | `https://www.article.com/product/<id>/<slug>` | name "Agotu 44" Marble Coffee Table - Walnut"; colour "Wood Stain: Walnut" (fetched) | "SKU No." (for example `SKU19383`); images at `cdn-images.article.com/products/SKU19383/...` | $699 on the fetched page |

Article is the best-structured source: A4 verified Product JSON-LD with `width`, `height` and `depth` strings such as "44 in", an image sitemap whose captions say "DIMENSION of ...", and sitemaps `https://www.article.com/sitemap.xml`, `/product_sitemap.xml`, `/product_image_sitemap.xml`. West Elm's `/products/` is not disallowed and `product-sitemap-index.xml` exists (A4); JSON-LD there is UNVERIFIED. CORT publishes `https://www.cort.com/sitemap/index.xml` and `/sitemap/detail0.xml` and has an `llms.txt` (A4). Affiliate networks (A4): CORT impact.com, Temple & Webster Rakuten 41108, Article Awin 55215.

### 7.2 How the size is written

The order differs by retailer, so the scraper must parse by the LETTERS, never by position, and write explicit `w_`, `d_`, `h_` columns.

| Retailer | Written as | Unit | Notes |
|---|---|---|---|
| Living Spaces | `90"W x 38.5"D x 29.5"H` | in | W x D x H; the order the v2 `DIM_RE` accepts |
| Wayfair | "Overall Dimensions: 32.5'' H X 73'' W X 31.5'' D" | in (US), cm (UK) | H x W x D; a specification block lists "Overall Width - Side to Side", "Depth - Front to Back", "Height - Top to Bottom". The site blocks non-browser clients (A4 S13) |
| CORT | Length / Depth / Height (trade catalogue) | UNVERIFIED | rental sets are normal here (5.4.3) |
| Temple & Webster | "Overall: 80cm H x 302cm W x 155cm D" | cm | H x W x D; a sofa also lists seat width and depth. 1.5 of this file says "W x D x H": the observed order is H x W x D, so labels decide |
| IKEA US | labelled fields Width, Depth, Height, Seat height; systems add Max width, Min depth, Max depth | in (US, fractions in separate fields), cm elsewhere | Packaging dimensions are also shown: NEVER use them |
| West Elm | mirrors write "Overall: 78"w x 42"d x 35"h"; the current order is UNVERIFIED | in | a size range in the title means the product is configurable: take the listed variant |
| Crate & Barrel | "37" high, 93" wide, 46" deep" (order UNVERIFIED); mirrors show Overall With Back Cushion Height plus Seat Width, Depth and Height | in | for seating prefer the Overall figures, not the seat |
| Article | "General Dimensions: 15"H x 44"W x 22.5"D" | in | H x W x D; "Shelf Dimensions" and "Box Dimensions" are components and packaging: NEVER use them |

v2's `DIM_RE` accepts only `<n> W x <n> D x <n> H`, so a Wayfair, Article or Temple & Webster string does not match and the product is skipped with "no listed size" (5.4.2 item 10). The batch columns below avoid the problem.

### 7.3 What a batch.csv row needs

The contract is `autogen/batch.py` (read-only, read for this report). The file is read as `utf-8-sig`; each header is lower-cased with non-alphanumerics turned into `_` and looked up in an alias table. A row is built only if a size can be found, in this order of precedence: the inch columns `w_in`, `d_in`, `h_in`; then `w_cm`, `d_cm`, `h_cm`; then unitless `w`, `d`, `h` with a `unit` column; then a size in the folder name or a note. A product with no size is skipped with "no listed size". The recognised columns are: `folder`, `title`, the size columns above, `url`, `sku` (also `product_id`, `id`), `price`, `currency`, `vendor` (also `brand`), `category`, `mode`, `units` (also `set_of`), `close_back`, `notes`.

| Field | Needed? | Source on the retailer page |
|---|---|---|
| `folder` | yes: the image folder | the scraper's own naming (`<vendor>_<sku>`) |
| `title` | yes: the router input, AS PUBLISHED (5.3d, the IKEA case rule) | the product name; keep IKEA's all-caps name |
| `w_in` / `d_in` / `h_in` (or `_cm`) | yes: without them the row is skipped | 7.2, mapped by letter; the overall dimensions only |
| `url`, `sku`, `vendor` | yes for traceability | 7.1 |
| `price`, `currency` | optional | 7.1; AUD for Temple & Webster |
| `category`, `mode` | leave EMPTY: the router decides (4.1) | none |
| `units` | when the listing is a set of N identical pieces (5.4.3) | the title ("Set of 2") |
| `unit` | when using unitless `w`, `d`, `h` | the retailer's locale (7.2) |

A real row built from the Article page of 7.1 (the dimensions are the page's "General Dimensions", H x W x D, mapped by letter):

```text
folder,title,w_in,d_in,h_in,url,sku,price,currency,vendor
article_SKU19383,"Agotu 44"" Marble Coffee Table - Walnut",44,22.5,15,https://www.article.com/product/<id>/<slug>,SKU19383,699,USD,Article
```

The `<id>/<slug>` is a placeholder (the fetched page's id was not recorded). A Wayfair "32.5'' H X 73'' W X 31.5'' D" becomes `h_in=32.5, w_in=73, d_in=31.5`; a Temple & Webster "80cm H x 302cm W x 155cm D" becomes `h_cm=80, w_cm=302, d_cm=155`.
