"""Print FACTS Grounding examples."""
import argparse
from datasets import load_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=3)
    parser.add_argument("--max-context", type=int, default=500, 
                        help="truncate context_document display")
    args = parser.parse_args()
    
    ds = load_dataset("google/FACTS-grounding-public", split="public")
    
    for i, example in enumerate(ds):
        if i >= args.num:
            break
        
        print(f"=== Example {i} ===")
        print(f"System: {example['system_instruction'][:200]}...")
        print(f"\nUser Request: {example['user_request']}")
        
        ctx = example['context_document']
        if len(ctx) > args.max_context:
            ctx = ctx[:args.max_context] + f"... [{len(example['context_document'])} chars total]"
        print(f"\nContext Document:\n{ctx}")
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
