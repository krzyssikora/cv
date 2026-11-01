"""Build the CV from content/cv.yaml.

dist/          public web pages and PDFs, without private details
private-pdfs/  PDFs with address and phone, built only if content/private.yaml exists
"""

import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
PRIVATE_PDFS = ROOT / "private-pdfs"
PRIVATE_CONTENT = ROOT / "content" / "private.yaml"
LANGUAGES = ("en", "pl")


def localize(node, lang, path="cv"):
    """Replace every {en: ..., pl: ...} pair with the text for `lang`."""
    if isinstance(node, dict):
        if set(node) & set(LANGUAGES):
            missing = [code for code in LANGUAGES if not node.get(code)]
            if missing:
                raise ValueError(f"{path}: missing translation for {', '.join(missing)}")
            extra = set(node) - set(LANGUAGES)
            if extra:
                raise ValueError(f"{path}: unexpected {sorted(extra)}. Does the text need quotes around a comma?")
            return node[lang]
        return {key: localize(value, lang, f"{path}.{key}") for key, value in node.items()}
    if isinstance(node, list):
        return [localize(value, lang, f"{path}[{i}]") for i, value in enumerate(node)]
    return node


def sections_for(data, variant_name):
    """Return the variant's sections in order, keeping only the items meant for it."""
    sections = []
    for name in data["variants"][variant_name]["sections"]:
        section = dict(data["sections"][name])
        section["items"] = [
            item for item in section["items"] if "only" not in item or variant_name in item["only"]
        ]
        sections.append(section)
    return sections


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def print_pdf(page, html, source_dir, pdf_path):
    # Printed from a temporary page next to the web page, so the asset links resolve.
    source = source_dir / "_pdf.html"
    source.write_text(html, encoding="utf-8")
    try:
        page.goto(source.as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True, tagged=True)
    finally:
        source.unlink()
    print(f"Built {pdf_path.relative_to(ROOT)}")


def build():
    content = load_yaml(ROOT / "content" / "cv.yaml")
    private = load_yaml(PRIVATE_CONTENT) if PRIVATE_CONTENT.exists() else None
    template = Environment(
        loader=FileSystemLoader(ROOT / "templates"), autoescape=True
    ).get_template("cv.html.j2")

    # Stop if old output can't be removed: a stale PDF could hold private details.
    for folder in (DIST, PRIVATE_PDFS):
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except PermissionError as error:
                raise SystemExit(f"Could not clear {folder.name}/. Close any open PDF from it and try again.\n{error}")
    shutil.copytree(ROOT / "assets", DIST / "assets")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        for variant_name in content["variants"]:
            for lang in LANGUAGES:
                data = localize(content, lang)
                pdf_name = f"Krzysztof-Sikora-CV-{lang}.pdf"
                context = {
                    "lang": lang,
                    "other_lang": next(code for code in LANGUAGES if code != lang),
                    "asset_root": "../../assets",
                    "person": data["person"],
                    "labels": data["labels"],
                    "variant_name": variant_name,
                    "variant": data["variants"][variant_name],
                    "sections": sections_for(data, variant_name),
                    "pdf_name": pdf_name,
                    "consent": data["consent_pl"] if lang == "pl" else None,
                }
                out_dir = DIST / lang / variant_name
                out_dir.mkdir(parents=True)
                (out_dir / "index.html").write_text(template.render(**context, for_pdf=False), encoding="utf-8")
                print_pdf(page, template.render(**context, for_pdf=True), out_dir, out_dir / pdf_name)

                if private:
                    details = localize(private, lang)
                    private_context = {
                        **context,
                        "person": {**data["person"], **details["person"]},
                    }
                    if lang == "pl":
                        private_context["consent"] = details["consent_pl"].get(variant_name, context["consent"])
                    print_pdf(
                        page,
                        template.render(**private_context, for_pdf=True),
                        out_dir,
                        PRIVATE_PDFS / lang / variant_name / pdf_name,
                    )
        browser.close()

    target = f"{LANGUAGES[0]}/{content['default_variant']}/"
    (DIST / "index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={target}">'
        f'<title>Krzysztof Sikora CV</title><a href="{target}">Krzysztof Sikora CV</a>',
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
