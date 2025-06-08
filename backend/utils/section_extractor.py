import re
from typing import Dict, List, Optional, Set

class SectionExtractor:
    """
    A utility class for extracting structured sections from medical text.
    """
    
    DIAGNOSIS_PATTERNS = [
        r"(?i)(diagnosis|impression|assessment)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(chief\s+complaint|presenting\s+problem)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
        r"(?i)(clinical\s+findings?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:treatment|history|medications?|rx|plan|follow|instructions)|$)",
    ]
    
    TREATMENT_PATTERNS = [
        r"(?i)(treatment|therapy|intervention)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(medications?|rx|prescriptions?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
        r"(?i)(procedures?|surgeries?)[\s:]+(.*?)(?=\n\s*\n|\n\s*(?:history|follow|plan|instructions)|$)",
    ]
    
    HISTORY_PATTERNS = [
        r"(?i)(medical\s+history|past\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(previous\s+conditions?|past\s+medical\s+problems?)[\s:]+(.*?)(?=\n\s*\n|$)",
        r"(?i)(family\s+history|social\s+history)[\s:]+(.*?)(?=\n\s*\n|$)",
    ]

    # Common filler phrases to remove
    FILLER_PHRASES = {
        r"(?i)patient\s+(?:was|is|has been)\s+",
        r"(?i)was\s+prescribed\s+",
        r"(?i)please?\s+",
        r"(?i)advised\s+to\s+",
        r"(?i)recommended\s+to\s+",
        r"(?i)as\s+per\s+(?:doctor'?s?|physician'?s?)\s+(?:orders?|instructions?)",
        r"(?i)continue\s+(?:with|taking)",
        r"(?i)start\s+taking",
        r"(?i)take\s+as\s+directed",
        r"(?i)(?:patient|individual)\s+(?:reports?|states?|mentions?)",
        r"(?i)(?:denies|reports)\s+(?:any|having)",
        r"(?i)(?:upon|on)\s+examination",
    }

    # Common bullet point and numbering patterns to clean
    BULLET_PATTERNS = {
        r"^\s*[-•*]\s*",
        r"^\s*\d+[.)]\s*",
        r"^\s*[a-z][.)]\s*",
        r"^\s*[(]?\d+[)]\s*",
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

    def _clean_and_bullet(self, section_text: str) -> List[str]:
        """
        Clean section text and convert to bullet points.
        Removes filler phrases and keeps only relevant medical information.
        """
        if not section_text:
            return []

        # Split into lines
        lines = re.split(r'[.;]\s*|\n+', section_text)
        
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove bullet points and numbering
            for pattern in self.BULLET_PATTERNS:
                line = re.sub(pattern, '', line)

            # Remove filler phrases
            for phrase in self.FILLER_PHRASES:
                line = re.sub(phrase, '', line)

            # Clean up the line
            line = line.strip()
            line = re.sub(r'\s+', ' ', line)
            
            # Skip if line is too short or just contains common words
            if len(line) < 3 or line.lower() in {'none', 'nil', 'no', 'yes', 'normal'}:
                continue

            # Skip lines that are just dates or numbers
            if re.match(r'^[\d\s\-\/\.]+$', line):
                continue

            if line:
                cleaned_lines.append(line)

        # Remove duplicates while preserving order
        seen = set()
        return [x for x in cleaned_lines if not (x.lower() in seen or seen.add(x.lower()))]

    def extract_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Extract structured sections from medical text.
        
        Args:
            text (str): The medical text to process
            
        Returns:
            Dict containing the extracted sections:
            - diagnosis (List[str]): List of diagnoses and clinical findings
            - clinical_treatment (List[str]): List of treatments, medications, and procedures
            - medical_history (List[str]): List of relevant medical history items
        """
        cleaned_text = self._clean_text(text)
        
        # Extract each section
        diagnosis = self._extract_section(cleaned_text, self.DIAGNOSIS_PATTERNS)
        treatment = self._extract_section(cleaned_text, self.TREATMENT_PATTERNS)
        history = self._extract_section(cleaned_text, self.HISTORY_PATTERNS)
        
        # Clean and convert each section to bullet points
        return {
            "diagnosis": self._clean_and_bullet(diagnosis),
            "clinical_treatment": self._clean_and_bullet(treatment),
            "medical_history": self._clean_and_bullet(history)
        } 