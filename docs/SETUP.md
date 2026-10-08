# Setting up Asset Auto Generator v2 on a Windows PC

**Version 2** (folder `AssetAutoGenerator_v2`) adds the automatic Gemini QA and the Discard button. It opens at `http://localhost:8766`.
The first version (`AssetAutoGenerator`) is **retired** since 2026-10-06: v2 sorts the `assets` folder into one folder per
vendor, which v1 can't read, so v1's Start.bat now only points here.

## v2: automatic QA in short
- **What it does.** After every new Tripo or Meshy result, the app renders the model in Blender from 8 sides plus one from above, and sends the renders with the product photos (front, angled/side, back) to Gemini. Gemini scores the model 0–100, plus the front, side and back separately. It also lists what is wrong with each view. This costs no credits, about $0.05 per version on the Gemini key.
- **Free fixes first.** Each version is also scored with Auto smooth 30° (and with duplicate layers removed when that was flagged), and the better one is kept. The best one is scored three times and averaged, because single answers vary.
- **What happens next** (Auto QA on, the default in v2):
  - 60 or more: accepted automatically into `final_glb`, with the steps that scored best.
  - 50–59: one paid retry, then the better attempt is accepted.
  - Under 50: up to two paid retries (Meshy, then Tripo with a new seed). If it's still under 50, the card waits for a person.
- **You can always step in.** Retries wait the normal undo window, and you can change or undo any decision on the card. To score only and decide yourself, set `auto = false` under `[qa]` in `AssetAutoGenerator_v2\config.toml`.
- **Key.** Gemini uses `GEMINI_API_KEY` from the same `.env` file (the shared one already has it).
- **Photos.** Gemini sorts each product's photos (front, back, sides, angled; doors open or not). Tripo then gets a multi-view run when there's a straight front plus another straight side, and Meshy gets the best 4. Add back and side shots whenever you have them: a single photo gives the generators much less to work with.
- **One photo only?** If such a product scores low, the first retry has Gemini draw the front, sides and back. Each drawing is checked against the listed size before use, and Tripo builds from all of them; the second retry gives Meshy the photo plus the drawings. The card says which views were drawn or rejected. Real back and side photos are still better whenever you can get them.
- **Order.** The newest cards are at the top.
- **Discard.** "Discard this product…" on any card that isn't accepted takes it off the review list and cancels anything queued for it. Nothing is deleted. It appears under the **Discarded** filter, with **Restore**.


No Claude account is needed. You need a Windows 10 or 11 PC, Google Drive for desktop and about 1 GB of free space.

## One-time setup (about 10 minutes, mostly a download)

1. **Google Drive for desktop.** Install it and sign in with your Sparx Google account. In File Explorer, check that the shared drive opens:
   `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator`
   If Google Drive uses another letter (for example `H:`), add that path to `assets_dirs` in `AssetAutoGenerator\config.toml`.
2. **The package.** Either run it from the shared drive (the `AssetAutoGenerator` folder), or copy the whole `AssetAutoGenerator` folder to your Desktop and run it from there. Both work the same way. The assets always live on the shared drive, so everyone's reviews and results end up in one place.
3. **API keys.** Credits are charged to whichever accounts these keys belong to.
   - The keys are read from a file named `.env`. The app looks in three places, in this order: inside the `AssetAutoGenerator` folder, then in the folder above it (the shared `Asset Auto Generator` folder, which already has one), then in `%LOCALAPPDATA%\AssetAutoGenerator`.
   - To use your own keys, copy `.env.example` to `.env` inside `AssetAutoGenerator` (or into `%LOCALAPPDATA%\AssetAutoGenerator`) and fill in:
     - `TRIPO_API_KEY=tsk_...` (from platform.tripo3d.ai)
     - `MESHY_API_KEY=msy_...` (from meshy.ai)
   - Never put a `.env` file on GitHub.
4. **First start.** Double-click `Start.bat`.
   - The first time on a PC, it downloads a portable copy of Blender 4.2 (about 370 MB) into your user folder and checks the download.
   - Nothing is installed system-wide, and you don't need admin rights.
   - When it's ready, your browser opens the review page at `http://localhost:8765` (v2: `http://localhost:8766`).

If Windows shows "Windows protected your PC" for `Start.bat`, click **More info → Run anyway**. If your company blocks PowerShell scripts, ask IT to allow `setup\setup.ps1`.

## Every day

1. Double-click `Start.bat`. Keep the black window open while you work; closing it stops the app.
2. The review page opens in your browser. Each card shows the generated model.
   - **Steps** sit right under the 3D view and go into the saved GLB:
     - **Auto smooth 30°** and **Auto smooth 45°** are unticked by default (tick one; 45° also blends slightly sharper bends). Leave both unticked to keep the model exactly as shown.
     - Lamp shades are fixed automatically (no box to tick): their shading is rebuilt like Auto smooth 30° on the shade only, so leave Auto smooth off for lamps unless the base needs it.
     - **Remove duplicate layers** appears only when overlapping panels were found.
     - **Net panel → opacity** appears only on models with a mesh or netted panel (for example a mesh office-chair back). It replaces the net with one surface and a drawn opacity map.
   - **Use this version** (Tripo, Meshy or the earlier version): the picked tile and button are highlighted. The app writes the model to `final_glb` in that asset's folder, and to the vendor folder for CORT. If steps are ticked, it rebuilds the model with them first.
   - **Fail – regenerate**: the new run starts as soon as you submit. There is a 30-second **Undo** first, and no credits are spent until the undo window ends. The card shows progress. The new card appears when it's ready, usually 3–5 minutes later.
   - After a retry, the card shows the earlier version and the new one side by side: **Use v1** / **Use v2** (or **Use Tripo version** / **Use Meshy version** after a Meshy retry). Each side has its own steps. The one you pick becomes the final GLB.
   - A first retry runs on Meshy unless you switch it to Tripo.
   - **Vendor** buttons under the status filters show only CORT or only Living Spaces assets.
   - **Fix size** (top right of a card) corrects wrong dimensions or units without generating again, so it costs no credits.
     - The form shows the size as listed now, in cm. If inches were typed as cm, just switch Units to inches; the numbers stay as they are.
     - Tick **Keep proportions** to size by height only. It is ticked by default for lamps.
     - Every version on the card is rebuilt from its original download. On an accepted card, the final GLB and the CORT copy are rewritten with the same choice.
   - **Lamps** are always sized by height. The listed width and depth are often the base's, not the shade's, so they never stretch the model.
   - **Beds** get a 12" mattress only when the bed is an empty frame. When the generated bed already has a mattress, it is kept as is, and the card offers **Add 12" mattress** if you want one anyway.
   - **In progress** at the top of the review page shows every run that is waiting or working: its step (waiting with a countdown and **Cancel**, uploading, generating with Tripo's percentage, downloading, finishing), time so far and typical time. Click "running · queued" in the header to jump there. These status checks are free: no credits.
3. **Adding products:** click **Add products** at the top of the review page.
   - Drag the **Send to Auto Generation** button to your bookmarks bar once.
   - Open a Living Spaces product page and click the bookmark. The form fills itself in: title, dimensions and the gallery photos.
   - Check the category, dimensions and photos, then press **Generate**. Leave out photos with doors or drawers open.
   - If the size looks wrong for the category (for example a 36 cm-high dresser), a yellow note says the numbers look like inches (or centimetres), with a button to switch the units.
   - If the bookmark can't read a page, type the details and drop the product photos onto the form. Keep Living Spaces' file names, because the view in the name (for example `_side_18`) decides which photo is used.
4. **Adding from a reference folder (CORT and other vendors):** on **Add products**, paste the folder with the photos into "Or from a reference folder" (for example `G:\Shared drives\Connecter Drive\Assets\Cort\Sayl Work Chair\Files\Ref`) and press **Load photos**.
   - The title comes from the asset folder's name (`Sayl Work Chair`), the vendor is set to CORT, and the units switch to centimetres.
   - The accepted GLB is also copied into the folder that holds `Ref` (here `...\Sayl Work Chair\Files\sayl_work_chair.glb`). You can change or clear that path on the form.
   - Enter W × D × H, check the category and photos, then press **Generate**.

## Tripo model
- Every product is made with **Tripo P2** (the Smart Mesh model the Tripo website uses), in two steps like the website: the mesh first, then the texture as its own step (Tripo's newest texture model, detailed quality). One Tripo run costs **120 credits** (100 + 20).

## Products that come in several sizes
- **Adding:** tick **Comes in more than one size** on Add products. Mark the size shown in the photos (it uses the W × D × H above), give every size a short name (`queen`, `king`, `24x36`) and its W × D × H. Beds start with twin / full / queen / king / cal_king: fill in the ones the product has, remove the rest.
- **One generation** is made for the size in the photos. When it is accepted (by you or by QA), the other sizes are built from it in Blender, free, and saved with it: `final_glb\<name>_queen.glb`, `<name>_king.glb`… (and to the CORT folder). Legs, posts and corners keep their size; the middle is stretched.
- **Own design:** tick it for a size that looks different (a centre leg, an extra drawer, a different picture) and pick its photo. It gets its own card and its own generation (credits; art and rugs are free).
- **Later:** **Sizes…** on a card adds sizes or changes them. On an accepted card they are built at once.
- **UUID:** each card shows its UUID at the top with a **Copy** button. It never changes for that product (not when steps are ticked, the size is fixed or the final is rewritten); every size has its own.

## Stopping a run, deleting a card
- **Stop (×):** hover over a tile under **In progress** and click the × in its corner. It is there while the run is waiting, uploading, in Finishing (Blender) or in the Gemini QA, and hidden while Tripo/Meshy is generating (those credits are already spent).
  - Stopped in Finishing: the paid model is kept. **Finish it (free)** builds it later; **Remove** drops it.
  - Stopped before generating: nothing was spent. **Start again** or **Remove** (a new product then moves to `assets\_deleted`).
  - Stopped QA: the card says "QA was stopped" and waits for you; press **Score again** if you want a score.
- **Delete:** only in the **Discarded** filter. **Delete…** → **Delete** takes the card out of the app for good. Its files move to `assets\_deleted\<vendor>\<name>` on the drive, so a mistake can still be undone by moving the folder back. Empty `_deleted` yourself when you're sure.

## Two people at once

Several PCs can run the app at the same time. Each job is claimed by one PC, so nothing is generated twice. If a PC is switched off in the middle of a job, another PC takes the job over after 20 minutes, and it continues the already-paid task instead of paying again. The daily credit cap (`daily_cap` in `config.toml`) counts all PCs together.

## Where things are

| What | Where |
|---|---|
| Accepted models | `assets\<vendor>\<name>\final_glb\<name>.glb`, e.g. `assets\CORT\greystone_credenza\final_glb\greystone_credenza.glb`. CORT models are also copied next to `Ref` in the CORT folder they were added from. |
| Review versions, photos, decisions | `assets\<vendor>\<name>\` (`rows`, `work`, `source_images`, `decisions`) |
| Vendor folders | `assets\CORT`, `assets\Living Spaces`, `assets\Other` (no vendor given), and one per new vendor: the name typed in **Vendor** on Add products, or the folder under `Assets\` when adding from a reference folder. Folders added before this are moved in when the app starts. |
| Credits spent per day | `assets\_runner\credits\` |
| Generation rules (budgets, modes, photo choice) | `AssetAutoGenerator\rules.toml` |
| Settings (drive path, port, credit cap, undo time) | `AssetAutoGenerator\config.toml` |
| Portable Blender, machine id | `%LOCALAPPDATA%\AssetAutoGenerator\` |

## If something goes wrong

- **The page says it can't reach the app:** the black window was closed. Run `Start.bat` again.
- **"Shared assets folder not found":** Google Drive for desktop isn't running, or it uses a different drive letter. See step 1.
- **"Missing key" in the status bar:** add the key to `.env` (step 3) and restart.
- **A card says "On hold":** the daily credit cap was reached, or an account's balance is too low. Raise `daily_cap` or top up the account, then press **Try again**.
- **A card says "failed":** the message says why (for example, the generator rejected the photo). Press **Try again**, or change the decision.
- Run `Start.bat` and read the black window: problems found at start-up are listed there.
