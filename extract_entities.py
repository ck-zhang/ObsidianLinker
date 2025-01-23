import os
import sys
import json
import re
import torch
from pathlib import Path
from transformers import pipeline
import argparse

NER_MODEL_NAME = "Jean-Baptiste/roberta-large-ner-english"
VALID_EXTENSIONS = [".md"]


def get_ner_pipeline():
    return pipeline(
        "ner",
        model=NER_MODEL_NAME,
        tokenizer=NER_MODEL_NAME,
        aggregation_strategy="simple",
        device=0 if torch.cuda.is_available() else -1,
    )


def remove_links(text):
    return re.sub(r"\[\[.*?\]\]", lambda m: " " * (m.end() - m.start()), text)


def extract_all_entities(notes_folder, output_json):

    print("PROGRESS:0", flush=True)

    if os.path.exists(output_json):
        os.remove(output_json)

    ner_pipeline = get_ner_pipeline()

    notes_folder = Path(notes_folder)
    files = [
        p
        for p in notes_folder.rglob("*")
        if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
    ]
    total_files = len(files)
    batch_size = 8

    print("PROGRESS:0", flush=True)
    entity_scores = {}

    for batch_idx in range(0, total_files, batch_size):
        batch_files = files[batch_idx : batch_idx + batch_size]
        batch_texts = []
        file_paths = []

        for fp in batch_files:
            with open(fp, "r", encoding="utf-8") as f:
                batch_texts.append(f.read())
            file_paths.append(str(fp))

        clean_texts = [remove_links(text) for text in batch_texts]
        ner_results = ner_pipeline(clean_texts, batch_size=batch_size)

        for i, text in enumerate(clean_texts):
            for entity in ner_results[i]:
                start = int(entity["start"])
                end = int(entity["end"])
                word = text[start:end]
                normalized_word = word.strip().lower()
                key = (entity["entity_group"], normalized_word)

                if key not in entity_scores:
                    entity_scores[key] = {
                        "entity_group": entity["entity_group"],
                        "word": word.strip(),
                        "normalized_word": normalized_word,
                        "score": 0.0,
                        "occurrences": [],
                    }

                entity_scores[key]["score"] += float(entity["score"])
                entity_scores[key]["occurrences"].append(
                    {"file": file_paths[i], "start": start, "end": end, "word": word}
                )

        processed_files = min(batch_idx + batch_size, total_files)
        progress = int((processed_files / total_files) * 100)
        print(f"PROGRESS:{progress}", flush=True)

    aggregated_entities = sorted(
        entity_scores.values(), key=lambda x: x["score"], reverse=True
    )
    output_data = {
        "entities": aggregated_entities,
        "processed_files": [str(f) for f in files],
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("PROGRESS:100", flush=True)
    return aggregated_entities


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes_folder", required=True)
    parser.add_argument("--output_json", required=True)
    args = parser.parse_args()
    extract_all_entities(args.notes_folder, args.output_json)
    print(f"Saved aggregated entities to {args.output_json}")
