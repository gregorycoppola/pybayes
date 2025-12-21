"""Analyze FACTS Grounding dataset to understand what's in it."""
import argparse
from collections import Counter
from datasets import load_dataset


def categorize_request(text: str) -> str:
    """Rough categorization based on keywords."""
    text_lower = text.lower()
    
    if any(w in text_lower for w in ['summarize', 'summary', 'summarise']):
        return 'summarization'
    if any(w in text_lower for w in ['list', 'what are', 'name the', 'identify']):
        return 'extraction'
    if any(w in text_lower for w in ['compare', 'difference', 'versus', 'vs']):
        return 'comparison'
    if any(w in text_lower for w in ['explain', 'why', 'how does', 'what does']):
        return 'explanation'
    if any(w in text_lower for w in ['pros and cons', 'advantages', 'disadvantages']):
        return 'pros_cons'
    if '?' in text:
        return 'question'
    return 'other'


def guess_domain(context: str) -> str:
    """Rough domain guess from context content."""
    ctx_lower = context.lower()
    
    if any(w in ctx_lower for w in ['patient', 'diagnosis', 'treatment', 'symptoms', 'clinical']):
        return 'medical'
    if any(w in ctx_lower for w in ['plaintiff', 'defendant', 'court', 'statute', 'legal']):
        return 'legal'
    if any(w in ctx_lower for w in ['revenue', 'earnings', 'fiscal', 'quarter', 'stock', 'investor']):
        return 'finance'
    if any(w in ctx_lower for w in ['software', 'api', 'server', 'database', 'code']):
        return 'technology'
    if any(w in ctx_lower for w in ['product', 'price', 'shipping', 'customer', 'order']):
        return 'retail'
    return 'other'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-examples", type=int, default=0,
                        help="show N examples per category")
    args = parser.parse_args()
    
    print("Loading dataset...")
    ds = load_dataset("google/FACTS-grounding-public", split="public")
    
    # Collect stats
    task_types = Counter()
    domains = Counter()
    context_lengths = []
    request_lengths = []
    
    examples_by_task = {}
    
    for example in ds:
        ctx = example['context_document']
        req = example['user_request']
        
        task = categorize_request(req)
        domain = guess_domain(ctx)
        
        task_types[task] += 1
        domains[domain] += 1
        context_lengths.append(len(ctx))
        request_lengths.append(len(req))
        
        if task not in examples_by_task:
            examples_by_task[task] = []
        if len(examples_by_task[task]) < 3:
            examples_by_task[task].append(req[:150])
    
    print(f"\n{'='*60}")
    print(f"FACTS Grounding Public: {len(ds)} examples")
    print(f"{'='*60}")
    
    print(f"\n📋 Task Types:")
    for task, count in task_types.most_common():
        pct = 100 * count / len(ds)
        print(f"  {task:20} {count:4} ({pct:5.1f}%)")
    
    print(f"\n🏷️  Domains (guessed):")
    for domain, count in domains.most_common():
        pct = 100 * count / len(ds)
        print(f"  {domain:20} {count:4} ({pct:5.1f}%)")
    
    print(f"\n📏 Context lengths:")
    print(f"  min: {min(context_lengths):,} chars")
    print(f"  max: {max(context_lengths):,} chars")
    print(f"  avg: {sum(context_lengths)//len(context_lengths):,} chars")
    
    print(f"\n📝 Request lengths:")
    print(f"  min: {min(request_lengths)} chars")
    print(f"  max: {max(request_lengths)} chars")
    print(f"  avg: {sum(request_lengths)//len(request_lengths)} chars")
    
    if args.show_examples:
        print(f"\n{'='*60}")
        print("Sample requests by category:")
        print(f"{'='*60}")
        for task, examples in examples_by_task.items():
            print(f"\n[{task}]")
            for ex in examples[:args.show_examples]:
                print(f"  • {ex}...")


if __name__ == "__main__":
    main()