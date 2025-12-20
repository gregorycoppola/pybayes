"""Print WANLI examples."""

import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=5)
    args = parser.parse_args()
    
    ds = load_dataset("alisawuffles/WANLI", split="train", streaming=True)
    
    for i, example in enumerate(ds):
        if i >= args.num:
            break
        
        print(f"=== Example {i} ===")
        print(f"Premise: {example['premise']}")
        print(f"Hypothesis: {example['hypothesis']}")
        print(f"Label: {example['gold']}")
        print(f"Genre: {example['genre']}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()