"""Print bAbI examples."""

import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=5)
    parser.add_argument("--task", type=int, default=1, help="1-20")
    args = parser.parse_args()
    
    # Use the aeslc mirror that's in newer format
    ds = load_dataset("Muennighoff/babi", split="train")
    
    count = 0
    for example in ds:
        if example.get("task_num") != args.task:
            continue
        if count >= args.num:
            break
        
        print(f"=== Example {count} (task {args.task}) ===")
        print(f"Passage:\n{example['passage']}")
        print(f"\nQuestion: {example['question']}")
        print(f"Answer: {example['answer']}")
        print("\n" + "="*50 + "\n")
        count += 1

if __name__ == "__main__":
    main()