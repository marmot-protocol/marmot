# Small-size visual review of the candidate alphabet

Status: non-normative review of the [candidate list](emoji-candidates.md). This records a visual inspection and its
repairs. It does not certify a human recognition rate or approve the alphabet for protocol use.

## Method and result

All 512 entries were rendered in 24- and 32-raster-pixel tiles, with maximum glyph bounds of 20 and 28 pixels,
using Noto Color Emoji and White Noise's fixed Marmot PNG. Every entry was inspected in grayscale. Both raw and contrast-normalized grayscale distances were
used to rank all 130,816 unordered pairs. The 96 closest pairs in each initial ranking were inspected. After the
repairs, the normalized ranking was repeated and its 96 closest pairs inspected. Rankings help find candidates to
inspect; their scores are not security or recognition thresholds.

The review replaced 24 candidates, preserving the original Matrix 64 and the fixed Marmot artwork. The count remains
512 and the ideal uniform five-symbol sequence remains 45 bits. The edits remove identified weak pairs; different
Unicode values and different raster images alone are insufficient evidence of usable verification symbols.

## Replacements

| Removed | Compared with | Replacement | Reason |
| --- | --- | --- | --- |
| 🦧 orangutan | gorilla | 🫀 anatomical heart | Similar primate pose and compact silhouette. |
| 🐺 wolf | Cat | 👁️ eye | Pointed-ear face silhouette; small facial detail carries the difference. |
| 🐭 mouse face | koala | 🦴 bone | Round ears and central face overlap at small sizes. |
| 🍊 tangerine | Apple | 🌂 closed umbrella | Near-round fruit with a small stem; grayscale weakens the distinction. |
| 🍐 pear | droplet | ✌️ victory hand | Similar tapered silhouette. |
| 🥖 baguette bread | cucumber | 💢 anger symbol | Diagonal elongated silhouette with fine internal marks. |
| 🥯 bagel | doughnut | 💀 skull | Both are ring pastries; toppings are a weak small-size cue. |
| 🧂 salt | glass of milk | 💥 collision | Tall pale container; holes and label become small. |
| 🥫 canned food | oil drum | ✋ raised hand | Cylindrical container; a small label supplies much of the difference. |
| 🍜 steaming bowl | cooked rice | 🫁 lungs | Food bowl distinguished by small chopsticks and contents. |
| 🧁 cupcake | Cake | 👻 ghost | Cake shape distinguished by small candles and wrapper details. |
| 🥛 glass of milk | salt | 💬 speech balloon | Tall pale container with weak internal detail. |
| 🛢️ oil drum | canned food | ☸️ wheel of dharma | Similar container geometry. |
| ⛅ sun behind cloud | Cloud | ⚠️ warning | An added sun is easy to miss behind the cloud. |
| 🎄 Christmas tree | evergreen tree | ☯️ yin yang | Same tree outline with small decorations. |
| 🏸 badminton | tennis | 👾 alien monster | Racket shape distinguished by a small shuttlecock or ball. |
| 🔋 battery | canned food | 🛠️ hammer and wrench | Cylinder distinguished by small electrical marks. |
| 🗳️ ballot box with ballot | package | ✔️ check mark | Box shape distinguished by a small inserted paper. |
| ⛏️ pick | Hammer | 🔱 trident emblem | Diagonal handle and horizontal head are close at small sizes. |
| 🧰 toolbox | briefcase | ♻️ recycling symbol | Case with handle; small latch detail is a weak cue. |
| 🧪 test tube | microphone | 🚫 prohibited | Tilted tube shape distinguished by a small cap/head. The trial nose replacement was also rejected against the dress silhouette. |
| 🩸 drop of blood | droplet | ❓ red question mark | Nearly the same silhouette; hue is the primary difference. |
| 🚪 door | mobile phone | ☢️ radioactive | Tall framed rectangle with small interior details. |
| ⚱️ funeral urn | amphora | 💪 flexed biceps | Vessel shape distinguished by subtle neck and handles. |

## Remaining acceptance work

Use at least 32 logical pixels per glyph in the comparison UI, rather than ordinary inline-text size. Show a stable
ordered layout, useful spacing, sufficient contrast, and an enlargement option. Preserve image proportions. Review
the actual bundled artwork in both themes; changing an emoji font invalidates this font-specific inspection.

Run participant comparisons of five-symbol sequences with one position changed, including grayscale, repeats,
low vision and different writing directions. Keep labels hidden for the visual-only test so naming does not supply
an extra cue; test screen-reader and numeric alternatives separately. Include the remaining nearest pairs such as
phone/traffic light, club/spade, and diagonal tools in those comparisons. Record mistakes and missed mismatches,
rather than treating different pixels or a similarity score as a pass.

Until that work supports the complete alphabet and artwork, the 45-bit number is an ideal encoding calculation,
not a measured user-verification guarantee. If the set cannot meet the comparison criteria, keep a smaller alphabet
and a longer sequence instead of silently lowering the security margin.
