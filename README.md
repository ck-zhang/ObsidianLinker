# Obsidian Linker

![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)
![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![GitHub stars](https://img.shields.io/github/stars/ck-zhang/ObsidianLinker.svg?style=social)

**Obsidian Linker** Recognize subjects and link notes in your Obsidian vault using named entity recognition so you can focus on the writing

![Demo](https://github.com/user-attachments/assets/e9ae5b91-7cf2-4ac2-814a-aba41d7c46c2)

## Features

- **Named Entity Recognition**: This is the main improvement over existing solutions, Obsidian Linker identifies subject via NER to capture even subjects that are not existing notes
- **Customizable Links**: Offers the flexibility to link with aliases

## Demo

https://github.com/user-attachments/assets/23742b61-d90c-402d-bbb6-1d912256121e

## Installation

```shell
git clone https://github.com/ck-zhang/ObsidianLinker
cd ObsidianLinker
pip install uv
uv sync
```

## Usage

```shell
uv run entity_linker.py
```

## TODO
- [ ] Obsidian Integration
