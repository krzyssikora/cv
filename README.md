# CV

All content is in `content/cv.yaml`.

## Edit online

Open `content/cv.yaml` on GitHub, click the pencil icon, make the change and commit it. The site rebuilds itself, usually within a couple of minutes.

## Edit locally

```
uv sync
uv run playwright install chromium
uv run python build.py
```

The build writes:

- `dist/`: the public web pages and PDFs, in the form `dist/en/developer/`.
- `private-pdfs/`: PDFs with the address and phone number, for sending directly to someone. These need `content/private.yaml`, which is kept out of this repository.

Push to `main` to publish.

## Versions

The versions are `data-scientist`, `developer` and `educational-analyst`. Each has its own summary and section order in `cv.yaml`. An item with `only: [...]` appears just in the versions listed.
