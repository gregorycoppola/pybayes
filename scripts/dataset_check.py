"""Check which datasets load cleanly."""

from datasets import load_dataset

datasets_to_try = [
    ("tasksource/ruletaker", {}),
    ("lighteval/logiqa", {}),
    ("alisawuffles/WANLI", {}),
]

for name, kwargs in datasets_to_try:
    try:
        ds = load_dataset(name, split="train", streaming=True, **kwargs)
        example = next(iter(ds))
        print(f"✓ {name}")
        print(f"  Keys: {list(example.keys())}")
        print()
    except Exception as e:
        print(f"✗ {name}: {e}")
        print()