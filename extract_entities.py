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


class NotesDataset:
    def __init__(self, files):
        self.files = files
        self.texts = []
        for fp in self.files:
            with open(fp, "r", encoding="utf-8") as f:
                self.texts.append(f.read())

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        return self.texts[idx]


def get_ner_pipeline():
    return pipeline(
        "ner",
        model=NER_MODEL_NAME,
        tokenizer=NER_MODEL_NAME,
        aggregation_strategy="simple",
        device=0 if torch.cuda.is_available() else -1,
    )


def remove_links(text):
    return re.sub(r"\[\[(.*?)\]\]", r"\1", text)


def find_largest_safe_batch_size(ner_pipe, dataset, start_bs=32):
    test_texts = dataset.texts[: min(64, len(dataset))]
    bs = start_bs
    while bs > 0:
        try:
            _ = ner_pipe(test_texts, batch_size=bs)
            return bs
        except RuntimeError as e:
            if "CUDA" in str(e) or "out of memory" in str(e).lower():
                bs //= 2
            else:
                raise e
    return 1


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
    dataset = NotesDataset(files)
    best_batch_size = find_largest_safe_batch_size(ner_pipeline, dataset)

    entity_scores = {}
    for batch_start_idx in range(0, total_files, best_batch_size):
        batch_end_idx = min(batch_start_idx + best_batch_size, total_files)
        batch_texts = [
            remove_links(dataset.texts[i])
            for i in range(batch_start_idx, batch_end_idx)
        ]
        ner_results = ner_pipeline(batch_texts, batch_size=best_batch_size)

        for i, text in enumerate(batch_texts):
            file_path = str(files[batch_start_idx + i])
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
                    {"file": file_path, "start": start, "end": end, "word": word}
                )
        progress = int(((batch_end_idx) / total_files) * 100)
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
