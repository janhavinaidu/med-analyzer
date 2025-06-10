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
        'fibrillation', 'anemia', 'insufficiency', 'stenosis',
        # Add more medical conditions
        'pain', 'inflammation', 'fracture', 'lesion', 'mass',
        'tumor', 'cyst', 'ulcer', 'bleeding', 'edema',
        'abnormal', 'acute', 'chronic', 'severe', 'mild',
        'moderate', 'recurrent', 'persistent', 'progressive'
    }

    # Keywords that indicate a valid treatment
    VALID_TREATMENT_KEYWORDS = {
        'mg', 'mcg', 'ml', 'units', 'prescribed', 'administered',
        'injection', 'infusion', 'tablet', 'capsule', 'surgery',
        'procedure', 'therapy', 'treatment', 'dose', 'daily',
        'weekly', 'monthly', 'twice', 'three times',
        # Add more treatment terms
        'medication', 'medicine', 'drug', 'antibiotic',
        'oral', 'topical', 'intravenous', 'iv', 'im',
        'patch', 'cream', 'ointment', 'solution', 'inhaler',
        'drops', 'spray', 'suppository', 'suspension'
    }

    # Keywords that indicate valid medical history
    VALID_HISTORY_KEYWORDS = {
        'history of', 'diagnosed with', 'since', 'chronic', 'previous',
        'past medical', 'underwent', 'years ago', 'long-standing',
        # Add more history terms
        'family history', 'surgical history', 'social history',
        'prior', 'earlier', 'former', 'initially', 'originally',
        'first diagnosed', 'onset', 'started', 'developed',
        'childhood', 'adolescence', 'adulthood', 'known case of'
    }

    DIAGNOSIS_PATTERNS = [
        r"(?i)(diagnosis|impression|assessment)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(clinical\s+findings?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(chief\s+complaint|reason\s+for\s+visit)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(presenting\s+symptoms?|primary\s+concern)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
    ]
    
    TREATMENT_PATTERNS = [
        r"(?i)(medications?|rx|prescriptions?|drugs?|treatment\s+plan)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(procedures?|surgeries?|interventions?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(current\s+medications?|active\s+medications?|ongoing\s+treatment)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(prescribed\s+medications?|current\s+prescriptions?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(treatment\s+regimen|therapeutic\s+plan)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)"
    ]
    
    HISTORY_PATTERNS = [
        r"(?i)(medical\s+history|past\s+history|past\s+medical\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(chronic\s+conditions?|previous\s+conditions?|ongoing\s+conditions?)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(past\s+(?:surgical|medical|health)\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(significant\s+(?:medical|health)\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(previous\s+(?:medical|health)\s+conditions?)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(family\s+(?:medical|health)\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(social\s+history|lifestyle\s+history)[\s:]+(.*?)(?=\n\s*\n|$)"
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
            'pain', 'ache', 'inflammation', 'itis', 'emia', 'osis',
            # Add more medical indicators
            'abnormal', 'acute', 'chronic', 'severe', 'mild',
            'moderate', 'recurrent', 'persistent', 'progressive',
            'fracture', 'lesion', 'mass', 'tumor', 'cyst',
            'ulcer', 'bleeding', 'edema', 'insufficiency'
        }
        
        # Accept if it contains medical terminology
        if any(indicator in text_lower for indicator in medical_indicators):
            logger.debug(f"Diagnosis accepted - contains medical term: {text}")
            return True
        
        # Accept if it matches common diagnostic patterns
        diagnostic_patterns = [
            r'\b(?:acute|chronic|recurrent|severe|mild|moderate)\b',
            r'\b(?:type|stage|grade|phase)\s*\d+\b',
            r'\b(?:bilateral|unilateral|primary|secondary)\b',
            r'\b(?:diagnosed|confirmed|suspected|probable|possible)\b',
            r'\b(?:early|late|advanced|initial|terminal)\b',
            r'\b(?:symptomatic|asymptomatic|active|inactive)\b',
            r'\b(?:stable|unstable|controlled|uncontrolled)\b',
            r'\b(?:positive|negative)\s+(?:for|test)\b'
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
        
        # Check for medication patterns (more lenient)
        med_patterns = [
            r'\b\d+\s*(?:mg|ml|mcg|g|units?|tabs?|caps?)\b',  # Dosage patterns
            r'\b(?:tablet|capsule|injection|dose|pill|patch|cream|gel|solution|syrup|inhaler)\b',  # Forms
            r'\b(?:daily|weekly|monthly|hourly|times|prn|bid|tid|qid|qd|qw|prn)\b',  # Frequency
            r'\b(?:oral|topical|iv|im|sc|po|pr)\b',  # Routes
            r'\b(?:prescribed|taking|given|started|administered|recommended)\b',  # Administration
            r'\b(?:paracetamol|ibuprofen|aspirin|acetaminophen)\b',  # Common medications
            r'\b(?:antibiotic|antiviral|painkiller|supplement)\b',  # Medication types
            r'\b(?:therapy|treatment|procedure|surgery|operation)\b',  # Procedures
            r'\b(?:continue|discontinue|increase|decrease|adjust)\b',  # Instructions
            r'\b(?:exercise|diet|lifestyle|modification)\b'  # Other treatments
        ]
        
        if any(re.search(pattern, text_lower) for pattern in med_patterns):
            logger.debug(f"Treatment accepted - medication pattern: {text}")
            return True
        
        # Check for common medication endings
        med_endings = ['zole', 'olol', 'oxin', 'icin', 'mycin', 'dronate', 'sartan', 'pril', 'statin']
        if any(text_lower.endswith(ending) for ending in med_endings):
            logger.debug(f"Treatment accepted - medication ending: {text}")
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
        
        # Check for temporal patterns (more lenient)
        temporal_patterns = [
            r'\b(?:history|past|previous|prior|earlier|former)\b',
            r'\b(?:ago|since|for|over)\s+(?:\d+\s+)?(?:year|month|week|day)s?\b',
            r'\b(?:chronic|ongoing|long-term|recurring|persistent)\b',
            r'\b(?:diagnosed|treated|underwent|had|developed|experienced)\b',
            r'\b(?:childhood|adolescence|adulthood)\b',
            r'\b(?:in|during|at)\s+(?:19|20)\d{2}\b',  # Years
            r'\b(?:started|began|onset|initially)\b',
            r'\b(?:known|case|of)\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in temporal_patterns):
            logger.debug(f"History accepted - temporal pattern: {text}")
            return True
        
        # Check for family history patterns
        family_patterns = [
            r'\b(?:family|mother|father|sibling|parent|brother|sister)\b',
            r'\b(?:maternal|paternal|hereditary|genetic|inherited)\b',
            r'\b(?:runs|history)\s+in\s+(?:the\s+)?family\b'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in family_patterns):
            logger.debug(f"History accepted - family pattern: {text}")
            return True
        
        # Check for medical condition keywords that might indicate history
        medical_conditions = self.VALID_DIAGNOSIS_KEYWORDS
        if any(keyword in text_lower for keyword in medical_conditions):
            logger.debug(f"History accepted - contains medical condition: {text}")
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
        """Extract sections from medical text using a multi-stage approach."""
        logger.info("Starting enhanced section extraction")
        
        # Initialize results
        sections = {
            "diagnosis": [],
            "clinical_treatment": [],
            "medical_history": []
        }
        
        # Normalize text for better processing
        text = self._normalize_text(text)
        
        # Stage 1: Pattern-based extraction
        logger.info("Stage 1: Pattern-based extraction")
        for section_type, patterns in self.section_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    content = match.group(1).strip()
                    if content:
                        items = self._split_into_items(content)
                        sections[section_type].extend(items)
                        logger.debug(f"Found {len(items)} items in {section_type} section")

        # Stage 2: Sentence-level analysis
        logger.info("Stage 2: Sentence-level analysis")
        sentences = re.split(r'[.!?]+\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check each sentence for section indicators
            sentence_lower = sentence.lower()
            
            # Diagnosis indicators
            if any(term in sentence_lower for term in self.section_terms["diagnosis"]):
                sections["diagnosis"].append(sentence)
                
            # Treatment indicators
            if any(term in sentence_lower for term in self.section_terms["clinical_treatment"]):
                sections["clinical_treatment"].append(sentence)
                
            # History indicators
            if any(term in sentence_lower for term in self.section_terms["medical_history"]):
                sections["medical_history"].append(sentence)

        # Stage 3: Entity-based extraction
        logger.info("Stage 3: Entity-based extraction")
        for sentence in sentences:
            # Look for medication patterns
            if re.search(r'\b\d+\s*(?:mg|ml|mcg|g)\b', sentence) or \
               re.search(r'\b(?:tablet|capsule|injection|pill)\b', sentence.lower()):
                sections["clinical_treatment"].append(sentence)
            
            # Look for temporal patterns indicating history
            if re.search(r'\b(?:ago|since|for|over)\s+(?:\d+\s+)?(?:year|month|week|day)s?\b', sentence.lower()) or \
               re.search(r'\b(?:in|during)\s+(?:19|20)\d{2}\b', sentence.lower()):
                sections["medical_history"].append(sentence)
            
            # Look for diagnostic patterns
            if re.search(r'\b(?:diagnosed|confirmed|suspected|shows|indicates|reveals)\b', sentence.lower()):
                sections["diagnosis"].append(sentence)

        # Stage 4: Clean and validate each section
        logger.info("Stage 4: Cleaning and validation")
        for section_type in sections:
            # Remove duplicates while preserving order
            seen = set()
            cleaned_items = []
            for item in sections[section_type]:
                item = self._clean_text(item)
                item_lower = item.lower()
                
                if item and item_lower not in seen:
                    # Validate based on section type
                    if section_type == "diagnosis" and self._is_valid_diagnosis(item):
                        cleaned_items.append(item)
                        seen.add(item_lower)
                    elif section_type == "clinical_treatment" and self._is_valid_treatment(item):
                        cleaned_items.append(item)
                        seen.add(item_lower)
                    elif section_type == "medical_history" and self._is_valid_history(item):
                        cleaned_items.append(item)
                        seen.add(item_lower)
            
            sections[section_type] = cleaned_items
            logger.info(f"{section_type}: Found {len(cleaned_items)} valid items")

        # Stage 5: Cross-reference and reorganize
        logger.info("Stage 5: Cross-reference and reorganize")
        # Move misplaced items to correct sections
        for section_type, items in list(sections.items()):
            for item in items[:]:
                if section_type != "diagnosis" and self._is_valid_diagnosis(item):
                    sections["diagnosis"].append(item)
                    sections[section_type].remove(item)
                elif section_type != "clinical_treatment" and self._is_valid_treatment(item):
                    sections["clinical_treatment"].append(item)
                    sections[section_type].remove(item)
                elif section_type != "medical_history" and self._is_valid_history(item):
                    sections["medical_history"].append(item)
                    sections[section_type].remove(item)

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
        """Split text into individual items with improved handling."""
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
            
            # If we still don't have items, try splitting on commas for lists
            if len(items) <= 1 and ',' in text:
                items = [item.strip() for item in text.split(',') if item.strip()]
        
        # Additional cleaning
        cleaned_items = []
        for item in items:
            # Remove common prefixes
            item = re.sub(r'^[-•*]\s*', '', item)
            item = re.sub(r'^\d+[.)] ', '', item)
            
            # Remove redundant whitespace
            item = re.sub(r'\s+', ' ', item)
            
            if item.strip():
                cleaned_items.append(item.strip())
        
        return cleaned_items 