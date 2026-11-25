MODELS SHEET AUTO-SYNC (and thumbnails)
=======================================
Once this is set up, nobody imports the CSV into the Models sheet by hand any more.

  Model approved (by Gemini or by a reviewer)
      -> its row is added to the Models tab (or updated, if its File name is there already)
      -> the whole row turns light yellow 2
      -> the thumbnail is put into the Thumbnail cell, from Assets\<Vendor>\<asset>\<File name>.jpg
  Model failed (Gemini gave up, a run ended in error, a reviewer pressed Fail, the card was discarded)
      -> a red row in the "Autogen failures" tab, with the reason, when, and which PC
      -> it stays red until the model is approved; then it leaves that tab and goes to Models (yellow)

Failures never go in the Models tab: the asset-upserter imports Models rows by row range and cannot see colours.

How it works: the tool writes one small file per event into
    Asset Auto Generator\assets\_runner\sheet_outbox
and the script in this folder (models_sheet_script.txt), installed on the Models sheet, reads that folder every
5 minutes, applies the events, and moves each file to sheet_outbox\done. No API keys, no Google Cloud project,
and the sheet stays private.


SET IT UP (once, by someone who can edit the Models sheet)
-----------------------------------------------------------
1. Open the Models Google Sheet. Extensions > Apps Script.
   If an older "Fill thumbnails" script is there, delete all of it.
2. Open models_sheet_script.txt (this folder), Ctrl+A, Ctrl+C, paste into the editor, Save (disk icon).
   Check the settings at the top. MODELS_TAB must be the exact name of the tab the asset-upserter imports
   from (now 'Models').
3. Reload the sheet. An "Asset tools" menu appears (to the right of Help).
4. Asset tools > Sync now. Google asks for permission the first time: pick your account and click Allow.
   If you see "Google hasn't verified this app", click Advanced > Go to ... (unsafe). It is your own script.
   It reads the Assets and sheet_outbox folders and writes this sheet.
5. Asset tools > Turn on auto-sync (every 5 min). It then keeps running when the sheet is closed, as your
   account. Turn it on for ONE person only.

The person who turns auto-sync on needs:
  - edit access to the sheet;
  - Content manager (or Manager) on the Connecter Drive, so done files can be moved.
    Without it, each done file is renamed _<name> and left in the outbox. That still works.


TRY IT FIRST ON A TEST COPY (recommended)
------------------------------------------
File > Make a copy of the Models sheet, and do steps 1-4 on the copy.
The tool's outbox already has events once a model has been approved or failed since 2026-10-28.
To send one on purpose, run this in the tool folder:
    python -m autogen export-vendor --asset <asset name> --sheet
Then click Sync now and check:
  - the row appears at the bottom of Models, light yellow, with the picture in the Thumbnail cell;
  - when something failed, an "Autogen failures" tab with a red row.
Notes:
  - Sync now on the copy moves the outbox files to done, so the real sheet won't see those events.
    Re-send them with the export-vendor command above.
  - The thumbnail step (picture inside the cell) is the part not tried on a real sheet yet. If the
    Sync now box says "thumbnail not put in: ...", send that message to Mukul / Claude.


DAY TO DAY
----------
Nothing to do. To see what happened, click Asset tools > Sync now: the box lists what it applied.
  - A row that is already in Models and gets approved again (a fixed revision) keeps what people typed.
    Only the size (Width/Depth/Height) and the paths (3D Model path, Image Path) are refreshed,
    empty cells are filled, and the thumbnail is replaced.
  - A failure for a model that is already approved in Models is ignored. The approved model stands.
  - Fill thumbnails (selected rows) still works on any tab with "Thumbnail" and "File name" headers,
    e.g. for rows added by hand.
  - To turn the tool side off, set  sync = false  under [sheet] in config.toml.


IF SOMETHING GOES WRONG
-----------------------
"no tab named Models"        Set MODELS_TAB at the top of the script to the tab's real name.
"thumbnail when Drive has it"
                             The JPG was not on Drive yet. The next runs keep trying for 3 hours, then
                             leave it; Fill thumbnails can add it later.
"not readable, moved to bad" A damaged event file; it is in sheet_outbox\bad. Re-send that model with
                             export-vendor --sheet.
Nothing happens              Asset tools > Turn on auto-sync again (it replaces the old timer). Also check
                             that sheet_outbox has files and that Google Drive for desktop is running on
                             the PCs that run the tool.
Two people turned it on      Harmless (a lock stops them running together), but one can turn it off.
