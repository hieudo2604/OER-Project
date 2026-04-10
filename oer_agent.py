"""
Main OER AI Agent
Orchestrates the complete workflow: syllabus analysis, OER search, evaluation, and reporting
"""
import time
import re
from typing import Dict, List, Optional
import logging

from config import Config
from scrapers.syllabus_scraper import SyllabusScraper
from scrapers.alg_scraper import ALGScraper
from llm.llm_client import LLMClient
from evaluators.rubric_evaluator import RubricEvaluator
from evaluators.license_checker import LicenseChecker
from utils.logger import UsageLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OERAgent:
    """Main AI agent for OER identification and evaluation"""
    
    def __init__(self, llm_provider=None, llm_model=None, use_selenium=False):
        """
        Initialize the OER Agent
        
        Args:
            llm_provider: LLM provider ('openai', 'anthropic', etc.)
            llm_model: Specific model to use
            use_selenium: If True, use Selenium scraper (requires selenium package)
        """
        self.config = Config()
        
        # Use Selenium scraper only if requested and available
        if use_selenium:
            try:
                from scrapers.syllabus_scraper_selenium import SyllabusScraperSelenium
                self.syllabus_scraper = SyllabusScraperSelenium(self.config.SYLLABUS_BASE_URL)
                logger.info("Using Selenium scraper for JavaScript-rendered content")
            except ImportError:
                logger.warning("Selenium not available, falling back to regular scraper")
                self.syllabus_scraper = SyllabusScraper(self.config.SYLLABUS_BASE_URL)
        else:
            self.syllabus_scraper = SyllabusScraper(self.config.SYLLABUS_BASE_URL)
        self.alg_scraper = ALGScraper(self.config.ALG_BASE_URL)
        self.llm = LLMClient(
            provider=llm_provider or self.config.DEFAULT_LLM_PROVIDER,
            model=llm_model or self.config.DEFAULT_MODEL
        )
        self.rubric_evaluator = RubricEvaluator(self.config.RUBRIC_CRITERIA)
        self.license_checker = LicenseChecker()
        self.logger = UsageLogger(self.config.LOG_DIR)
    
    def find_oer_for_course(self, course_code: str, term: str = None, keywords: str = None) -> Dict:
        """
        Main method: Find and evaluate OER resources for a course
        
        Args:
            course_code: Course code (e.g., 'ENGL 1101')
            term: Optional term (e.g., 'Fall 2025')
        
        Returns:
            Complete results with OER recommendations and evaluations
        """
        start_time = time.time()
        # Use course name keywords for search, fall back to course code
        search_keywords = keywords or course_code
        logger.info(f"Using search keywords: {search_keywords}")
        
        try:
            logger.info(f"Starting OER search for {course_code}")
            
            # Step 1: Get syllabus information
            logger.info("Step 1: Fetching syllabus information...")
            syllabi = self.syllabus_scraper.search_course(course_code, term)
            
            if not syllabi:
                logger.warning(f"No syllabi found for {course_code}")
                syllabi = [{'course_code': course_code, 'title': course_code, 'description': ''}]
            
            syllabus_info = syllabi[0]  # Use first syllabus found
            
            # Step 2: Search ALG Library for relevant resources
            logger.info("Step 2: Searching Open ALG Library...")
            search_query = search_keywords
            alg_resources = self.alg_scraper.search_resources(search_query, course_code)

            if not alg_resources:
                logger.warning(f"No resources found in ALG Library for {course_code}")
                subject = course_code.split()[0] if ' ' in course_code else course_code
                alg_resources = self.alg_scraper.search_resources(subject, course_code)
                logger.info(f"Broader search found {len(alg_resources)} resources")

            # Step 2b: ALWAYS get LLM direct-link resources and merge them in (runs for every course)
            logger.info("Step 2b: Getting LLM direct-link resources...")
            try:
                llm_resources = self._get_llm_suggested_resources(course_code, syllabus_info, search_keywords)
                logger.info(f"LLM found {len(llm_resources)} direct-link resources")
                # LLM resources first (direct book links), then ALG resources after
                alg_resources = llm_resources + (alg_resources or [])
            except Exception as e:
                logger.warning(f"LLM resource suggestion failed: {e}")
                if not alg_resources:
                    alg_resources = self._get_default_suggestions(course_code, search_keywords)
                    logger.info(f"Using {len(alg_resources)} default suggestions as fallback")

            # Final fallback - only if everything above failed
            if not alg_resources:
                logger.warning("All methods failed. Creating minimal default resources.")
                alg_resources = self._get_default_suggestions(course_code, search_keywords)
                logger.info(f"Created {len(alg_resources)} default resources as final fallback")
            
            # Step 3: Use LLM to identify most relevant resources (optional)
            logger.info("Step 3: Identifying relevant OER resources with AI...")
            identified_resources = []
            
            if alg_resources:
                try:
                    identified_resources = self.llm.identify_oer_resources(syllabus_info, alg_resources)
                    if not identified_resources:
                        raise Exception("LLM returned empty results")
                except Exception as e:
                    logger.warning(f"LLM identification failed: {e}. Using resources directly.")
                    # If LLM fails, use resources directly
                    identified_resources = [{'resource': r, 'relevance_explanation': f'Resource for {course_code}', 'identified_by': 'direct'} for r in alg_resources[:10]]
            
            # If no identified resources but we have alg_resources, use them directly
            if not identified_resources and alg_resources:
                logger.info("Using resources directly without LLM identification")
                identified_resources = [{'resource': r, 'relevance_explanation': f'Resource for {course_code}', 'identified_by': 'direct'} for r in alg_resources[:10]]
            
            # Step 4: Evaluate each identified resource
            logger.info("Step 4: Evaluating OER quality...")
            logger.info(f"Identified resources count: {len(identified_resources)}, ALG resources count: {len(alg_resources)}")
            evaluated_resources = []
            
            # Ensure we have resources to evaluate - CRITICAL FIX
            if not identified_resources and alg_resources:
                logger.info(f"Creating identified_resources from {len(alg_resources)} alg_resources")
                identified_resources = [{'resource': r, 'relevance_explanation': f'Resource for {course_code}', 'identified_by': 'direct'} for r in alg_resources[:10]]
                logger.info(f"Created {len(identified_resources)} identified_resources")
            
            # If still no identified_resources but we have alg_resources, force create them
            if not identified_resources and alg_resources:
                logger.warning("FORCE CREATING identified_resources from alg_resources")
                for r in alg_resources[:10]:
                    if r:  # Make sure resource is not None
                        identified_resources.append({
                            'resource': r,
                            'relevance_explanation': f'Resource for {course_code}',
                            'identified_by': 'force_created'
                        })
                logger.info(f"Force created {len(identified_resources)} identified_resources")
            
            logger.info(f"About to evaluate {len(identified_resources)} resources...")
            if not identified_resources:
                logger.error("ERROR: No identified_resources to evaluate! This should not happen.")
            
            for idx, identified in enumerate(identified_resources[:10]):  # Limit to top 10
                try:
                    logger.info(f"Processing resource {idx+1}/{len(identified_resources)}")
                    resource = identified.get('resource', {})
                    
                    # Skip if resource is empty
                    if not resource:
                        logger.warning(f"Skipping empty resource at index {idx}")
                        continue
                    
                    # Ensure resource has at least a title or URL
                    if not resource.get('title') and not resource.get('url'):
                        logger.warning(f"Skipping resource with no title or URL: {resource}")
                        continue
                    
                    # Set default title if missing
                    if not resource.get('title'):
                        resource['title'] = resource.get('url', 'Untitled Resource')
                        logger.info(f"Set default title for resource: {resource['title']}")
                    
                    # Get detailed resource information if needed
                    if not resource.get('description') and resource.get('url'):
                        try:
                            details = self.alg_scraper.get_resource_details(resource['url'])
                            if details:
                                resource.update(details)
                        except Exception as e:
                            logger.debug(f"Could not get details for {resource.get('url')}: {e}")
                    
                    # LLM evaluation
                    llm_eval = {}
                    try:
                        llm_eval = self.llm.evaluate_oer_quality(resource, self.config.RUBRIC_CRITERIA)
                    except Exception as e:
                        logger.warning(f"LLM evaluation failed for {resource.get('title', 'Unknown')}: {e}")
                    
                    # Rubric evaluation (always works, doesn't need LLM)
                    try:
                        rubric_eval = self.rubric_evaluator.evaluate(resource, llm_eval, search_keywords)
                    except Exception as e:
                        logger.error(f"Rubric evaluation failed: {e}")
                        # Create minimal evaluation
                        rubric_eval = {
                            'criteria_evaluations': {},
                            'overall_score': 0,
                            'summary': 'Evaluation incomplete'
                        }
                    
                    # License check
                    try:
                        license_check = self.license_checker.check_license(resource)
                    except Exception as e:
                        logger.error(f"License check failed: {e}")
                        license_check = {
                            'has_open_license': False,
                            'license_type': 'Unknown',
                            'confidence': 'low',
                            'evidence': 'License check failed',
                            'details': ''
                        }
                    
                    # Combine evaluations
                    evaluated_resource = {
                        'resource': resource,
                        'relevance_explanation': identified.get('relevance_explanation', ''),
                        'llm_evaluation': llm_eval,
                        'rubric_evaluation': rubric_eval,
                        'license_check': license_check,
                        'integration_guidance': self._generate_integration_guidance(resource, rubric_eval, license_check)
                    }
                    
                    evaluated_resources.append(evaluated_resource)
                    logger.info(f"Successfully evaluated resource {idx+1}: {resource.get('title', 'Unknown')}")
                    
                except Exception as e:
                    logger.error(f"Error processing resource {idx+1}: {e}", exc_info=True)
                    # Even if evaluation fails, try to add resource with minimal data
                    try:
                        logger.info(f"Attempting to add resource {idx+1} with minimal evaluation")
                        resource = identified.get('resource', {})
                        if resource:
                            minimal_resource = {
                                'resource': resource,
                                'relevance_explanation': identified.get('relevance_explanation', f'Resource for {course_code}'),
                                'llm_evaluation': {},
                                'rubric_evaluation': {
                                    'resource': resource,
                                    'criteria_evaluations': {},
                                    'overall_score': 0,
                                    'summary': 'Evaluation failed - resource added with minimal data'
                                },
                                'license_check': {
                                    'has_open_license': False,
                                    'license_type': 'Unknown',
                                    'confidence': 'low',
                                    'evidence': 'Could not evaluate',
                                    'details': ''
                                },
                                'integration_guidance': f'Resource URL: {resource.get("url", "N/A")}\nNote: Full evaluation could not be completed.'
                            }
                            evaluated_resources.append(minimal_resource)
                            logger.info(f"Added resource {idx+1} with minimal evaluation: {resource.get('title', 'Unknown')}")
                    except Exception as e2:
                        logger.error(f"Failed to add resource even with minimal evaluation: {e2}")
                    continue
            
            logger.info(f"Created {len(evaluated_resources)} evaluated resources after main loop")
            
            # CRITICAL: If we still have no evaluated resources but have alg_resources, create them now
            if not evaluated_resources and alg_resources:
                logger.warning(f"EMERGENCY: No evaluated_resources but we have {len(alg_resources)} alg_resources. Creating evaluations now!")
                for idx, resource in enumerate(alg_resources[:10]):
                    try:
                        logger.info(f"[EMERGENCY] Creating evaluation {idx+1}/{min(10, len(alg_resources))} for: {resource.get('title', 'Unknown')}")
                        
                        # Ensure resource is valid
                        if not isinstance(resource, dict):
                            logger.warning(f"Resource {idx+1} is not a dict: {type(resource)}")
                            continue
                        
                        if not resource.get('title') and not resource.get('url'):
                            logger.warning(f"Resource {idx+1} has no title or URL")
                            resource['title'] = f'Resource {idx+1}'
                        
                        if not resource.get('title'):
                            resource['title'] = resource.get('url', f'Resource {idx+1}')
                        
                        # Evaluate
                        rubric_eval = self.rubric_evaluator.evaluate(resource, {}, search_keywords)
                        license_check = self.license_checker.check_license(resource)
                        
                        evaluated_resource = {
                            'resource': resource,
                            'relevance_explanation': f'Resource for {course_code}',
                            'llm_evaluation': {},
                            'rubric_evaluation': rubric_eval,
                            'license_check': license_check,
                            'integration_guidance': self._generate_integration_guidance(resource, rubric_eval, license_check)
                        }
                        evaluated_resources.append(evaluated_resource)
                        logger.info(f"[EMERGENCY] Successfully added resource {idx+1}: {resource.get('title', 'Unknown')}")
                    except Exception as e:
                        logger.error(f"[EMERGENCY] Error evaluating resource {idx+1}: {e}", exc_info=True)
                        # Even if evaluation fails, add the resource with minimal info
                        try:
                            evaluated_resource = {
                                'resource': resource,
                                'relevance_explanation': f'Resource for {course_code}',
                                'llm_evaluation': {},
                                'rubric_evaluation': {
                                    'criteria_evaluations': {},
                                    'overall_score': 0,
                                    'summary': 'Evaluation incomplete due to error'
                                },
                                'license_check': {
                                    'has_open_license': False,
                                    'license_type': 'Unknown',
                                    'confidence': 'low',
                                    'evidence': 'Could not evaluate',
                                    'details': ''
                                },
                                'integration_guidance': f'Resource URL: {resource.get("url", "N/A")}'
                            }
                            evaluated_resources.append(evaluated_resource)
                            logger.info(f"Added resource with minimal evaluation: {resource.get('title', 'Unknown')}")
                        except Exception as e2:
                            logger.error(f"Failed to add resource even with minimal evaluation: {e2}")
            
            # Sort by overall quality score
            evaluated_resources.sort(
                key=lambda x: x['rubric_evaluation'].get('overall_score', 0),
                reverse=True
            )
            
            # FINAL SAFETY CHECK - BEFORE creating results dictionary
            # This MUST happen before results is created
            if not evaluated_resources:
                logger.warning("FINAL CHECK: No evaluated_resources! Creating default suggestions NOW.")
                try:
                    # Get default suggestions
                    if not alg_resources:
                        alg_resources = self._get_default_suggestions(course_code, keywords)
                        logger.info(f"Got {len(alg_resources)} default suggestions")
                    
                    # Evaluate default suggestions
                    for resource in alg_resources[:10]:
                        try:
                            logger.info(f"Evaluating default resource: {resource.get('title', 'Unknown')}")
                            rubric_eval = self.rubric_evaluator.evaluate(resource, {}, search_keywords)
                            license_check = self.license_checker.check_license(resource)
                            evaluated_resources.append({
                                'resource': resource,
                                'relevance_explanation': f'Default OER suggestion for {course_code}',
                                'llm_evaluation': {},
                                'rubric_evaluation': rubric_eval,
                                'license_check': license_check,
                                'integration_guidance': self._generate_integration_guidance(resource, rubric_eval, license_check)
                            })
                            logger.info(f"Successfully added default resource: {resource.get('title', 'Unknown')}")
                        except Exception as e:
                            logger.error(f"Error processing default resource: {e}", exc_info=True)
                            # Add with minimal data
                            evaluated_resources.append({
                                'resource': resource,
                                'relevance_explanation': f'Default OER suggestion for {course_code}',
                                'llm_evaluation': {},
                                'rubric_evaluation': {'criteria_evaluations': {}, 'overall_score': 0, 'summary': 'Evaluation incomplete'},
                                'license_check': {'has_open_license': True, 'license_type': resource.get('license', 'CC BY'), 'confidence': 'medium', 'evidence': '', 'details': ''},
                                'integration_guidance': f"Resource URL: {resource.get('url', 'N/A')}"
                            })
                    
                    logger.info(f"Final safety check created {len(evaluated_resources)} evaluated resources")
                except Exception as e:
                    logger.error(f"Final safety check failed: {e}", exc_info=True)
                    # Last resort - create at least one resource
                    evaluated_resources = [{
                        'resource': {
                            'title': f'OER Resources for {course_code}',
                            'description': f'Search for open educational resources for {course_code}',
                            'url': 'https://alg.manifoldapp.org',
                            'license': 'CC BY',
                            'author': 'Various',
                            'source': 'Open ALG Library'
                        },
                        'relevance_explanation': f'General OER resources for {course_code}',
                        'llm_evaluation': {},
                        'rubric_evaluation': {'criteria_evaluations': {}, 'overall_score': 0, 'summary': 'Minimal evaluation'},
                        'license_check': {'has_open_license': True, 'license_type': 'CC BY', 'confidence': 'medium', 'evidence': '', 'details': ''},
                        'integration_guidance': f'Visit https://alg.manifoldapp.org to search for {course_code} resources'
                    }]
                    logger.info("Created last resort resource")
            
            # GUARANTEE we have at least one resource
            if not evaluated_resources:
                logger.error("CRITICAL: Still no evaluated_resources! Creating emergency resource.")
                evaluated_resources = [{
                    'resource': {
                        'title': f'OER Resources for {course_code}',
                        'description': f'Search for open educational resources for {course_code}',
                        'url': 'https://alg.manifoldapp.org',
                        'license': 'CC BY',
                        'author': 'Various',
                        'source': 'Emergency Fallback'
                    },
                    'relevance_explanation': f'Emergency fallback resource for {course_code}',
                    'llm_evaluation': {},
                    'rubric_evaluation': {'criteria_evaluations': {}, 'overall_score': 0, 'summary': 'Emergency evaluation'},
                    'license_check': {'has_open_license': True, 'license_type': 'CC BY', 'confidence': 'low', 'evidence': '', 'details': ''},
                    'integration_guidance': f'Visit https://alg.manifoldapp.org to search for {course_code} resources'
                }]
            
            # Step 5: Compile results - NOW that we're GUARANTEED to have evaluated_resources
            processing_time = time.time() - start_time
            
            # Final check before creating results
            logger.info(f"FINAL CHECK: {len(evaluated_resources)} evaluated_resources, {len(alg_resources)} alg_resources")
            
            results = {
                'course_code': course_code,
                'term': term,
                'syllabus_info': syllabus_info,
                'resources_found': len(alg_resources) if alg_resources else len(evaluated_resources),
                'resources_evaluated': len(evaluated_resources),
                'evaluated_resources': evaluated_resources,
                'summary': self._generate_summary(evaluated_resources),
                'processing_time_seconds': processing_time
            }
            
            # Debug: Log what we're returning
            logger.info(f"RETURNING: {len(evaluated_resources)} evaluated_resources")
            if evaluated_resources:
                logger.info(f"First resource title: {evaluated_resources[0].get('resource', {}).get('title', 'N/A')}")
            else:
                logger.error("CRITICAL ERROR: Returning 0 evaluated_resources after all checks!")
            
            # Log the query
            self.logger.log_query(
                course_code=course_code,
                query_type='oer_search',
                results=evaluated_resources,
                processing_time=processing_time,
                status='success'
            )
            
            logger.info(f"Completed OER search for {course_code} in {processing_time:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"Error in OER search for {course_code}: {e}", exc_info=True)
            processing_time = time.time() - start_time
            
            # Log error
            self.logger.log_query(
                course_code=course_code,
                query_type='oer_search',
                results=[],
                processing_time=processing_time,
                status='error'
            )
            
            return {
                'course_code': course_code,
                'error': str(e),
                'processing_time_seconds': processing_time
            }
    
    def _generate_integration_guidance(self, resource: Dict, rubric_eval: Dict, license_check: Dict) -> str:
        """Generate guidance for instructors on how to integrate the resource"""
        guidance = []
        
        # License information
        if license_check.get('has_open_license'):
            guidance.append(f"✓ Open License Confirmed: {license_check.get('license_type', 'Open')}")
        else:
            guidance.append(f"⚠ License Status: {license_check.get('license_type', 'Unknown')} - Verify before use")
        
        # Quality score
        overall_score = rubric_eval.get('overall_score', 0)
        if overall_score >= 4:
            guidance.append(f"✓ High Quality Resource (Score: {overall_score:.1f}/5.0)")
        elif overall_score >= 3:
            guidance.append(f"○ Moderate Quality Resource (Score: {overall_score:.1f}/5.0)")
        else:
            guidance.append(f"⚠ Lower Quality Resource (Score: {overall_score:.1f}/5.0) - Review carefully")
        
        # Strengths from evaluation
        if 'llm_evaluation' in rubric_eval and 'strengths' in rubric_eval['llm_evaluation']:
            strengths = rubric_eval['llm_evaluation']['strengths']
            if strengths:
                guidance.append(f"Key Strengths: {', '.join(strengths[:3])}")
        
        # Integration suggestions
        guidance.append(f"Resource URL: {resource.get('url', 'N/A')}")
        guidance.append("Consider: Review the resource content to determine best integration approach for your specific course needs.")
        
        return '\n'.join(guidance)
    
#     def _get_llm_suggested_resources(self, course_code: str, syllabus_info: Dict, keywords: str = None) -> List[Dict]:
#         """Use LLM to suggest OER resources when scrapers fail"""
#         system_prompt = """You are an expert in open educational resources (OER). 
# Suggest relevant OER resources for courses. Provide realistic resource suggestions with titles, 
# descriptions, and URLs to common OER platforms like OpenStax, OER Commons, MERLOT, etc."""
        
#         prompt = f"""Course: {course_code}
# Title: {syllabus_info.get('title', course_code)}
# Description: {syllabus_info.get('description', '')[:500]}

# Suggest 5-10 relevant OER resources for this course. For each resource, provide:
# 1. Title
# 2. Brief description
# 3. URL (use a realistic OER platform URL like openstax.org, oercommons.org, etc.)
# 4. License type (e.g., CC BY, CC BY-SA)
# 5. Author/Publisher

# Format as a numbered list."""
        
#         try:
#             response = self.llm.generate(prompt, system_prompt, max_tokens=2000)
#         except Exception as e:
#             logger.error(f"LLM generation failed: {e}")
#             # Return some default suggestions
#             return self._get_default_suggestions(course_code, keywords)
        
#         if not response:
#             return self._get_default_suggestions(course_code, keywords)
        
#         # Parse LLM response into resource format
#         resources = []
#         lines = response.split('\n')
#         current_resource = {}
        
#         for line in lines:
#             line = line.strip()
#             if not line or line.startswith('#'):
#                 continue
            
#             # Look for numbered items
#             if re.match(r'^\d+[\.\)]', line):
#                 if current_resource:
#                     resources.append(current_resource)
#                 current_resource = {
#                     'title': '',
#                     'description': '',
#                     'url': '',
#                     'license': 'CC BY',
#                     'author': '',
#                     'source': 'LLM Suggested',
#                     'query': course_code
#                 }
#                 # Extract title (remove number)
#                 title = re.sub(r'^\d+[\.\)]\s*', '', line)
#                 current_resource['title'] = title[:200]
            
#             elif current_resource:
#                 line_lower = line.lower()
#                 if 'url' in line_lower or 'http' in line_lower:
#                     # Extract URL
#                     url_match = re.search(r'https?://[^\s]+', line)
#                     if url_match:
#                         current_resource['url'] = url_match.group(0)
#                 elif 'license' in line_lower or 'cc' in line_lower:
#                     # Extract license
#                     license_match = re.search(r'CC\s*[A-Z\-]+', line, re.IGNORECASE)
#                     if license_match:
#                         current_resource['license'] = license_match.group(0)
#                 elif 'author' in line_lower or 'publisher' in line_lower:
#                     # Extract author
#                     author = re.sub(r'^(author|publisher):\s*', '', line, flags=re.IGNORECASE)
#                     current_resource['author'] = author[:100]
#                 else:
#                     # Add to description
#                     if current_resource['description']:
#                         current_resource['description'] += ' ' + line
#                     else:
#                         current_resource['description'] = line
#                     current_resource['description'] = current_resource['description'][:500]
        
#         if current_resource:
#             resources.append(current_resource)
        
#         # If parsing failed, create at least one resource with the response
#         if not resources:
#             resources.append({
#                 'title': f'OER Resources for {course_code}',
#                 'description': response[:500],
#                 'url': 'https://alg.manifoldapp.org',
#                 'license': 'CC BY',
#                 'author': 'Various',
#                 'source': 'LLM Suggested',
#                 'query': course_code
#             })
        
#         logger.info(f"LLM suggested {len(resources)} resources")
#         return resources
    
    def _get_llm_suggested_resources(self, course_code: str, syllabus_info: Dict, keywords: str = None) -> List[Dict]:
        system_prompt = """You are an OER expert.

    Return ONLY real, existing open textbooks with DIRECT URLs.

GOOD:
 - https://openstax.org/details/books/biology-2e
 - https://open.umn.edu/opentextbooks/textbooks/database-design-2nd-edition
 - https://greenteapress.com/wp/think-python-2e/

BAD (NEVER RETURN):
 - search pages
 - URLs with ?query= or ?search=
 - homepage links
    """

        base_prompt = f"""Find 3-5 OPEN TEXTBOOKS for:

    Course: {course_code}
    Topic: {keywords or syllabus_info.get('title', course_code)}

    FORMAT STRICTLY:

    RESOURCE
    Title: ...
    URL: ...
    License: ...
    Author: ...
    Description: ...
    END
    """

        def generate_and_parse(prompt_text):
            try:
                response = self.llm.generate(prompt_text, system_prompt, max_tokens=2000)
            except Exception as e:
                logger.error(f"LLM failed: {e}")
                return []

            if not response:
                return []

            resources = []
            blocks = re.split(r'\bRESOURCE\b', response, flags=re.IGNORECASE)

            for block in blocks[1:]:
                resource = {
                    'title': '',
                    'url': '',
                    'license': 'CC BY',
                    'author': '',
                    'description': '',
                    'source': 'LLM Suggested',
                    'query': keywords or course_code
                }

                for line in block.split('\n'):
                    line = line.strip()
                    if not line or line.upper() == 'END':
                        continue

                    if ':' not in line:
                        continue

                    key, _, value = line.partition(':')
                    key = key.strip().lower()
                    value = value.strip()

                    if key == 'title':
                        resource['title'] = value
                    elif key == 'url':
                        match = re.search(r'https?://[^\s]+', value)
                        if match:
                            resource['url'] = match.group(0).rstrip('.,)')
                    elif key == 'license':
                        resource['license'] = value
                    elif key == 'author':
                        resource['author'] = value
                    elif key == 'description':
                        resource['description'] = value

                # Detect source
                url = resource.get('url', '').lower()
                if 'openstax' in url:
                    resource['source'] = 'OpenStax'
                elif 'open.umn' in url:
                    resource['source'] = 'Open Textbook Library'
                elif 'libretexts' in url:
                    resource['source'] = 'LibreTexts'
                elif 'ocw.mit' in url:
                    resource['source'] = 'MIT OpenCourseWare'
                elif 'greenteapress' in url:
                    resource['source'] = 'Green Tea Press'
                elif 'gutenberg' in url:
                    resource['source'] = 'Project Gutenberg'

                # STRICT FILTER
                if self._is_valid_direct_url(resource.get('url')):
                    resources.append(resource)
                    logger.info(f"✓ Accepted: {resource['title']} → {resource['url']}")
                else:
                    logger.warning(f"✗ Rejected URL: {resource.get('url')}")

            return resources

        # --- First attempt ---
        resources = generate_and_parse(base_prompt)

        # --- Retry with stricter prompt if needed ---
        if not resources:
            logger.warning("Retrying LLM with stricter constraints...")
            stricter_prompt = base_prompt + "\nONLY return URLs containing '/books/' or '/textbooks/' or '/ebooks/'."
            resources = generate_and_parse(stricter_prompt)

        # --- Final fallback ---
        if not resources:
            logger.warning("LLM failed completely, using clean fallback")
            return self._get_default_suggestions(course_code, keywords)

        logger.info(f"LLM returned {len(resources)} valid direct resources")
        return resources
    
    def _is_valid_direct_url(self, url: str) -> bool:
        if not url:
            return False

        url_lower = url.lower()

        # Reject obvious search/browse pages
        bad_patterns = [
            '/search?', '/browse?', 'f.search=', 'keywords=',
            '/subjects/', '/hubs/', '/catalog?'
        ]
        if any(p in url_lower for p in bad_patterns):
            return False

        # Accept known OER platforms with direct resource paths
        good_patterns = [
            'openstax.org/details/books/',
            'open.umn.edu/opentextbooks/textbooks/',
            'greenteapress.com',
            'libretexts.org',
            'ocw.mit.edu/courses',
            'gutenberg.org/ebooks/',
            'artint.info',
            'python.org',
            'docs.python.org',
        ]
        return any(p in url_lower for p in good_patterns)

    def _get_default_suggestions(self, course_code: str, keywords: str = None) -> List[Dict]:
        """Get default OER suggestions when LLM fails"""
        subject = course_code.split()[0] if ' ' in course_code else course_code
        course_num = course_code.split()[1] if ' ' in course_code else ''
        search_term = keywords or course_code  # ← use meaningful keywords
        search_term_encoded = search_term.replace(" ", "+")
        hub_id = 19;
        
        # Map common subjects to relevant OER platforms
        subject_lower = subject.lower()
        
        # Course-specific suggestions based on subject
        default_resources = []
        
        # Biology courses
        if 'biol' in subject_lower:
            if '1101' in course_num or '1102' in course_num:
                default_resources.extend([
                    {
                        'title': 'Biology 2e - OpenStax',
                        'description': f'Free, peer-reviewed biology textbook covering principles of biology, cell structure, genetics, evolution, and ecology. Suitable for {course_code}.',
                        'url': 'https://openstax.org/details/books/biology-2e',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    },
                    {
                        'title': 'Concepts of Biology - OpenStax',
                        'description': f'Introductory biology textbook covering basic biological concepts. Perfect for {course_code}.',
                        'url': 'https://openstax.org/details/books/concepts-biology',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    }
                ])
        
        # English courses
        elif 'engl' in subject_lower:
            if '1101' in course_num:
                default_resources.extend([
                    {
                        'title': 'Writing Guide with Handbook - OpenStax',
                        'description': f'Comprehensive writing guide for composition courses. Covers academic writing, research, and citation. Suitable for {course_code}.',
                        'url': 'https://openstax.org/details/books/writing-guide',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    },
                    {
                        'title': 'Writing Spaces: Readings on Writing',
                        'description': f'Open textbook series on writing, rhetoric, and composition. Free peer-reviewed essays for {course_code}.',
                        'url': 'https://writingspaces.org',
                        'license': 'CC BY-NC-SA',
                        'author': 'Writing Spaces',
                        'source': 'Writing Spaces',
                        'query': course_code
                    }
                ])
            elif '1102' in course_num:
                default_resources.extend([
                    {
                        'title': 'Writing and Literature - Open Textbook Library',
                        'description': f'Literature and composition textbook for second-semester English courses. Suitable for {course_code}.',
                        'url': 'https://open.umn.edu/opentextbooks/textbooks/writing-and-literature',
                        'license': 'CC BY',
                        'author': 'Various',
                        'source': 'Open Textbook Library',
                        'query': course_code
                    }
                ])
        
        # History courses
        elif 'hist' in subject_lower:
            if '2111' in course_num:
                default_resources.extend([
                    {
                        'title': 'U.S. History - OpenStax',
                        'description': f'Comprehensive U.S. History textbook covering from pre-Columbian times to present. Suitable for {course_code}.',
                        'url': 'https://openstax.org/details/books/us-history',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    }
                ])
            elif '2112' in course_num:
                default_resources.extend([
                    {
                        'title': 'U.S. History - OpenStax',
                        'description': f'U.S. History textbook covering Reconstruction to present. Suitable for {course_code}.',
                        'url': 'https://openstax.org/details/books/us-history',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    }
                ])
        
        # IT/Computing courses
        elif 'itec' in subject_lower or 'comp' in subject_lower or 'cs' in subject_lower:
            if '1001' in course_num:
                default_resources.extend([
                    {
                        'title': 'Introduction to Computer Science - OpenStax',
                        'description': f'Introduction to computer science covering programming fundamentals, algorithms, and data structures. Suitable for {course_code}.',
                        'url': 'https://openstax.org/details/books/introduction-computer-science',
                        'license': 'CC BY',
                        'author': 'OpenStax',
                        'source': 'OpenStax',
                        'query': course_code
                    },
                    {
                        'title': 'Think Python 2e',
                        'description': f'Free introduction to programming using Python. Perfect for {course_code}.',
                        'url': 'https://greenteapress.com/wp/think-python-2e/',
                        'license': 'CC BY-NC',
                        'author': 'Allen Downey',
                        'source': 'Green Tea Press',
                        'query': course_code
                    }
                ])
        
        # Arts courses
        elif 'arts' in subject_lower:
            default_resources.extend([
                {
                    'title': 'Art History - OpenStax',
                    'description': f'Art history textbook covering major art movements and works. Suitable for {course_code}.',
                    'url': 'https://openstax.org/details/books/art-history',
                    'license': 'CC BY',
                    'author': 'OpenStax',
                    'source': 'OpenStax',
                    'query': course_code
                }
            ])
        
        # If no course-specific suggestions, add general ones
        if not default_resources:
            default_resources = [
                {
                    'title': f'OER Commons - {search_term}',
                    'description': f'Open educational resources for {course_code} from OER Commons.',
                    'url': f'https://oercommons.org/hubs/{hub_id}/browse?f.search={search_term_encoded}&__hub_id={hub_id}',
                    'license': 'CC BY',
                    'author': 'OER Commons',
                    'source': 'OER Commons',
                    'query': search_term
                },
                {
                    'title': f'MERLOT - {search_term}',
                    'description': f'Educational materials for {course_code} from MERLOT.',
                    'url': f'https://www.merlot.org/merlot/materials.htm?keywords={search_term_encoded}&sort.property=relevance',
                    'license': 'CC BY',
                    'author': 'MERLOT',
                    'source': 'MERLOT',
                    'query': search_term
                }
            ]
        
        logger.info(f"Created {len(default_resources)} course-specific default suggestions for {course_code}")
        return default_resources
    
    def _generate_summary(self, evaluated_resources: List[Dict]) -> str:
        """Generate summary of evaluation results"""
        if not evaluated_resources:
            return "No OER resources found for this course. The web scrapers may need to be customized for the actual website structures. Check the logs for more details."
        
        summary = f"Found {len(evaluated_resources)} evaluated OER resources.\n\n"
        
        # Count by license status
        open_licensed = sum(1 for r in evaluated_resources 
                          if r.get('license_check', {}).get('has_open_license', False))
        summary += f"Open Licensed Resources: {open_licensed}/{len(evaluated_resources)}\n"
        
        # Average quality score
        avg_score = sum(r.get('rubric_evaluation', {}).get('overall_score', 0) 
                       for r in evaluated_resources) / len(evaluated_resources)
        summary += f"Average Quality Score: {avg_score:.1f}/5.0\n\n"
        
        # Top resources
        summary += "Top Recommended Resources:\n"
        for i, resource in enumerate(evaluated_resources[:5], 1):
            title = resource.get('resource', {}).get('title', 'Unknown')
            score = resource.get('rubric_evaluation', {}).get('overall_score', 0)
            summary += f"{i}. {title} (Score: {score:.1f}/5.0)\n"
        
        return summary
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics"""
        return self.logger.get_usage_stats()
