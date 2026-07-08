# Teddie & Lane Place Blend Maker — Build 2.0

## Local Style Transfer + Consistent Travel Posters

This is a separate Streamlit app. It upgrades Build 1.0 with a **local neural style-transfer engine** that uses an uploaded reference image to restyle every travel photo consistently.

## What creates the style

In **Local neural style transfer** mode:

1. Upload one style-reference image.
2. Upload 2–5 place photographs.
3. The app uses a lightweight pretrained SqueezeNet feature network to transfer visual texture and colour from the reference image to each photo.
4. The same reference, preset, strength and palette matching are used for every place.
5. The styled images are combined into the selected poster layout.

The model runs on the Streamlit server. There is no OpenAI image API, no per-image API charge and no API key.

## Important limitation

The local model keeps the content and layout of each source photograph. It can make the photographs look more painterly and coordinated, but it does **not** invent new landmarks, move buildings into a fantasy scene or reproduce a completely generated collage.

## Included art presets

- Painterly Travel Poster
- Sunny Mediterranean
- Bold Landmark Art
- Soft Painted Photo
- Vintage Travel Postcard

## Included layouts

- Soft blended scene
- Panel collage
- Travel poster
- Postcard
- Scrapbook

## Quality modes

- Draft — fastest: 256 px neural working size, 18 passes
- Balanced — recommended: 320 px, 32 passes
- Detailed — slower: 384 px, 48 passes

The result is enlarged back to the source-photo dimensions before the poster is assembled. Free hosting may be slower in Detailed mode.

## Downloads

- Final poster PNG
- ZIP of every individually styled source image
- Full project ZIP with the final poster, styled images and settings JSON
- 150 or 300 DPI metadata choice

## Deploy as a separate app

1. Create a new GitHub repository.
2. Unzip this build.
3. Upload **all files and folders** to the repository root, including `.streamlit`.
4. In Streamlit Community Cloud, choose **Deploy an app**.
5. Select the repository.
6. Set the entrypoint to `app.py`.

The first neural run downloads the small official SqueezeNet 1.1 checkpoint through torchvision and caches it. A normal internet connection is required for that first model load.

## Add to an existing Teddie & Lane repository later

Copy these files:

- `4_Place_Blend_Maker.py`
- `place_blend_core.py`
- `local_style_transfer.py`

Merge the entries from `requirements.txt` into the existing requirements file. Test separately before adding it to the main launcher because PyTorch uses more memory than the other tools.

## Photo and reference rights

The app does not verify licences. Use source photos and style-reference images you own or are permitted to use, especially when selling the final design.

## Low-memory fallback

Choose **Fast travel-poster finish** when the free server cannot complete the local neural process. That mode still applies the chosen palette, painterly smoothing and poster finish, but it is not neural style transfer.
