"""
OER Quality Rubric Evaluator
Applies the OER quality rubric developed by GGC's AI in Curriculum and Pedagogy OER Working Group
"""
import resource
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class RubricEvaluator:
    """Evaluates OER resources using quality rubric"""
    
    def __init__(self, rubric_criteria=None):
        """
        Initialize evaluator with rubric criteria
        
        Args:
            rubric_criteria: List of criteria to evaluate. If None, uses default criteria.
        """
        self.criteria = rubric_criteria or [
            'Open License',
            'Content Quality',
            'Accessibility',
            'Relevance to Course',
            'Currency/Up-to-date',
            'Pedagogical Value',
            'Technical Quality'
        ]
    
    def evaluate(self, resource: Dict, llm_evaluation: Dict = None, keywords: str = None) -> Dict:
        evaluation = {
            'criteria_evaluations': {},
            'overall_score': 0,
            'summary': ''
        }

        for criterion in self.criteria:
            criterion_eval = self._evaluate_criterion(resource, criterion, llm_evaluation, keywords)
            evaluation['criteria_evaluations'][criterion] = criterion_eval

        scores = [eval_data.get('score', 0) for eval_data in evaluation['criteria_evaluations'].values()]
        if scores:
            evaluation['overall_score'] = sum(scores) / len(scores)

        evaluation['summary'] = self._generate_summary(evaluation)
        return evaluation
    
    def _evaluate_criterion(self, resource: Dict, criterion: str, llm_evaluation: Dict = None, keywords: str = None) -> Dict:
        eval_data = {
            'criterion': criterion,
            'score': 0,
            'explanation': '',
            'evidence': []
        }

        if llm_evaluation and 'criteria_scores' in llm_evaluation:
            if criterion in llm_evaluation['criteria_scores']:
                eval_data['score'] = llm_evaluation['criteria_scores'][criterion]
                eval_data['explanation'] = llm_evaluation.get('evaluation_text', '')

        if criterion == 'Open License':
            eval_data.update(self._evaluate_license(resource))
        elif criterion == 'Content Quality':
            eval_data.update(self._evaluate_content_quality(resource))
        elif criterion == 'Accessibility':
            eval_data.update(self._evaluate_accessibility(resource))
        elif criterion == 'Relevance to Course':
            eval_data.update(self._evaluate_relevance(resource, keywords))  # ← pass keywords
        elif criterion == 'Currency/Up-to-date':
            eval_data.update(self._evaluate_currency(resource))
        elif criterion == 'Pedagogical Value':
            eval_data.update(self._evaluate_pedagogical_value(resource))
        elif criterion == 'Technical Quality':
            eval_data.update(self._evaluate_technical_quality(resource))

        return eval_data
    
    def _evaluate_license(self, resource: Dict) -> Dict:
        """Evaluate open license criterion"""
        license_text = resource.get('license', '').lower()
        score = 0
        explanation = "License information not found or unclear."
        
        # Check for open licenses
        open_licenses = ['cc by', 'cc-by', 'creative commons', 'public domain', 'open access', 'mit', 'apache']
        if any(lic in license_text for lic in open_licenses):
            score = 5
            explanation = f"Resource has an open license: {resource.get('license', 'Unknown')}"
        elif 'copyright' in license_text and 'all rights reserved' in license_text:
            score = 1
            explanation = "Resource appears to have restrictive copyright, not an open license."
        elif license_text:
            score = 3
            explanation = f"License status unclear: {resource.get('license', 'Unknown')}"
        
        return {'score': score, 'explanation': explanation}
    
    def _evaluate_content_quality(self, resource: Dict) -> Dict:
        """Evaluate content quality"""
        description = resource.get('description', '')
        title = resource.get('title', '')
        source = resource.get('source', '').lower()
        
        score = 3  # Default middle score
        explanation = "Content quality assessment requires detailed review."
        
        # Differentiate by source/platform
        if 'openstax' in source:
            score = 4.0  # OpenStax is peer-reviewed and high quality
            explanation = "OpenStax provides peer-reviewed, high-quality textbooks."
        elif 'oer commons' in source:
            score = 3.5  # OER Commons has curated resources
            explanation = "OER Commons provides curated open educational resources."
        elif 'merlot' in source:
            score = 3.5  # MERLOT has peer-reviewed materials
            explanation = "MERLOT provides peer-reviewed learning materials."
        elif 'open textbook library' in source:
            score = 4.0  # Open Textbook Library has quality materials
            explanation = "Open Textbook Library provides quality open textbooks."
        else:
            # Basic heuristics for unknown sources
            if len(description) > 200:
                score += 0.5
                explanation = "Resource has substantial description."
            if title and len(title) > 10:
                score += 0.3
        
        return {'score': min(5, round(score, 1)), 'explanation': explanation}
    
    def _evaluate_accessibility(self, resource: Dict) -> Dict:
        """Evaluate accessibility"""
        score = 3
        explanation = "Accessibility information not explicitly provided. Requires manual review."
        
        # Check for accessibility indicators
        description = resource.get('description', '').lower()
        if any(word in description for word in ['accessible', 'ada', 'wcag', 'screen reader']):
            score = 4
            explanation = "Resource mentions accessibility features."
        
        return {'score': score, 'explanation': explanation}
    
    def _evaluate_relevance(self, resource: Dict, keywords: str = None) -> Dict:
        source = resource.get('source', '').lower()
        title = resource.get('title', '').lower()
        description = resource.get('description', '').lower()
        query = resource.get('query', '').lower()

        score = 3
        explanation = "Relevance should be evaluated in context of specific course requirements."

        # Use keywords to score relevance dynamically
        search_terms = [t for t in (keywords or query).lower().split() if len(t) > 2]
        if search_terms:
            matches = sum(1 for term in search_terms if term in title or term in description)
            match_ratio = matches / len(search_terms)

            if match_ratio >= 0.7:
                score = 5.0
                explanation = f"Resource closely matches course topic: {keywords or query}"
            elif match_ratio >= 0.4:
                score = 4.0
                explanation = f"Resource partially matches course topic."
            elif match_ratio >= 0.1:
                score = 3.0
                explanation = f"Resource has some overlap with course topic."
            else:
                score = 2.0
                explanation = "Limited keyword match. Review for direct course relevance."

        # Search/browse pages are less directly relevant
        if any(word in title for word in ['search', 'browse', 'materials']):
            score = max(1.5, score - 1)
            explanation = "This is a search/browse page. Review specific resources for direct relevance."

        return {'score': round(score, 1), 'explanation': explanation}
    
    def _evaluate_currency(self, resource: Dict) -> Dict:
        """Evaluate currency/up-to-date status"""
        score = 3
        explanation = "Publication date information not available. Requires manual verification."
        
        # Check for date indicators in description or URL
        description = resource.get('description', '').lower()
        if any(year in description for year in ['2024', '2025', '2026']):
            score = 4
            explanation = "Resource appears to be recent."
        
        return {'score': score, 'explanation': explanation}
    
    def _evaluate_pedagogical_value(self, resource: Dict) -> Dict:
        """Evaluate pedagogical value"""
        score = 3
        explanation = "Pedagogical value assessment requires content review."
        
        description = resource.get('description', '').lower()
        pedagogical_indicators = ['assignment', 'exercise', 'activity', 'lesson', 'module', 'curriculum']
        if any(indicator in description for indicator in pedagogical_indicators):
            score = 4
            explanation = "Resource appears to have pedagogical components."
        
        return {'score': score, 'explanation': explanation}
    
    def _evaluate_technical_quality(self, resource: Dict) -> Dict:
        """Evaluate technical quality"""
        score = 3
        explanation = "Technical quality requires access to the resource."
        
        url = resource.get('url', '')
        if url and ('http' in url):
            score = 4
            explanation = "Resource has accessible URL."
        
        return {'score': score, 'explanation': explanation}
    
    def _generate_summary(self, evaluation: Dict) -> str:
        """Generate evaluation summary"""
        overall = evaluation['overall_score']
        criteria = evaluation['criteria_evaluations']
        
        summary = f"Overall Quality Score: {overall:.1f}/5.0\n\n"
        summary += "Criterion Scores:\n"
        
        for criterion, eval_data in criteria.items():
            score = eval_data.get('score', 0)
            summary += f"- {criterion}: {score}/5\n"
        
        return summary
