"""Print bAbI examples."""

import argparse
from datasets import load_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=5)
    parser.add_argument("--task", default="qa1", help="qa1-qa20")
    args = parser.parse_args()
    
    ds = load_dataset("facebook/babi_qa", type="en", task_no=args.task, split="train")
    
    for i, example in enumerate(ds):
        if i >= args.num:
            break
        
        print(f"=== Example {i} (task: {args.task}) ===")
        print(f"Story:\n{example['story']}")
        print(f"\nAnswer: {example['answer']}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()