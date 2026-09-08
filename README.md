# Exact area reference

Replicate pan/rotate/zoom from Krita canvas to docker. If you zoom your artwork into hands area and linked same size reference, this docker tries to zoom into hands area of it as well. Mostly useful for reproductions and study works.

- Tested on Krita 5.3.2.1
- Maybe 5.2.x also supported
- Python required: 3.x

## Controls

Source/target DPI: resolution, screen or pixel density compensator; for multi-monitor usage
Load: show file open dialog
Paste: use clipboard data as image (also supports absolute filename)
Clear: remove reference image
Realign: no matter of current canvas position, link image to center of window
Mouse drag: adjust relative pan

## Install

Menu -> Tools -> Scripts -> Install python plugin from file
Or, copy/unzip into %appdata%\krita\pykrita dir.

## Further plans

Mirror view supported, but don't handle pan coords correctly. These going negative while mirroring tho shouldn't.

If you experience lags or inadequate Krita behavior, let me know in issues. Current update timer set to 25ms and maybe I need to sacrifice it.
