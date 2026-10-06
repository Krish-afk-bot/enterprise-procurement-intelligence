# The world layer

The authenticated workspace draws every 3D surface with **one** WebGL canvas.
The canvas lives in `WorldCanvas.tsx` (lazy: it is the only module that pulls in
three.js), is mounted once by `WorldStage.tsx` inside `AppShell`, and is
`position: fixed` over the viewport with `pointer-events: none`. Nothing drawn on
it can block a click.

Regions are rectangles of the page that the canvas draws into using a scissor
box, so 3D is clipped to its own box and can never paint over text. The region
element is a real DOM box; three.js content for it is portalled into its own
scene and camera, which is why one canvas can host several independent surfaces.

| File | Responsibility |
| --- | --- |
| `WorldStage.tsx` | The band of the workspace: its DOM, the effects controls, the fallback layer. Small, and eagerly loaded. |
| `WorldCanvas.tsx` | The single canvas: regions, lights, frame metering, visibility pause. Lazy. |
| `SceneRegion.tsx` | One page-embedded 3D rectangle, drawn by the shared canvas. |
| `BandScene.tsx` | Route-aware registry: which scene the band shows for a given route. |
| `Watcher.tsx` | The one global character: eyes, blinks, saccades, moods. |
| `Courier.tsx` | The walking character, with a suitcase labelled with a real route name. |
| `PaperFlow.tsx` | Instanced translucent sheets on curved paths, reactive to the cursor. |
| `StaticBand.tsx` | The SVG/CSS version of the band for no-WebGL, phones and reduced motion. |

## Rules this layer is built on

1. **One canvas.** A second WebGL context is a bug, not a feature.
2. **Never over content.** Regions are clipped to their own rectangle, and the
   band's rectangle is reserved space in the layout; text, tables, forms,
   citations and controls are never underneath animated geometry.
3. **Decorative means decorative.** Characters are `aria-hidden`. Every setting
   that changes them is a real button. Every entity shown in 3D has a DOM
   equivalent that came from the same API response.
4. **Nothing invented.** Props are symbolic (a folder, a crate, a tag). Only the
   suitcase carries text, and it is a route name that exists in this workspace.
5. **Honest degradation.** No WebGL, a phone, a tab in the background, a slow
   machine and reduced motion each have a defined, tested behaviour.
