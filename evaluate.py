"""
Evaluation module for RAG system.
Measures groundedness, citation accuracy, and latency.
"""

import os
import json
import time
import statistics
from typing import List, Dict, Any, Tuple
from rag import RAGPipeline
from dotenv import load_dotenv

load_dotenv()


class RAGEvaluator:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag = rag_pipeline
        self.results = []
    
    def load_eval_questions(self, file_path: str = "eval_questions.json") -> List[Dict[str, Any]]:
        """Load evaluation questions from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def check_groundedness(self, answer: str, sources: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Check if answer is grounded in sources.
        Simple heuristic: check if key facts in answer appear in sources.
        
        Returns: (is_grounded, explanation)
        """
        if "I can only answer" in answer or "I don't have information" in answer:
            return True, "Correctly refused to answer"
        
        # Check if answer contains citations
        has_citations = "[Source" in answer or "Source" in answer
        
        if not has_citations:
            return False, "No citations provided"
        
        # Extract sentences from answer (simple split)
        answer_lower = answer.lower()
        
        # Combine all source texts
        source_text = " ".join([s['full_text'].lower() for s in sources])
        
        # Check if major terms in answer appear in sources
        # This is a simplified check - production would use NLI models
        answer_words = set(answer_lower.split())
        source_words = set(source_text.split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'i', 'you', 'it', 'that', 'this'}
        answer_words = answer_words - common_words
        source_words = source_words - common_words
        
        overlap = len(answer_words & source_words)
        overlap_ratio = overlap / len(answer_words) if answer_words else 0
        
        # Consider grounded if >50% overlap
        is_grounded = overlap_ratio > 0.5
        explanation = f"Word overlap: {overlap_ratio:.2%}"
        
        return is_grounded, explanation
    
    def check_citation_accuracy(self, answer: str, sources: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Check if citations in answer point to correct sources.
        
        Returns: (citations_accurate, explanation)
        """
        if "I can only answer" in answer or "I don't have information" in answer:
            return True, "No claims made"
        
        # Extract citation numbers from answer
        import re
        citations = re.findall(r'\[Source (\d+)\]', answer)
        
        if not citations:
            return False, "No citations found in answer"
        
        # Check if cited sources exist
        max_source = len(sources)
        invalid_citations = [c for c in citations if int(c) > max_source]
        
        if invalid_citations:
            return False, f"Invalid citation numbers: {invalid_citations}"
        
        return True, f"Found {len(set(citations))} unique valid citations"
    
    def evaluate_answer(self, question: str, result: Dict[str, Any], expected_answer: str = None) -> Dict[str, Any]:
        """
        Evaluate a single answer across multiple metrics.
        
        Returns evaluation results dictionary.
        """
        answer = result['answer']
        sources = result['sources']
        
        # Groundedness check
        grounded, ground_explanation = self.check_groundedness(answer, sources)
        
        # Citation accuracy check
        citations_accurate, citation_explanation = self.check_citation_accuracy(answer, sources)
        
        # Optional: exact/partial match (if gold answer provided)
        exact_match = False
        partial_match = False
        if expected_answer:
            answer_lower = answer.lower()
            expected_lower = expected_answer.lower()
            exact_match = answer_lower.strip() == expected_lower.strip()
            partial_match = expected_lower in answer_lower or answer_lower in expected_lower
        
        eval_result = {
            'question': question,
            'answer': answer,
            'grounded': grounded,
            'groundedness_explanation': ground_explanation,
            'citations_accurate': citations_accurate,
            'citation_explanation': citation_explanation,
            'exact_match': exact_match,
            'partial_match': partial_match,
            'num_sources': len(sources),
            'latency_ms': result.get('latency_ms', 0)
        }
        
        return eval_result
    
    def run_evaluation(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run full evaluation suite on list of questions.
        
        Args:
            questions: List of dicts with 'question' and optional 'expected_answer'
        
        Returns:
            Evaluation summary with metrics
        """
        print("\n" + "="*60)
        print("Starting RAG Evaluation")
        print("="*60)
        
        results = []
        latencies = []
        
        for i, q_data in enumerate(questions, 1):
            question = q_data['question']
            expected = q_data.get('expected_answer', None)
            
            print(f"\n[{i}/{len(questions)}] {question}")
            
            # Query RAG system
            start_time = time.time()
            result = self.rag.query(question)
            latency_ms = int((time.time() - start_time) * 1000)
            result['latency_ms'] = latency_ms
            
            # Evaluate answer
            eval_result = self.evaluate_answer(question, result, expected)
            results.append(eval_result)
            latencies.append(latency_ms)
            
            print(f"  ✓ Grounded: {eval_result['grounded']}")
            print(f"  ✓ Citations Accurate: {eval_result['citations_accurate']}")
            print(f"  ✓ Latency: {latency_ms}ms")
        
        # Calculate aggregate metrics
        grounded_count = sum(1 for r in results if r['grounded'])
        citations_accurate_count = sum(1 for r in results if r['citations_accurate'])
        exact_match_count = sum(1 for r in results if r['exact_match'])
        partial_match_count = sum(1 for r in results if r['partial_match'])
        
        summary = {
            'total_questions': len(questions),
            'groundedness': {
                'count': grounded_count,
                'percentage': (grounded_count / len(questions)) * 100
            },
            'citation_accuracy': {
                'count': citations_accurate_count,
                'percentage': (citations_accurate_count / len(questions)) * 100
            },
            'exact_match': {
                'count': exact_match_count,
                'percentage': (exact_match_count / len(questions)) * 100
            },
            'partial_match': {
                'count': partial_match_count,
                'percentage': (partial_match_count / len(questions)) * 100
            },
            'latency': {
                'p50': statistics.median(latencies),
                'p95': statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0],
                'mean': statistics.mean(latencies),
                'min': min(latencies),
                'max': max(latencies)
            },
            'detailed_results': results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print evaluation summary in readable format."""
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        
        print(f"\n📊 Total Questions: {summary['total_questions']}")
        
        print("\n🎯 ANSWER QUALITY METRICS:")
        print(f"  Groundedness:      {summary['groundedness']['count']}/{summary['total_questions']} ({summary['groundedness']['percentage']:.1f}%)")
        print(f"  Citation Accuracy: {summary['citation_accuracy']['count']}/{summary['total_questions']} ({summary['citation_accuracy']['percentage']:.1f}%)")
        
        if summary['exact_match']['count'] > 0 or summary['partial_match']['count'] > 0:
            print(f"  Exact Match:       {summary['exact_match']['count']}/{summary['total_questions']} ({summary['exact_match']['percentage']:.1f}%)")
            print(f"  Partial Match:     {summary['partial_match']['count']}/{summary['total_questions']} ({summary['partial_match']['percentage']:.1f}%)")
        
        print("\n⚡ SYSTEM METRICS:")
        print(f"  Latency P50:  {summary['latency']['p50']:.0f}ms")
        print(f"  Latency P95:  {summary['latency']['p95']:.0f}ms")
        print(f"  Latency Mean: {summary['latency']['mean']:.0f}ms")
        print(f"  Latency Min:  {summary['latency']['min']:.0f}ms")
        print(f"  Latency Max:  {summary['latency']['max']:.0f}ms")
        
        print("\n" + "="*60)
    
    def save_results(self, summary: Dict[str, Any], output_file: str = "evaluation_results.json"):
        """Save evaluation results to JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print(f"\n✅ Results saved to {output_file}")


def main():
    """Run evaluation."""
    # Initialize RAG pipeline
    print("Initializing RAG pipeline...")
    rag = RAGPipeline(
        db_path="chroma_db",
        embedding_model="all-MiniLM-L6-v2",
        llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
        model_name=os.getenv("MODEL_NAME", "meta-llama/llama-3.1-8b-instruct:free"),
        top_k=5
    )
    
    # Initialize evaluator
    evaluator = RAGEvaluator(rag)
    
    # Load questions
    try:
        questions = evaluator.load_eval_questions("eval_questions.json")
    except FileNotFoundError:
        print("eval_questions.json not found. Using default questions.")
        questions = [
            {"question": "How many days of PTO do I get?"},
            {"question": "Can I work remotely?"},
            {"question": "What is the expense reimbursement limit for meals when traveling?"},
            {"question": "What holidays does the company observe?"},
            {"question": "What are the password requirements?"},
            {"question": "How do I request parental leave?"},
            {"question": "What is the 401k company match?"},
            {"question": "Can I expense my gym membership?"},
            {"question": "What should I do if I lose my laptop?"},
            {"question": "How often are performance reviews conducted?"},
        ]
    
    # Run evaluation
    summary = evaluator.run_evaluation(questions)
    
    # Print summary
    evaluator.print_summary(summary)
    
    # Save results
    evaluator.save_results(summary)


if __name__ == "__main__":
    main()
