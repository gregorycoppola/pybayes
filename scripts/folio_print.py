"""Print FOLIO examples."""

import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=5)
    args = parser.parse_args()
    
    ds = load_dataset("yale-nlp/FOLIO", split="train")
    
    for i, example in enumerate(ds):
        if i >= args.num:
            break
        
        print(f"=== Example {i} ===")
        print(f"Premises:\n{example['premises']}")
        print(f"\nConclusion: {example['conclusion']}")
        print(f"Label: {example['label']}")
        if 'FOL_premises' in example:
            print(f"\nFOL: {example['FOL_premises']}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()