# OMNI FLASH HOOK-LED PROMPT LIBRARY (v2)
Templatized from `ref videos/` (18 scene templates) + `ref videos/hooks/` (16 hook videos).
Every prompt is a single continuous 8–10s shot (unless a cut is specified), 9:16 vertical, UGC selfie-arm realism, product swappable via `{{VARIABLES}}`.
v2: each hook template now includes a **VISUAL HOOK (0–4s)** block — the exact camera rig, movement, focus behavior and effects observed in the reference video, and the prompts encode them beat-by-beat.

---

## 1. GLOBAL VARIABLE MAP

| Variable | What to inject |
|---|---|
| `{{PRODUCT_NAME}}` | Brand + product name as printed on packaging |
| `{{PRODUCT_VISUAL}}` | Forensic packaging description: shape, size, material, colors, label, logo placement. Consistency anchor — never abbreviate. |
| `{{PRODUCT_ACTION}}` | The one natural use-gesture: apply / sip / spray / unwrap / wear / tap screen |
| `{{TALENT}}` | One consistent on-screen character: age, gender, ethnicity, hair, wardrobe (avatar_character_library.json or preset below) |
| `{{SETTING}}` | Environment matched to demographic + category |
| `{{HOOK_LINE}}` | Spoken line in the FIRST 1.5 seconds |
| `{{OST}}` | On-screen text overlay, ≤6 words, bold sans-serif, top-third |
| `{{TONE}}` | Delivery energy: deadpan / hyped / soft-luxury / confident-expert |
| `{{CTA_LINE}}` | Final spoken/overlay line |

## 2. DEMOGRAPHIC PRESETS (swap these as the audience changes)

| Preset | {{TALENT}} | {{SETTING}} | {{TONE}} |
|---|---|---|---|
| Gen-Z US female | Woman 19–24, effortless styling, claw clip / baggy layers | Pastel bedroom, bodega, thrifted-decor apartment | Deadpan, ironic, fast |
| Millennial mom | Woman 30–42, soft knitwear, minimal makeup | Warm neutral living room, kitchen island | Warm, honest, relieved |
| Indian metro Gen-Z | Man/woman 20–28, streetwear + ethnic-fusion accents | Café steps, terrace at golden hour, metro street | High-energy Hinglish-friendly |
| Male 25–40 fitness/tech | Athletic man, fitted tee or performance wear | Home gym, whiteboard office, garage setup | Confident expert, punchy |
| Luxury female 28–45 | Polished woman, silk/tailored neutrals, fine jewelry | Marble vanity, golden-hour villa, hotel suite | Slow, hushed, ASMR-soft |
| Gen-Z male streetwear | Man 18–26, racing jacket / vintage sportswear, curly hair | City sidewalk, parking lot, skate spot | Casual bro-cam, mid-walk |

Swap rule: change ONLY `{{TALENT}}`, `{{SETTING}}`, `{{TONE}}`, `{{HOOK_LINE}}` language. Never change `{{PRODUCT_VISUAL}}`, the VISUAL HOOK camera grammar, or shot timing — those ARE the template.

---

# PART A — THE 16 HOOK TEMPLATES (from hooks/)
The scroll-stop lives in the first 1.5–4 seconds. The VISUAL HOOK block is the camera/effect recipe; the prompt encodes it verbatim.

---

## H1. THROWN-IN PRODUCT WAKE-UP (hooks/0376d63f — pink tote)
**Mechanic:** Static sleepy frame violently interrupted by the product flying INTO frame.
**VISUAL HOOK (0–4s):** Locked-off static wide, phone propped at couch eye-level — zero camera movement. 0–0.9s: subject asleep, frame dead still. ~0.9s: the product is TOSSED in from off-screen right on a shallow arc with real tumble physics and motion blur; it lands center-floor, rocks, settles upright label-to-camera exactly as she startles awake. ~3s: one hidden jump-cut punches in ~40% tighter as she slides off the couch toward it. The interrupt is a moving object inside a static frame.
**Hook lines:** "I woke up and it was HERE." / "POV: your order arrives while you nap."

**PROMPT:**
9:16 vertical UGC video, locked-off static wide shot from a phone propped at couch height in a {{SETTING}}, natural daylight, no camera movement. 0–0.9s: a {{TALENT}} lies asleep on the couch, completely still frame. At 0.9s a {{PRODUCT_VISUAL}} is thrown in from off-screen right — shallow arc, natural tumble and motion blur — landing on the rug center-frame, rocking once and settling upright with the label facing camera as she jolts awake with a gasp: "{{HOOK_LINE}}". 1.5–3s: she stares at it, then scrambles off the couch. At 3s a single jump-cut punches in 40% closer: she kneels beside the {{PRODUCT_NAME}}, lifts it, opens it and {{PRODUCT_ACTION}} with {{TONE}} energy. 8–9s: she hugs it to chest, grinning at lens, "{{CTA_LINE}}". OST "{{OST}}" at 0.3s, top third. Room ambience, soft thud SFX on landing.

---

## H2. MACRO PRODUCT → SLOW TILT-UP FACE REVEAL (hooks/310818fe — necklace)
**Mechanic:** Face withheld for 2 full seconds — product in macro owns the frame first.
**VISUAL HOOK (0–4s):** 0–2s: extreme macro close-up on the worn product at chest level, face fully cropped out, golden-hour side light with hard shadow edges slowly moving across skin; handheld micro-drift and gentle focus breathing keep it alive. 2–4s: one slow unbroken tilt-up along the neckline — lips enter frame at ~2.5s mid-sentence — ending in a tight talking-head crop at 4s. Focus racks product → lips → eyes during the tilt. No cuts.
**Hook lines:** "Everyone asks where this is from." / "This is why I get stopped on the street."

**PROMPT:**
9:16 vertical selfie video, warm golden-hour window light, shallow depth of field. 0–2s: extreme macro close-up on {{PRODUCT_VISUAL}} worn/held at the chest of a {{TALENT}}, face cropped out of frame entirely; hard sunlight edges drift across skin, handheld micro-jitter and slight focus breathing on the product details; her voice starts over the macro: "{{HOOK_LINE}}". 2–4s: one slow continuous tilt-up along the neckline — lips enter frame mid-sentence at 2.5s — finishing in a tight talking-head crop, focus racking from product to eyes. 4–7s: she speaks in {{TONE}}, glances down at the {{PRODUCT_NAME}}, touches it. 7–9s: soft smile, "{{CTA_LINE}}". OST "{{OST}}" fades in at 0.5s. Single unbroken shot, front-camera grain, quiet room tone.

---

## H3. DEADPAN DESK GRAB (hooks/319d686e — office lipstick)
**Mechanic:** Zero camera tricks — choreography is the hook: she grabs the product without looking, then first eye contact.
**VISUAL HOOK (0–4s):** Static propped camera, medium shot across the desk. Product pre-placed in soft-focus foreground beside the laptop. 0–2.5s: she types, never acknowledging camera. ~2.5s: her hand leaves the keyboard and grabs the product WITHOUT her looking at it. ~3.2s: she raises it beside her face — focus shifts to the product, and she makes first eye contact with the lens in the same beat. Later: she leans the product into the lens for a macro moment, face blurring behind.
**Hook lines:** "My coworker left this on my desk…" / "HR said stop talking about it. No."

**PROMPT:**
9:16 vertical video, static phone propped across an office desk, bright corporate daylight, medium shot. A {{TALENT}} types at a laptop in {{SETTING}}; a small {{PRODUCT_VISUAL}} stands in soft-focus foreground beside the keyboard. 0–2.5s: she types, eyes on screen, ignoring camera; ambient keyboard sounds. At 2.5s her hand leaves the keyboard and grabs the product without looking. At 3.2s she lifts it beside her face — focus racks onto the {{PRODUCT_NAME}} as she makes first eye contact and says "{{HOOK_LINE}}". 4–7s: she pushes the product toward the lens into crisp macro, label filling frame, face soft behind, and {{PRODUCT_ACTION}}, {{TONE}}. 7–9s: leans back, nods, "{{CTA_LINE}}", resumes typing with product displayed. OST "{{OST}}" at 0.4s. One static shot, autofocus breathing on the macro push.

---

## H4. ROOFTOP EDGE VERTIGO WALK (hooks/342e6d35 — skyline)
**Mechanic:** Altitude + motion: skyline parallax below makes thumbs freeze.
**VISUAL HOOK (0–4s):** Wide-lens selfie-arm rig, her extended arm visible and foreshortened at frame bottom. Constant walk-sway and handheld bob. She pivots along the roof edge so the skyline sweeps ~90° behind her across the first 4s — strong parallax of streets far below. Wind moves hair continuously; slight lens roll off horizontal; a bird crosses frame deep in background. No cuts, no stabilization.
**Hook lines:** "I climbed 60 floors to tell you this." / "If I'm risking my life, it's worth it."

**PROMPT:**
9:16 vertical selfie-arm video, wide front lens, overcast daylight. A {{TALENT}} stands on a skyscraper rooftop, {{SETTING}} skyline and streets dizzyingly far below, her extended arm foreshortened at the bottom of frame. 0–1.5s: walk-sway and handheld bob as she stares into the lens: "{{HOOK_LINE}}"; wind whips her hair, horizon tilted a few degrees. 1.5–4s: she pivots and walks along the rooftop edge so the skyline sweeps 90° behind her with strong parallax, holding up a {{PRODUCT_VISUAL}} into frame. 4–8s: quick {{PRODUCT_ACTION}} demo held high against the cityscape, {{TONE}}. 8–9s: grin, thumbs up, "{{CTA_LINE}}". OST "{{OST}}" at 0.3s. One continuous unstabilized shot, wind audio under clear dialogue.

---

## H5. FOREGROUND OBJECT DROP (hooks/381965b9 — baguette)
**Mechanic:** A themed prop plunges through the TOP of frame inches from the lens — scale shock.
**VISUAL HOOK (0–4s):** Static low-propped camera on the steps, angled slightly up. Frame 1: the prop drops vertically through the top edge IN EXTREME FOREGROUND — huge, defocused, nearly touching the lens — while she sits small and sharp in the background reaching up. ~1s: she catches it; scale snaps from lens-filling blur to normal size in her hand. Camera never moves; the hook is z-axis scale shock inside a static frame. She then holds the prop like a mic while producing the actual product from her pocket at ~3s.
**Hook lines:** "Wait— okay, as I was saying." / "The universe said take this."

**PROMPT:**
9:16 vertical UGC video, static phone propped low on the steps of a {{SETTING}}, tilted slightly up, soft overcast light. A {{TALENT}} sits on the steps with a takeaway coffee. At 0.2s a {{THEMED_PROP e.g. baguette / samosa / protein bar}} drops vertically through the top of frame in extreme foreground — massive, defocused, inches from the lens, with motion blur — while she reaches up sharp in the background and catches it at 1s, unfazed, saying "{{HOOK_LINE}}". 1.5–3s: she holds the prop like a microphone. At 3s she pulls a {{PRODUCT_VISUAL}} from her pocket with the other hand and presents both to camera. 4–7s: {{PRODUCT_ACTION}}, riffing in {{TONE}}, prop absurdly still in hand. 7–9s: lean into lens, "{{CTA_LINE}}". OST "{{OST}}" at 0.4s. Static frame throughout, street ambience.

---

## H6. AIRPLANE-WING ARM-RIG (hooks/67775be9)
**Mechanic:** Impossible place, mundane ritual — sold by rig-stability physics.
**VISUAL HOOK (0–4s):** Extended-arm selfie rig locked to her body: SHE stays tack-sharp and stable while the wing, cloud deck and horizon drift and slowly roll ~10° behind her. Wide FOV, her foreshortened arm anchoring the bottom corner. Hair and top rip in the wind while her pose stays casual — the stability-vs-chaos contrast IS the effect. No cuts, no camera moves beyond the rig's micro-shake.
**Hook lines:** "This works literally anywhere." / "They said don't test it here. So I did."

**PROMPT:**
9:16 vertical extended-arm selfie video, wide FOV, her foreshortened arm anchored in the bottom corner of frame. A {{TALENT}} sits cross-legged on the wing of a commercial airplane in flight — endless cloud deck and deep blue sky behind. 0–4s: she remains tack-sharp and body-stable while the wing and horizon drift and slowly roll about 10 degrees behind her; hair and clothing whip violently in the wind as she calmly says "{{HOOK_LINE}}" with dead-calm eye contact. 4–6s: she casually {{PRODUCT_ACTION}} with the {{PRODUCT_VISUAL}} as if at home, {{TONE}}. 6–8s: she holds the {{PRODUCT_NAME}} to lens, label sharp, clouds bokeh'd. 8–9s: smirk, "{{CTA_LINE}}". OST "{{OST}}" at 0.3s. One continuous shot; roaring wind ducked under crisp dialogue.

---

## H7. GOLDEN-HOUR CRASH-FLOP (hooks/6b1698c1 — lawn pajamas)
**Mechanic:** Subject-driven crash-in: she tumbles from tiny-in-background to big-in-foreground in one second.
**VISUAL HOOK (0–4s):** Locked ground-level camera, heavy golden backlight flare striping the lens. 0–0.7s: she enters small, full-body, walking from the background. 0.7–1.5s: theatrical forward tumble/flop onto the pavers with hair-whip motion blur — landing seated MUCH closer to the lens, so subject scale jumps without any camera move. 1.5–2.5s: hair settles through the flare as she straightens up. ~3s: one punch-in jump-cut to waist-up as she produces the product into the sunbeam.
**Hook lines:** "That's it. I'm not moving until you hear this." / "This product ended me. Respectfully."

**PROMPT:**
9:16 vertical video, locked static camera at ground level on a {{SETTING}} lawn/terrace at golden hour, heavy lens flare streaking the frame. 0–0.7s: a {{TALENT}} in relaxed loungewear walks into frame from the background, small and full-body. 0.7–1.5s: she performs a theatrical forward tumble onto the stone pavers with hair-whip motion blur, landing seated much closer to the lens — her scale jumping in frame with zero camera movement — saying "{{HOOK_LINE}}" as she lands. 1.5–2.5s: hair settles through the backlight flare. At 3s one punch-in jump-cut to waist-up: she pulls out a {{PRODUCT_VISUAL}} and holds it in the sunbeam. 4–7s: seated {{PRODUCT_ACTION}} in {{TONE}}, flare sweeping the lens. 7–9s: macro push of product at lips/hand height, "{{CTA_LINE}}", OST "{{OST}}" at 0.5s. Evening ambience.

---

## H8. PRODUCT WHIP-WIPE CATCH (hooks/81a3aed0 — drink pouch)
**Mechanic:** The product itself crosses the lens as a full-frame motion-blur wipe, then lands in her palm.
**VISUAL HOOK (0–4s):** Handheld selfie medium shot. 0–1s: she talks normally. At ~1.2s the product whips across the frame inches from the lens — 3–4 frames of full-frame motion blur that wipe the entire image — and lands smack in her raised palm on the far side, an in-camera transition with no cut. A small reactive crash-zoom/settle as she catches it. By 2s: label rotated to lens, eyebrows up. Focus snaps onto the product.
**Hook lines:** "Catch. Now listen." / "It literally found me."

**PROMPT:**
9:16 vertical handheld selfie video in a bright {{SETTING}}. 0–1s: a {{TALENT}} talks casually to camera: "{{HOOK_LINE}}". At 1.2s a {{PRODUCT_VISUAL}} whips across the frame inches from the lens — full-frame motion blur wiping the image for a few frames like an in-camera transition — and lands smack into her raised palm on the other side of frame, with a small reactive crash-zoom settle as she catches it; no cut. 2–4s: she rotates the {{PRODUCT_NAME}} label-to-lens, focus snapping onto it, eyebrows raised, {{TONE}}. 4–7s: {{PRODUCT_ACTION}} with a satisfied reaction. 7–9s: product beside her face, "{{CTA_LINE}}", OST "{{OST}}" at 0.3s. One continuous shot, soft whoosh-thwap SFX under room tone.

---

## H9. WALK-CAM WHIP-PAN STREET STOP (hooks/868ca5a9 — racing jacket)
**Mechanic:** POV walking bounce → violent whip pan → backward-tracking walk-and-talk.
**VISUAL HOOK (0–4s):** True POV walk-cam with natural step bounce, following pedestrians down a sunny sidewalk. At ~1.2s: a violent whip-pan right — 2–3 fully motion-blurred frames streaking across parked cars — lands on the talent mid-reaction as he shields his eyes and lights up at the camera. 2–4s: the camera tracks BACKWARD as he walks toward it, framing tightening from full-body to chest-up, footstep bob throughout, sun flare kicking across the lens and reflections in his sunglasses.
**Hook lines:** "Yo wait, you need to see this." / "Stopped me mid-walk — fine, it's worth it."

**PROMPT:**
9:16 vertical POV video walking down a sunny {{SETTING}} sidewalk with natural step bounce, pedestrians and palm shadows ahead. At 1.2s the camera whip-pans right — several fully motion-blurred frames streaking across parked cars — landing on a {{TALENT}} who shields his eyes from the sun, spots the camera and lights up: "{{HOOK_LINE}}". 2–5s: the camera tracks backward as he walks toward it, framing tightening from full-body to chest-up with footstep bob, while he pitches the {{PRODUCT_VISUAL}} he pulls from his jacket, {{TONE}}; lens flare and sunglass reflections. 5–8s: he stops, holds the {{PRODUCT_NAME}} to the lens, street bustle behind, {{PRODUCT_ACTION}}. 8–9s: points at camera, "{{CTA_LINE}}". OST "{{OST}}" at 0.5s. Continuous shot, real street audio.

---

## H10. MIC-IN-FRAME STREET INTERVIEW + JUMP-CUT SUBJECTS (hooks/913b0ed2 — umbrellas)
**Mechanic:** Interviewer's mic hand anchors the foreground; hard jump-cuts between interviewees keep resetting attention.
**VISUAL HOOK (0–4s):** Interviewer-POV handheld at eye height. The interviewer's arm holding a tiny mic enters from bottom-frame as a constant foreground anchor. Subject #1 stands under an umbrella whose canopy caps the top of frame — a natural vignette. Slight push-in as she reacts to the question and answers. At ~3.5s: HARD CUT to subject #2 framed over-the-shoulder from behind (different umbrella/parasol, different storefront), who turns around to answer — the cut rhythm and repeated mic anchor are the hook.
**Hook lines:** Interviewer: "{{HOOK_QUESTION e.g. What's the one thing you can't live without?}}" Talent: "Easy. This."

**PROMPT:**
9:16 vertical street-interview video, interviewer-POV handheld at eye height on a {{SETTING}} sidewalk, overcast soft light; the interviewer's arm holding a small black mic enters from bottom-frame as a constant foreground anchor. 0–2s: a {{TALENT}} stands under a {{DISTINCT_PROP e.g. umbrella/parasol}} whose canopy caps the top of frame like a vignette; interviewer voice asks "{{HOOK_QUESTION}}"; slight push-in as she smiles surprised. 2–3.5s: she answers "{{HOOK_LINE}}" and raises the {{PRODUCT_VISUAL}}. At 3.5s a hard jump-cut: a second {{TALENT_2}} framed over-the-shoulder from behind under a different canopy turns around to the mic and adds a one-line endorsement. 5–8s: cut back to subject one demoing {{PRODUCT_ACTION}} into the mic, {{TONE}}, passersby blurred. 8–9s: lean into mic, "{{CTA_LINE}}". OST "{{OST}}" at 0.6s. Mic-proximity audio shift on each cut.

---

## H11. TRAIN-ROOF SPEED PARALLAX (hooks/a12f2040 — energy can)
**Mechanic:** Subject tack-sharp, world streaking — speed sells the frame before a word is spoken.
**VISUAL HOOK (0–4s):** Extended-arm selfie rig on a moving train roof: she is stable and sharp while golden fields streak laterally at speed behind her — hard parallax; catenary wires whip overhead frame to frame; hair violently wind-blown; horizon banks gently on curves. At ~1.5s she lifts the product into frame from below; camera rotates a few degrees to hold face + product in a two-shot. No cuts.
**Hook lines:** "This is the only place quiet enough to tell you." / "Worth climbing up here for."

**PROMPT:**
9:16 vertical extended-arm selfie video: a {{TALENT}} sits on the corrugated roof of a moving train through golden {{SETTING}} countryside at dusk. 0–1.5s: she is tack-sharp and rig-stable while fields streak laterally behind her with hard parallax, catenary wires whipping overhead frame to frame, hair violent in the wind, horizon banking gently on a curve; she steadies and says "{{HOOK_LINE}}". 1.5–4s: she lifts the {{PRODUCT_VISUAL}} into frame from below; the camera rotates slightly to hold face and product in a two-shot, label catching the last sun. 4–7s: {{PRODUCT_ACTION}} with a relieved exhale, landscape rushing. 7–9s: product-toast to camera, "{{CTA_LINE}}". OST "{{OST}}" at 0.4s. Continuous shot, rhythmic track clatter under dialogue.

---

## H12. FORCED-PERSPECTIVE THRUST + RAINING PROPS (hooks/b46b6584 — lollipop)
**Mechanic:** Product already AT the lens in frame one; background chaos escalates around a deadpan face.
**VISUAL HOOK (0–4s):** Frame one opens with the product ALREADY thrust at the lens — forced perspective, product razor-sharp, her face two feet behind in soft focus (DOF locked on foreground the entire time). From ~1s, duplicate products/candy packs are thrown through fore- and background with motion blur; one nearly clips the lens. She sweeps her forearm flat over the product like a shelf, product never moving. A barely perceptible 5% dolly-in across 4s. Deadpan throughout — chaos vs stillness.
**Hook lines:** "You're going to want to catch one." / "It's raining {{PRODUCT_CATEGORY}}. Stay focused."

**PROMPT:**
9:16 vertical video in a bright {{SETTING}} supermarket aisle, fluorescent light. Frame one opens with a {{PRODUCT_VISUAL}} already thrust at the lens — forced perspective, product razor-sharp filling the foreground, the {{TALENT}}'s face two feet behind in soft focus; depth of field stays locked on the product for the whole shot. She says "{{HOOK_LINE}}" deadpan. From 1s, duplicate {{PRODUCT_NAME}} units and packets fly through foreground and background with motion blur, bouncing off shelves; one nearly clips the lens. 2–4s: she sweeps her forearm flat above the product like a shelf, product perfectly still; an almost imperceptible 5% dolly-in. 4–7s: she swats a falling unit aside mid-sentence, {{TONE}}, then {{PRODUCT_ACTION}}. 7–9s: arms spread as products keep raining, "{{CTA_LINE}}". OST "{{OST}}" at 0.5s. Comedic thuds under aisle ambience.

---

## H13. DESKTOP UFO BEAM (hooks/b6a67cd5 — cow abduction)
**Mechanic:** Practical-VFX absurdity: a palm-sized UFO levitates something on the desk while the talent reacts.
**VISUAL HOOK (0–4s):** Handheld selfie with micro-jitter at a cluttered desk. Behind/left of him, a palm-sized chrome UFO hovers with a bright volumetric light-beam cylinder onto the desk; a tiny object levitates and slowly rotates inside the beam. The beam glow flickers, casting real light on his face and the desk (practical-VFX feel). His beats: shocked open mouth (0–1.5s) → pointing at the beam (1.5–3s) → thumbs-up to camera (3–4s), with small handheld reframes between beats. Push slightly toward the beam at ~3s.
**Hook lines:** "They're trying to steal my {{PRODUCT_NAME}}." / "Bro. It chose mine."

**PROMPT:**
9:16 vertical handheld selfie video with natural micro-jitter at a cluttered {{SETTING}} desk by a window. Behind the {{TALENT}}, a palm-sized chrome UFO hovers over the desk projecting a bright volumetric light-beam cylinder; inside it a {{PRODUCT_VISUAL}} levitates and slowly rotates. The beam's glow flickers, casting believable light on his face and the desktop. 0–1.5s: shocked open-mouth reaction: "{{HOOK_LINE}}". 1.5–3s: he points at the beam, small handheld reframes, {{TONE}} narration. 3–4s: thumbs-up to camera as the camera pushes slightly toward the beam. 5–7s: he snatches the {{PRODUCT_NAME}} out of the beam — the UFO wobbles off annoyed — and holds it to the lens. 7–9s: deadpan "{{PRODUCT_ACTION}} — {{CTA_LINE}}". OST "{{OST}}" at 0.4s. Soft sci-fi hum + room tone.

---

## H14. JUMP-CUT BED TESTIMONIAL (hooks/d5a34b0a — activewear)
**Mechanic:** No gimmick — trust. The hook is jump-cut rhythm inside an identical locked frame.
**VISUAL HOOK (0–4s):** Locked-off camera propped at the foot of the bed, soft window light, framing never changes. Three micro jump-cuts in the first 4s with her pose changing between each: (1) looking down adjusting the product/waistband, (2) hands settling, chin up, first eye contact, (3) leaning slightly forward delivering the first line. Identical background across cuts makes the pose-pops feel snappy.
**Hook lines:** "I've worn this every day for 3 weeks. Here's the truth." / "Nobody paid me to say this. Unfortunately."

**PROMPT:**
9:16 vertical video, locked-off phone propped at the foot of a bed in a bright airy {{SETTING}} bedroom, soft morning light through sheer curtains; the framing never changes. A {{TALENT}} wearing/holding the {{PRODUCT_VISUAL}} sits on the bed. 0–4s: three snappy jump-cuts in the same frame, pose popping between each — looking down adjusting the product, hands settling with chin up and first eye contact, then leaning forward to deliver "{{HOOK_LINE}}". 4–6.5s: unhurried honest review in {{TONE}}, touching the exact product details as she names them. 6.5–8s: she shifts to show fit / does {{PRODUCT_ACTION}}, one more jump-cut. 8–9s: soft direct "{{CTA_LINE}}". OST "{{OST}}" at 1s. Cozy room tone, no music until 4s.

---

## H15. COUNTER SLIDE + REACH-THROUGH-LENS (hooks/e106fdf3 — bottle)
**Mechanic:** Product skids across the counter toward the viewer, then a hand reaches through the frame.
**VISUAL HOOK (0–4s):** Static camera at counter level. 0–0.5s: she stands at the island holding the product. 0.5–1.5s: she slaps it down and slides it hard across the marble TOWARD the lens — it skids with motion blur and a splash of water off the stone, coming to rest large in the foreground. 1.5–3s: she reaches forward THROUGH the frame — hand foreshortened, fingers defocusing at the lens as if handing it to the viewer — saying the hook line. By 4s: bottle retrieved, label locked to camera.
**Hook lines:** "Here. Just try it." / "Stop scrolling. Drink water. This one."

**PROMPT:**
9:16 vertical video, static camera at counter level across a stone kitchen island in a minimal {{SETTING}}, soft daylight. 0–0.5s: a {{TALENT}} stands at the island holding a {{PRODUCT_VISUAL}}. 0.5–1.5s: she slaps it down and slides it hard across the marble toward the lens — skidding with motion blur and a splash of water off the stone — coming to rest large in the foreground. 1.5–3s: she reaches through the frame, hand foreshortened and defocusing at the lens as if offering it to the viewer: "{{HOOK_LINE}}". 3–5s: she retrieves it, opens it and {{PRODUCT_ACTION}}, eyes closed, savoring, {{TONE}}. 5–8s: sets it down label-to-lens, taps it twice, one-line benefit. 8–9s: second reach toward the lens with the product, "{{CTA_LINE}}". OST "{{OST}}" at 0.4s. ASMR-leaning audio: skid, splash, cap click.

---

## H16. SUNROOF NEAR-MISS TRUCK PASS (hooks/eeddac4e — desert gum)
**Mechanic:** Kinetic jolt: a semi-truck blasts past feet behind her in the first second.
**VISUAL HOOK (0–4s):** Extended-arm selfie rig from a car sunroof at sunset — she's stable, road streaking beneath, hard golden rim light. At ~0.8s a semi-truck blasts past in the opposite lane only feet behind her with a whoosh — the frame shudders slightly and her hair blasts sideways: the near-miss is the jolt. The product lies on the car roof in the foreground, sliding a few centimeters with the car's motion. ~2.5s: she plucks it off the roof and raises it to the lens, full flare behind.
**Hook lines:** "Road rule #1: never leave without this." / "Almost died. Anyway—"

**PROMPT:**
9:16 vertical extended-arm selfie video: a {{TALENT}} stands up through the sunroof of a car rolling down an empty desert {{SETTING}} highway at sunset, hard golden rim light, road streaking beneath, a {{PRODUCT_VISUAL}} lying on the car roof in the foreground sliding a few centimeters with the motion. At 0.8s a semi-truck blasts past in the opposite lane only feet behind her — whoosh, slight frame shudder, hair blasting sideways — as she turns to the lens: "{{HOOK_LINE}}". 2.5–4s: she plucks the {{PRODUCT_NAME}} off the roof and raises it against the sunset. 4–7s: macro-feel insert of hands opening/unwrapping it over the blurred asphalt, then back up to {{PRODUCT_ACTION}} with a grin, {{TONE}}. 7–9s: leaning on the roof, product beside face, "{{CTA_LINE}}". OST "{{OST}}" at 0.4s. Wind + tire hum + truck whoosh ducked under dialogue, golden flare.

---

# PART B — THE 18 SCENE TEMPLATES (from ref videos/), HOOK-LED
Each includes a one-line visual hook (0–1.5s camera/effect) consistent with the reference previews.

## S1. Product Zoom & Motion-Background Shift
**Visual hook:** locked static product shot — the product silently levitates off the counter in second one; background then whip-dissolves.
9:16 video: a {{PRODUCT_VISUAL}} sits on a {{SETTING}} kitchen counter beside fresh {{INGREDIENT_PROPS}}, static camera. 0–1s: it hovers smoothly upward — OST "{{OST}}" snaps in. 1–4s: the background whip-dissolves into an abstract high-energy 3D motion-graphics world in {{BRAND_COLORS}}. 4–8s: photorealistic {{INGREDIENT_PROPS}} orbit the floating product, camera slowly circling. 8–10s: elements snap into a locked hero end-frame with {{PRODUCT_NAME}} logo. Whoosh-driven sound design.

## S2. Drone Light Show Brand Reveal
**Visual hook:** first-person gasp + fast tilt-up from street level to sky.
9:16 POV at night over a {{CITY_SKYLINE}}. 0–1.5s: audible gasp, fast tilt-up — thousands of glowing drones ripple into formation. 1.5–6s: drones morph from a beating heart into an animated {{BRAND_MASCOT}}. 6–10s: drones lock to spell "{{BRAND_NAME}}" in {{BRAND_COLORS}} neon; crowd cheers below. OST "{{OST}}" at 1s.

## S3. FPV Product Fly-Through
**Visual hook:** the product rockets past the lens in frame one; camera gives chase.
9:16 FPV-drone video: 0–1s: a {{PRODUCT_VISUAL}} blasts past camera on a sunny balcony — camera whips after it. 1–7s: seamless high-speed pursuit down a {{STREET/BEACH/MARKET}}, weaving through crowds, product centered. 7–9s: crash-zoom through a {{CENTRAL_GRAPHIC}}; product lands on a {{TABLE_SURFACE}} beside {{CONTEXT_PROP}} at sunset. 9–10s: settle on label. Whoosh SFX.

## S4. Screen-Share UGC App Preview
**Visual hook:** talent's face → fast whip-down to the device on the table.
9:16 UGC video: 0–1.5s: an enthusiastic {{TALENT}} says "{{HOOK_LINE}}", then the phone whips down to a {{DEVICE}} on the table with motion blur. 1.5–7s: finger drives the live {{APP_NAME}} interface — smooth animations of {{KEY_FEATURE}}. 7–10s: whip back up to their sold face: "{{CTA_LINE}}". OST "{{OST}}" at 0.3s.

## S5. Cinematic Lifestyle Montage
**Visual hook:** hard-cut burst of close-up laughter in second one.
9:16 montage: 0–1s: close-up burst of friends laughing in a {{SETTING}}. 1–6s: rapid warm clips — {{TALENT}} group sharing phones, golden-hour candids. 6–8s: transition to a {{DEVICE}} scrolling the {{APP/BRAND}} feed. 8–10s: minimalist white end-card: {{BRAND_LOGO}} + "{{TAGLINE}}".

## S6. Urban Stealth Chase (comedic)
**Visual hook:** POV grip on the product + whip-around reveal of pursuers.
9:16 POV: 0–1.5s: looking down at your hand gripping a {{PRODUCT_VISUAL}}, fast breathing — whip-around with blur reveals a {{TARGET_DEMOGRAPHIC_GROUP}} sprinting after you. 1.5–7s: comedic flight down an urban path, camera bouncing. 7–10s: vault behind cover, product to lens: "{{CTA_LINE}}". OST "{{OST}}" at 0.5s.

## S7. Top-Down Tactical ASMR Unboxing
**Visual hook:** two sharp rhythmic taps on the box, top-down, dead-static frame.
9:16 top-down flat-lay on {{SURFACE}}: 0–1.5s: two hands tap-tap the {{BRAND_STYLE}} box — crisp ASMR. 1.5–6s: lid lifts, {{TISSUE_COLOR}} tissue crinkles, hands extract the {{PRODUCT_VISUAL}} deliberately. 6–10s: product raised slowly to camera, label filling frame. OST "{{OST}}" at 2s.

## S8. Casual Couch UGC Unboxing
**Visual hook:** flap ripped open on the first word.
9:16 medium shot: a {{TALENT}} on a {{SETTING}} sofa, shipping box in lap. 0–1.5s: "{{HOOK_LINE}}" while ripping the flap. 1.5–6s: pulls out the {{PRODUCT_VISUAL}}, genuine delight, reads the label. 6–10s: direct-to-camera mini-review, {{TONE}}, product beside face, "{{CTA_LINE}}".

## S9. Split-Screen Fitness App
**Visual hook:** sweaty close-up + "Day 30. Look." with split-screen snapping in.
9:16 split-screen: left = {{TALENT}} with the {{APP_NAME}} dashboard; right = fast workout montage of {{EXERCISE_TYPE}}. 0–1.5s: hook line, split snaps in. 1.5–7s: quick cuts + smartwatch metrics updating live. 7–10s: water sip, wipe to {{BRAND_LOGO}} end-card.

## S10. Whiteboard Expert Pitch
**Visual hook:** marker slams a circle around the top pain point.
9:16 medium close-up: an energetic {{EXPERT_PERSONA}} beside a whiteboard listing {{PAIN_POINTS}}. 0–1.5s: marker slams a circle around the top one: "{{HOOK_LINE}}". 1.5–6s: rapid walkthrough, wipes one myth off the board. 6–9s: pulls the physical {{PRODUCT_VISUAL}} into frame, macro on texture. 9–10s: point at lens, "{{CTA_LINE}}". OST "{{OST}}" at 0.5s.

## S11. Watch-Party Tension
**Visual hook:** frozen faces and dead silence for two full seconds — then eruption.
9:16: friends packed on a couch, frozen mid-suspense at an off-screen {{EVENT_TYPE}}. 0–2s: silence; one {{TALENT}} slowly raises a {{PRODUCT_ITEM}} to their mouth. 2–4s: eruption — jumping, popcorn flying. 4–8s: camera pans down sharply to the branded {{PRODUCT_VISUAL}} perfectly lit on the table amid chaos. 8–10s: slow push-in on label, crowd fading. OST "{{OST}}".

## S12. Skydive Product Test
**Visual hook:** unexplained freefall POV, wind roar, camera shake.
9:16 wide POV: freefall over clouds and {{LANDSCAPE}}. 0–1.5s: wind roar, shake — OST "{{OST}}". 1.5–6s: skydiver extracts a {{PRODUCT_VISUAL}} from a utility belt and calmly {{PRODUCT_ACTION}} mid-air. 6–10s: parachute snaps open — sudden quiet — product held against blue sky: "{{CTA_LINE}}".

## S13. Popularity Crowd Run
**Visual hook:** backward-tracking POV; a joyful mob sprints at the lens after the product in your outstretched hand.
9:16 first-person POV moving backward fast down a {{CITY_SIDEWALK}}: 0–1.5s: your hand extends holding a {{PRODUCT_VISUAL}}; a smiling crowd of {{TARGET_DEMOGRAPHIC_GROUP}} sprints after it, arms out, camera bobbing with the run. 1.5–7s: sustained backward run, crowd growing, hands nearly grabbing it. 7–10s: round a corner, hug the product: "{{CTA_LINE}}". OST "{{OST}}" at 0.5s.

## S14. Roller-Coaster App Stress Test
**Visual hook:** the click-click-click of the lift hill + white-knuckle phone grip.
9:16 close tracking: a {{TALENT}} strapped into a coaster climbing the lift hill holding a {{DEVICE}} steady. 0–2s: clicks, nervous grin: "{{HOOK_LINE}}". 2–7s: the plunge — thrilled screams intercut with a clean screen-record of {{APP_NAME}} completing {{APP_ACTION}} mid-loop. 7–10s: pull-in, hair wrecked, phone raised: "{{CTA_LINE}}".

## S15. Skydive Notification
**Visual hook:** phone pulled out at terminal velocity.
9:16 freefall POV toward earth. 0–1.5s: rugged phone into frame against roaring wind. 1.5–5s: premium notification animates: {{APP_NAME}} — "{{CUSTOM_ALERT_TEXT}}". 5–8s: thumbs-up, cord pull, jolt to silence. 8–10s: phone steady over a scenic vista, notification glowing. OST mirrors the alert.

## S16. 3D Mascot Sports Animation
**Visual hook:** the product has limbs and nutmegs a defender in second one.
9:16 cinematic stadium under floodlights: an animated {{PRODUCT_VISUAL}} character dribbles a {{SPORT_BALL}} past realistic defenders. 0–1.5s: nutmeg — crowd roar. 1.5–7s: end-to-end run, low tracking camera. 7–10s: spectacular goal, winning pose, duplicates land symmetrically, {{BRAND_LOGO}} on the jumbotron.

## S17. Vanity Glamour Unboxing
**Visual hook:** macro gold-embossed box sliding open, ASMR-quiet.
9:16 macro at an elegant {{SETTING}} vanity, warm glow. 0–2s: fingertips slide open a gold-embossed {{PRODUCT_BOX}} — soft ASMR. 2–6s: luxury {{PRODUCT_VISUAL}} lifted in slow macro, catching light. 6–9s: gentle wrist application, liquid texture glinting, hushed "{{HOOK_LINE}}". 9–10s: product set beside box, label forward. OST "{{OST}}" at 3s, serif.

## S18. Surf Barrel Demo
**Visual hook:** inside a collapsing turquoise barrel, camera-stick POV.
9:16 inside the barrel of a massive turquoise wave: a pro surfer films selfie-stick style. 0–1.5s: wave thunders overhead — OST "{{OST}}". 1.5–6s: mid-ride they extract a waterproof {{PRODUCT_VISUAL}} from their sleeve and {{PRODUCT_ACTION}}. 6–10s: shoot out into sunlight, product to lens, spray backlit: "{{CTA_LINE}}".

---

## 3. USAGE CHECKLIST
1. Pick a template (H = talent-led visual hooks, S = concept scenes).
2. Fill `{{PRODUCT_VISUAL}}` forensically from product photos/URL — locks product consistency in Omni Flash.
3. Apply ONE demographic preset row (talent + setting + tone + hook language). Change nothing else — the VISUAL HOOK camera grammar is untouchable.
4. Keep the visual hook inside 0–1.5s, spoken hook inside 0–1.5s, OST inside 0.5s.
5. Nano Banana → Omni Flash pipeline: generate the 6-panel storyboard first (`storyboard_prompt_template.md`), then pass this prompt + storyboard as reference.
