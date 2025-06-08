import re
import logging
from typing import Dict, List, Set, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SectionExtractor:
    """
    A utility class for extracting structured sections from medical text with strict filtering.
    """
    
    # Keywords that indicate a valid medical condition/diagnosis
    VALID_DIAGNOSIS_KEYWORDS = {
        'syndrome', 'disease', 'disorder', 'condition', 'deficiency',
        'infection', 'failure', 'dysfunction', 'impairment', 'injury',
        'hypertension', 'diabetes', 'arthritis', 'asthma', 'cancer',
        'fibrillation', 'anemia', 'insufficiency', 'stenosis'
    }

    # Keywords that indicate a valid treatment
    VALID_TREATMENT_KEYWORDS = {
        'mg', 'mcg', 'ml', 'units', 'prescribed', 'administered',
        'injection', 'infusion', 'tablet', 'capsule', 'surgery',
        'procedure', 'therapy', 'treatment', 'dose', 'daily',
        'weekly', 'monthly', 'twice', 'three times'
    }

    # Keywords that indicate valid medical history
    VALID_HISTORY_KEYWORDS = {
        'history of', 'diagnosed with', 'since', 'chronic', 'previous',
        'past medical', 'underwent', 'years ago', 'long-standing'
    }

    DIAGNOSIS_PATTERNS = [
        r"(?i)(diagnosis|impression|assessment)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(clinical\s+findings?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
    ]
    
    TREATMENT_PATTERNS = [
        r"(?i)(medications?|rx|prescriptions?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(procedures?|surgeries?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
    ]
    
    HISTORY_PATTERNS = [
        r"(?i)(medical\s+history|past\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(chronic\s+conditions?|previous\s+conditions?)[\s:]+(.*?)(?=\n\s*\n|$)",
    ]

    # Expanded phrases to remove
    FILLER_PHRASES = {
        # Patient demographics
        r"(?i)(?:mr\.|mrs\.|ms\.|dr\.)\s+[a-z]+",
        r"(?i)\d+[-\s](?:year|yr)[-\s]old",
        r"(?i)age(?:d)?\s+\d+",
        r"(?i)(?:male|female)\s+(?:patient)?",
        r"(?i)(?:married|single|divorced|widowed)",
        r"(?i)(?:employed|unemployed|retired|occupation|job|work)",
        r"(?i)(?:lives|residing)\s+(?:alone|with|in)",
        
        # Narrative/temporal phrases
        r"(?i)(?:patient|individual|client)\s+(?:is|was|has|had|reports?|states?|mentions?|notes?|complains?|presents?)",
        r"(?i)(?:denies|reports)\s+(?:any|having|using|taking)",
        r"(?i)(?:upon|on|during)\s+examination",
        r"(?i)presents?\s+(?:with|to|for)",
        r"(?i)(?:came|referred|admitted)\s+(?:to|for|with)",
        r"(?i)(?:today|yesterday|last\s+(?:week|month|year))",
        
        # Treatment narrative
        r"(?i)(?:was|is|has\s+been)\s+prescribed",
        r"(?i)please?\s+(?:take|continue|start)",
        r"(?i)advised\s+to\s+(?:take|continue|start)",
        r"(?i)recommended\s+to\s+(?:take|continue|start)",
        r"(?i)as\s+per\s+(?:doctor'?s?|physician'?s?)\s+(?:orders?|instructions?)",
        r"(?i)continue\s+(?:with|taking|using)",
        r"(?i)start\s+taking",
        r"(?i)take\s+as\s+directed",
        r"(?i)(?:follow|schedule)\s+(?:up|appointment)",
        
        # Location/facility
        r"(?i)(?:at|in)\s+(?:the\s+)?(?:hospital|clinic|office|center|ward|department)",
        r"(?i)(?:admitted|discharged)\s+(?:to|from)\s+(?:the\s+)?(?:hospital|clinic|ward)",
        r"(?i)(?:emergency|room|department|unit|floor)",
        
        # Dates and times
        r"(?i)(?:on|at)\s+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        r"(?i)(?:date\s+of|started\s+on|ended\s+on)",
        r"(?i)(?:morning|afternoon|evening|night)",
        
        # Social/lifestyle
        r"(?i)(?:smoking|alcohol|drug)\s+(?:history|use)",
        r"(?i)(?:social|family|lifestyle)\s+history",
        r"(?i)(?:diet|exercise|activity)\s+(?:level|status)",
        
        # General medical phrases
        r"(?i)(?:vital\s+signs|blood\s+pressure|temperature|pulse|respiration)",
        r"(?i)(?:normal|stable|unchanged|improved|worsened)",
        r"(?i)(?:lab|test|examination)\s+(?:results?|findings?)",
    }

    # Common bullet point and numbering patterns to clean
    BULLET_PATTERNS = {
        r"^\s*[-•*]\s*",
        r"^\s*\d+[.)]\s*",
        r"^\s*[a-z][.)]\s*",
        r"^\s*[(]?\d+[)]\s*",
    }

    def __init__(self):
        # Section header patterns
        self.section_patterns = {
            "diagnosis": [
                r"(?i)(?:final |primary |secondary |working )?diagnos[ie]s?\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)assessment\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)impression\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)problems?\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)"
            ],
            "clinical_treatment": [
                r"(?i)(?:treatment|plan|therapy|intervention|medication)\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)(?:prescribed|recommended)\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)management\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)"
            ],
            "medical_history": [
                r"(?i)(?:medical |past |family |social )?history\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)background\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)",
                r"(?i)previous\s*[:;]\s*(.*?)(?=\n\n|\n(?:[A-Z][a-z]+:)|\Z)"
            ]
        }

        # Common medical terms for each section
        self.section_terms = {
            "diagnosis": {
                "diagnosed with", "presents with", "suffering from", "complains of",
                "shows signs of", "exhibits", "demonstrates", "manifests",
                "consistent with", "suggestive of", "indicative of"
            },
            "clinical_treatment": {
                "prescribed", "administered", "given", "started on", "treated with",
                "recommended", "advised", "instructed", "directed to", "to take",
                "therapy", "treatment", "medication", "dose", "mg", "ml"
            },
            "medical_history": {
                "history of", "past medical", "previously", "chronic", "known case of",
                "has had", "underwent", "since", "ago", "prior to", "earlier"
            }
        }

        # Common filler phrases to remove
        self.filler_phrases = {
            r"(?i)please\s+",
            r"(?i)patient\s+",
            r"(?i)was\s+",
            r"(?i)is\s+",
            r"(?i)has\s+",
            r"(?i)had\s+",
            r"(?i)will\s+",
            r"(?i)should\s+",
            r"(?i)could\s+",
            r"(?i)would\s+",
            r"(?i)may\s+",
            r"(?i)might\s+",
            r"(?i)must\s+",
            r"(?i)needs?\s+to\s+",
            r"(?i)requires?\s+",
            r"(?i)recommended\s+to\s+",
            r"(?i)advised\s+to\s+"
        }

    @staticmethod
    def _extract_section(text: str, patterns: List[str]) -> Optional[str]:
        """
        Extract a section from text using a list of regex patterns.
        Returns the first match found or None if no match.
        """
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                # Get the captured content (group 2 contains the actual content)
                content = match.group(2).strip()
                if content:
                    return content
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text for better pattern matching."""
        # Replace multiple newlines with single newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Convert common list markers to standard bullet points
        text = re.sub(r'(?m)^\s*[-•*]\s*', '• ', text)
        text = re.sub(r'(?m)^\s*\d+[.)] ', '• ', text)
        # Normalize periods and semicolons
        text = re.sub(r'[.;]+(?=\s|$)', '.\n', text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _is_valid_diagnosis(self, text: str) -> bool:
        """Validate if text looks like a diagnosis."""
        text_lower = text.lower()
        
        # Must be longer than just a few characters
        if len(text) < 3:
            logger.debug(f"Diagnosis rejected - too short: {text}")
            return False
        
        # Should not be just a measurement
        if re.match(r'^\d+\s*[a-zA-Z/]+$', text):
            logger.debug(f"Diagnosis rejected - just a measurement: {text}")
            return False
        
        # Should not be just a date
        if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', text):
            logger.debug(f"Diagnosis rejected - just a date: {text}")
            return False
        
        # Check for medical condition indicators
        medical_indicators = {
            'syndrome', 'disease', 'disorder', 'condition', 'deficiency',
            'infection', 'failure', 'dysfunction', 'impairment', 'injury',
            'hypertension', 'diabetes', 'arthritis', 'asthma', 'cancer',
            'pain', 'ache', 'inflammation', 'itis', 'emia', 'osis'
        }
        
        # Accept if it contains medical terminology
        if any(indicator in text_lower for indicator in medical_indicators):
            logger.debug(f"Diagnosis accepted - contains medical term: {text}")
            return True
        
        # Accept if it matches common diagnostic patterns
        diagnostic_patterns = [
            r'\b(?:acute|chronic|recurrent|severe)\b',
            r'\b(?:type|stage|grade|phase)\s*\d+\b',
            r'\b(?:bilateral|unilateral|primary|secondary)\b',
            r'\b(?:diagnosed|confirmed|suspected|probable)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in diagnostic_patterns):
            logger.debug(f"Diagnosis accepted - matches diagnostic pattern: {text}")
            return True
        
        logger.debug(f"Diagnosis rejected - no medical indicators: {text}")
        return False

    def _is_valid_treatment(self, text: str) -> bool:
        """Validate if text looks like a treatment."""
        text_lower = text.lower()
        
        # Must be longer than just a few characters
        if len(text) < 3:
            logger.debug(f"Treatment rejected - too short: {text}")
            return False
        
        # Check for medication patterns
        med_patterns = [
            r'\b\d+\s*(?:mg|ml|mcg|g)\b',
            r'\b(?:tablet|capsule|injection|dose|pill)\b',
            r'\b(?:daily|weekly|monthly|hourly|times|prn)\b',
            r'\b(?:oral|topical|iv|im|sc)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in med_patterns):
            logger.debug(f"Treatment accepted - medication pattern: {text}")
            return True
        
        # Check for procedure/therapy patterns
        procedure_patterns = [
            r'\b(?:therapy|treatment|procedure|surgery|operation)\b',
            r'\b(?:prescribed|administered|given|started)\b',
            r'\b(?:continue|discontinue|increase|decrease)\b',
            r'\b(?:exercise|diet|lifestyle|modification)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in procedure_patterns):
            logger.debug(f"Treatment accepted - procedure pattern: {text}")
            return True
        
        logger.debug(f"Treatment rejected - no treatment indicators: {text}")
        return False

    def _is_valid_history(self, text: str) -> bool:
        """Validate if text looks like medical history."""
        text_lower = text.lower()
        
        # Must be longer than just a few characters
        if len(text) < 3:
            logger.debug(f"History rejected - too short: {text}")
            return False
        
        # Check for temporal patterns
        temporal_patterns = [
            r'\b(?:history|past|previous|prior)\b',
            r'\b(?:ago|since|for|over)\s+(?:\d+\s+)?(?:year|month|week|day)s?\b',
            r'\b(?:chronic|ongoing|long-term|recurring)\b',
            r'\b(?:diagnosed|treated|underwent|had)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in temporal_patterns):
            logger.debug(f"History accepted - temporal pattern: {text}")
            return True
        
        # Check for family history patterns
        family_patterns = [
            r'\b(?:family|mother|father|sibling|parent)\b',
            r'\b(?:maternal|paternal|hereditary|genetic)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in family_patterns):
            logger.debug(f"History accepted - family pattern: {text}")
            return True
        
        logger.debug(f"History rejected - no history indicators: {text}")
        return False

    def _clean_and_bullet(self, section_text: str, section_type: str) -> List[str]:
        """Clean section text and convert to bullet points with strict filtering."""
        if not section_text:
            return []

        # Split into lines
        lines = re.split(r'[.;]\s*|\n+', section_text)
        
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:  # Ignore very short lines
                continue

            # Remove bullet points and numbering
            for pattern in self.BULLET_PATTERNS:
                line = re.sub(pattern, '', line)

            # Remove all filler phrases
            for phrase in self.FILLER_PHRASES:
                line = re.sub(phrase, '', line)

            # Clean up the line
            line = line.strip()
            line = re.sub(r'\s+', ' ', line)
            
            # Skip common words and short phrases
            if len(line) < 5 or line.lower() in {'none', 'nil', 'no', 'yes', 'normal', 'stable', 'unchanged'}:
                continue

            # Skip lines that are just dates, numbers or measurements
            if re.match(r'^[\d\s\-\/\.]+$', line) or re.match(r'^\d+\s*(?:mg|ml|units?|tabs?|caps?)$', line):
                continue

            # Apply strict section-specific validation
            if section_type == 'diagnosis' and not self._is_valid_diagnosis(line):
                continue
            elif section_type == 'treatment' and not self._is_valid_treatment(line):
                continue
            elif section_type == 'history' and not self._is_valid_history(line):
                continue

            if line:
                # Format consistently
                line = line.strip().rstrip('.')
                if section_type == 'treatment' and not line.lower().startswith(('prescribed', 'administered', 'given')):
                    line = f"Prescribed {line}"
                cleaned_lines.append(line)

        # Remove duplicates while preserving order
        seen = set()
        filtered_lines = []
        for line in cleaned_lines:
            line_lower = line.lower()
            if line_lower not in seen:
                seen.add(line_lower)
                filtered_lines.append(line)

        return filtered_lines

    def extract_sections(self, text: str) -> Dict[str, List[str]]:
        """Extract sections from medical text using patterns and term matching."""
        logger.info("Starting section extraction")
        logger.debug("Input text: %s", text[:200])  # Log first 200 chars
        
        # Initialize results
        sections = {
            "diagnosis": [],
            "clinical_treatment": [],
            "medical_history": []
        }
        
        # First try pattern-based extraction
        for section_type, patterns in self.section_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    content = match.group(1).strip()
                    if content:
                        logger.debug(f"Found {section_type} section with pattern: {pattern}")
                        sections[section_type].extend(self._split_into_items(content))
        
        # If pattern matching didn't find much, try term-based extraction
        if not any(sections.values()):
            logger.info("Pattern matching found no sections, trying term-based extraction")
            sections = self._extract_by_terms(text)
        
        # Clean and validate each section
        for section_type in sections:
            original_count = len(sections[section_type])
            sections[section_type] = self._clean_and_validate(sections[section_type], section_type)
            logger.info(f"{section_type}: {original_count} items found, {len(sections[section_type])} valid")
            logger.debug(f"{section_type} items: {sections[section_type]}")
        
        return sections

    def _normalize_text(self, text: str) -> str:
        """Normalize text for better pattern matching."""
        # Add newlines around potential section headers
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1\n\n\2', text)
        
        # Ensure colon after common section headers
        text = re.sub(r'(?i)(\b(?:diagnosis|assessment|plan|history)\s*)(?=[A-Z])', r'\1:\n', text)
        
        # Normalize line endings
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        
        # Remove multiple spaces and normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def _split_into_items(self, text: str) -> List[str]:
        """Split text into individual items."""
        # Split on common delimiters
        items = []
        
        # First try splitting on bullet points and numbers
        if re.search(r'(?m)^[\s-]*[•\-\d.)]', text):
            for line in text.split('\n'):
                line = re.sub(r'^[\s-]*[•\-\d.)][\s-]*', '', line)
                if line.strip():
                    items.append(line.strip())
        else:
            # Split on sentence endings and semicolons
            splits = re.split(r'[.;]\s+(?=[A-Z]|$)', text)
            items.extend(split.strip() for split in splits if split.strip())
        
        return items

    def _extract_by_terms(self, text: str) -> Dict[str, List[str]]:
        """Extract sections by looking for characteristic terms."""
        sections = {
            "diagnosis": [],
            "clinical_treatment": [],
            "medical_history": []
        }
        
        # First try to split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        # Process each sentence
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check each section's terms
            matched = False
            for section_type, terms in self.section_terms.items():
                # Check if any term appears in the sentence
                if any(term.lower() in sentence.lower() for term in terms):
                    # Clean up the sentence
                    cleaned = sentence
                    for phrase in self.filler_phrases:
                        cleaned = re.sub(phrase, '', cleaned)
                    cleaned = cleaned.strip()
                    
                    # Add to appropriate section if it's valid
                    if section_type == "diagnosis" and self._is_valid_diagnosis(cleaned):
                        sections["diagnosis"].append(cleaned)
                        matched = True
                        break
                    elif section_type == "clinical_treatment" and self._is_valid_treatment(cleaned):
                        sections["clinical_treatment"].append(cleaned)
                        matched = True
                        break
                    elif section_type == "medical_history" and self._is_valid_history(cleaned):
                        sections["medical_history"].append(cleaned)
                        matched = True
                        break
            
            # If sentence wasn't matched but contains medical terms, try to classify it
            if not matched:
                # Look for medication patterns
                if re.search(r'\b\d+\s*(?:mg|ml|mcg|g)\b', sentence, re.IGNORECASE):
                    cleaned = sentence
                    for phrase in self.filler_phrases:
                        cleaned = re.sub(phrase, '', cleaned)
                    cleaned = cleaned.strip()
                    if cleaned:
                        sections["clinical_treatment"].append(cleaned)
                
                # Look for temporal patterns suggesting history
                elif re.search(r'\b(?:since|for|ago|past|history|previous)\b', sentence, re.IGNORECASE):
                    cleaned = sentence
                    for phrase in self.filler_phrases:
                        cleaned = re.sub(phrase, '', cleaned)
                    cleaned = cleaned.strip()
                    if cleaned:
                        sections["medical_history"].append(cleaned)
                
                # Look for diagnostic patterns
                elif re.search(r'\b(?:diagnosed|presents|shows|exhibits|symptoms?|signs?)\b', sentence, re.IGNORECASE):
                    cleaned = sentence
                    for phrase in self.filler_phrases:
                        cleaned = re.sub(phrase, '', cleaned)
                    cleaned = cleaned.strip()
                    if cleaned:
                        sections["diagnosis"].append(cleaned)
        
        return sections

    def _clean_and_validate(self, items: List[str], section_type: str) -> List[str]:
        """Clean and validate items for a specific section."""
        cleaned = []
        seen = set()
        
        for item in items:
            # Remove filler phrases
            for phrase in self.filler_phrases:
                item = re.sub(phrase, '', item)
            
            # Clean up the item
            item = item.strip()
            item = re.sub(r'\s+', ' ', item)
            
            # Skip if too short or duplicate
            if len(item) < 5 or item.lower() in seen:
                continue
            
            # Validate based on section type
            if section_type == "diagnosis" and self._is_valid_diagnosis(item):
                cleaned.append(item)
                seen.add(item.lower())
            elif section_type == "clinical_treatment" and self._is_valid_treatment(item):
                cleaned.append(item)
                seen.add(item.lower())
            elif section_type == "medical_history" and self._is_valid_history(item):
                cleaned.append(item)
                seen.add(item.lower())
        
        return cleaned 