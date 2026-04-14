from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _escape_embedded_newlines(content: str) -> str:
    result: list[str] = []
    in_quotes = False
    index = 0
    length = len(content)

    while index < length:
        char = content[index]
        next_char = content[index + 1] if index + 1 < length else ""

        if char == '"':
            if not in_quotes:
                in_quotes = True
                result.append('"')
            elif next_char == '"':
                result.append('""')
                index += 2
                continue
            elif next_char in (",", "\n", "\r", ""):
                in_quotes = False
                result.append('"')
            else:
                result.append('""')
        elif char == "\r" and next_char == "\n":
            result.append("\\n" if in_quotes else "\n")
            index += 2
            continue
        elif char == "\n" and in_quotes:
            result.append("\\n")
        else:
            result.append(char)

        index += 1

    return "".join(result)


def preprocess_raw_csvs(
    input_dir: str | Path = "data/raw",
    output_dir: str | Path = "data",
) -> list[Path]:
    source_dir = Path(input_dir)
    target_dir = Path(output_dir)

    if not source_dir.is_absolute():
        source_dir = PROJECT_ROOT / source_dir
    if not target_dir.is_absolute():
        target_dir = PROJECT_ROOT / target_dir

    if not source_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    processed_files: list[Path] = []
    for input_file in sorted(source_dir.glob("*.csv")):
        output_file = target_dir / input_file.name
        with input_file.open("r", encoding="utf-8", newline="") as file_handle:
            content = file_handle.read()

        with output_file.open("w", encoding="utf-8", newline="") as file_handle:
            file_handle.write(_escape_embedded_newlines(content))

        processed_files.append(output_file)

    return processed_files


if __name__ == "__main__":
    for output_file in preprocess_raw_csvs():
        print(f"Done: {output_file.name}")
