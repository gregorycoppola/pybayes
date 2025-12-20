"""Print RuleTaker examples to see the format."""

import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=10)
    parser.add_argument("--split", default="train")
    parser.add_argument("--config", help="filter by config e.g. depth-1")
    args = parser.parse_args()
    
    ds = load_dataset("tasksource/ruletaker", split=args.split)
    
    count = 0
    for example in ds:
        if args.config and example["config"] != args.config:
            continue
        
        print(f"=== Example {count} ({example['config']}) ===")
        print(f"Context:\n{example['context']}")
        print(f"\nQuestion: {example['question']}")
        print(f"Label: {example['label']}")
        print("\n" + "="*50 + "\n")
        
        count += 1
        if count >= args.num:
            break

if __name__ == "__main__":
    main()