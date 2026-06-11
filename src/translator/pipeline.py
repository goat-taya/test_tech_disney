import argparse
from pathlib import Path

from translator.excel import translate_excel
from translator.pdf import translate_pdf
from translator.service import TranslationService
from translator.word import translate_word


SUPPORTED_EXTENSIONS = {
    ".xlsx": translate_excel,
    ".docx": translate_word,
    ".pdf": translate_pdf,
}


def translate_file(
    input_path: str | Path,
    output_dir: str | Path,
    service: TranslationService | None = None,
) -> Path:
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    translator = SUPPORTED_EXTENSIONS.get(input_path.suffix.lower())
    if translator is None:
        raise ValueError(f"Unsupported file type: {input_path.suffix}")

    output_path = output_dir / f"{input_path.stem}_en{input_path.suffix}"
    return translator(input_path, output_path, service=service)


def translate_directory(input_dir: str | Path, output_dir: str | Path) -> list[Path]:
    input_dir = Path(input_dir)
    service = TranslationService()
    translated_files = []
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            translated_files.append(translate_file(path, output_dir, service=service))
    return translated_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate supported business documents.")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("output", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        paths = translate_directory(input_path, args.output)
    else:
        paths = [translate_file(input_path, args.output)]

    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
