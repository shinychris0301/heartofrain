HEART OF THE RAIN — M67 R2: VICTORY ANIMATION
19 October 2026. Design review revision.

OPEN THE COMPLETE PROJECT
Extract Heart_of_the_Rain_Unity_Project.zip. In Unity Hub, open
Heart_of_the_Rain/Unity with Unity 2022.3.62f3.
The full project includes Assets, Packages, ProjectSettings, all 50 Chapter 1
levels, existing pages, approved gameplay art/audio, and this revision.
No earlier archive is required. Unity will regenerate its local caches.

REVIEW THIS REVISION
Menu: Heart of the Rain > App > M67 R2 > Validate Celebration Assets.
Open Daria Celebration Review and enter Play Mode. It plays the same overlay
as a real win without changing campaign progress or awarding rewards.
Open Chapter 1 Finale Review to check the revised character in the story.
Capture Actual Game View is available from the same menu while playing.

VICTORY PRESENTATION
The success flow no longer creates the old LevelCompleteModal.
Daria celebrates directly over the existing board: a soft entrance, two claps,
an open-palmed congratulation, warm light, gold stars and falling confetti.
There are no victory-panel labels, reward boxes, progress bars or visible buttons.
The animation lasts 3.5 active seconds and advances automatically. Tap anywhere,
press Enter/Space on the focused overlay, or press Escape to skip after 0.65 seconds.
Reduced motion uses a still smiling pose for 1.6 seconds, without moving particles.
A neutral black shade peaks at 24% opacity; it does not introduce a blue/purple cast.

Rewards settle once, before animation. Completion or skipping opens the existing
next-level preview. The first clear of level 50 plays the chapter cinematic,
then opens the Journey ending directly; there is no intervening victory modal.
The chapter cinematic retains its narrative captions and Skip/Continue control.
Missing celebration art also advances safely without a victory modal.
Standalone gameplay review scenes use the same overlay for success. Their
Continue callback retains their existing level/replay behavior. Loss dialogs,
confirmed life loss, retry and booster reservations retain their existing flow.
The historical M66 result-review scene remains an archival design sample;
it is not used by the current live or standalone win routes.

DARIA ART AND MOTION
The replacement RGBA atlas has 16 forward-facing, smiling, waist-up poses.
Curly dark-brown hair, muted olive cloak, cream sleeves, brown leather and the
gold diamond clasp follow the original character reference. There is no runtime
color tint. The atlas uses sRGB, straight alpha, no mipmaps or texture compression.
Custom row boundaries avoid bleeding from the preceding pose row. Brief hand
transitions avoid prolonged double-hand silhouettes; gentle shoulder sway,
rebound, entrance overshoot and settling provide secondary motion.
The shader feathers the cropped waist into the board. This is sprite animation,
not a skeletal rig, motion capture or a newly supplied 3D character.

RESPONSIVE PRESENTATION
The overlay fits the screen safe area, preserves a square character viewport,
and supports compact/tall portrait, tablet and wide presentation geometry.
Seven geometry profiles are checked. Existing gameplay requests portrait;
landscape preview compositions are geometry checks, not validation of the whole
app's landscape layout. Actual phones and notch behavior still need Unity tests.
Focus loss pauses the animation clock. Skip cannot consume the initial victory
tap, and an Escape skip cannot also dismiss the next-level preview that frame.
English, Spanish, French, German and Russian remain supported. No Japanese added.

COLOR REVIEW
Approved board, background, HUD artwork, tile/obstacle textures, audio and level
JSON are byte-identical to the preceding package. The rejected result shell is
removed from the win route. Daria was regenerated against the original olive,
cream and brown reference, rather than adopting the reference game's purple.
The supplied Match Villains screenshot guides the panel-free composition only.
It is not included as game artwork or as a packaged dependency.

DELIVERABLES
Heart_of_the_Rain_Unity_Project.zip — complete current project.
Heart_of_the_Rain_M67R2_Celebrations.unitypackage — cumulative M67/R2 update
for the existing M66/M67 project; import with dependencies. It does not replace
ProjectSettings. Open the existing M67 review scenes via the updated menu.
Heart_of_the_Rain_M67R2_Celebration_Review.zip — runtime/source, checks,
preview video/stills, original character reference and incremental package.
The same review material is included under Heart_of_the_Rain/M67R2 in the full ZIP.

VALIDATION AND LIMITS
404 production HomeLevelFlow checks passed with a fake UI host, exercising 246
legal actions on levels 21, 28, 36, 49 and 50 with available/missing presentation
assets. Duplicate callbacks, automatic next-level routing, chapter routing,
reward settlement, loss/retry and booster rollback were checked.
18,171 chapter/character policy checks and 77,249 overlay geometry/particle/time
checks passed. Legacy receipt-policy regression checks also passed.
Asset references, stable GUIDs, retained gameplay artwork and package integrity
were checked. See Validation for reports and precise scope.

The MP4/PNG previews are offline compositions using the actual packaged artwork
and compiled production motion samples, over an initial review board. They show
only the animation, not an actual played win or the subsequent next-level UI.
The video is 60 fps; sprite pose changes follow their authored timing.
Unity Editor/API compilation, shader compilation, Play Mode, real input/audio
focus, native builds and mobile performance have NOT been run here.
Persistent campaign/cloud saves remain a separate milestone; existing local
review-state persistence behavior has not been expanded in this revision.

OFFLINE REPRODUCTION
Source/run_validation.py requires .NET 8, Python, tree-sitter and tree-sitter-c-sharp.
Set M67_DOTNET_ROOT if dotnet is not on PATH. Source/render_review.py uses Pillow,
numpy and FFmpeg. Retained fixtures live in CoreReference and M66Reference.
Source contains the final Unity sources and reproducible offline tools.
Use the packaged Unity folder as the canonical implementation.

DOWNLOADS
Use the current full-project link in the chat, signed into the same account.
A valid local ZIP and successful save do not prove that a particular browser can
download it. If the link still fails, the exact browser error will identify the
remaining delivery issue. The smaller Unity update is an alternative for users
who already have the preceding project.
