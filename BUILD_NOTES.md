# Place Blend Maker Build 2.1 — Clean Local Travel Art

## Fixed
- Removed the unstable optimisation-based texture transfer that produced coloured grain and faded detail.
- Added a clean reference-guided illustration renderer using edge-preserving smoothing, restrained stylisation, LAB palette matching, poster colour blocks, warm ink edges and detail recovery.
- Buildings, trams, coastlines and signs remain much clearer.
- The same renderer, reference palette and preset are applied to every source image for consistency.
- Removed the large PyTorch and torchvision dependencies.

## Important limitation
This is local restyling, not generative image creation. It preserves the original photo composition and does not invent a new fantasy arrangement of landmarks.
