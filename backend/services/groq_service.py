import groq
from config import Config
import json
import re
from datetime import datetime
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class GroqService:
    """Groq AI service for file analysis"""
    
    def __init__(self):
        self.available_models = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile", 
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        self.default_model = "llama-3.1-8b-instant"
        
        if Config.GROQ_API_KEY:
            try:
                self.client = groq.Groq(api_key=Config.GROQ_API_KEY)
                # Test connection with the default model
                test_response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": "Say 'Hello'"}],
                    model=self.default_model,
                    max_tokens=5
                )
                logger.info(f"✅ Groq API service initialized successfully using model: {test_response.model}")
                print("✅ Groq API service initialized and working!")
            except Exception as e:
                logger.error(f"❌ Groq API initialization failed: {e}")
                print(f"❌ Groq API initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ GROQ_API_KEY not found, AI features disabled")
            print("⚠️ GROQ_API_KEY not found, AI features disabled")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Groq service is available"""
        return self.client is not None
    
    def analyze_text(self, text: str, filename: str, model: str = None) -> dict:
        """Analyze text using Groq AI with fallback models"""
        if not self.is_available() or not text:
            return None
        
        if model is None:
            model = self.default_model
        
        # Try with the specified model first
        result = self._analyze_with_model(text, filename, model)
        
        # If analysis failed or keywords are empty, try fallback models
        if not result or not result.get('keywords') or len(result.get('keywords', [])) < 3:
            logger.warning(f"Primary model {model} produced insufficient results, trying fallback models")
            
            for fallback_model in self.available_models:
                if fallback_model != model:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    fallback_result = self._analyze_with_model(text, filename, fallback_model)
                    if fallback_result and fallback_result.get('keywords') and len(fallback_result.get('keywords', [])) >= 3:
                        logger.info(f"Fallback model {fallback_model} produced better results")
                        result = fallback_result
                        break
        
        # If still no keywords, generate them from the text
        if result and (not result.get('keywords') or len(result.get('keywords', [])) < 3):
            logger.info("Generating keywords from text content")
            generated_keywords = self._generate_keywords_from_text(text, filename)
            result['keywords'] = generated_keywords
            result['keywords_source'] = 'generated'
        
        return result
    
    def _analyze_with_model(self, text: str, filename: str, model: str) -> dict:
        """Analyze text with a specific model"""
        try:
            content_preview = text[:4000]  # Limit context window
            
            # Enhanced prompt with better instructions for keywords
            prompt = self._build_analysis_prompt(content_preview, filename)
            
            logger.info(f"Sending request to Groq model: {model}")
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=0.3,  # Slightly higher for more creative keywords
                max_tokens=1024,
                top_p=0.9,
                stream=False
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"Groq raw response: {result_text[:500]}...")
            
            # Parse JSON response
            analysis_result = self._parse_response(result_text, filename)
            
            # Ensure all required fields are present
            analysis_result = self._ensure_analysis_fields(analysis_result, text, filename)
            analysis_result["analysis_date"] = datetime.utcnow().isoformat()
            analysis_result["model_used"] = model
            
            logger.info(f"Analysis completed with model {model}, keywords count: {len(analysis_result.get('keywords', []))}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in Groq analysis with model {model}: {e}")
            return None
    
    def _build_analysis_prompt(self, text: str, filename: str) -> str:
        """Build a more effective prompt for analysis"""
        file_extension = filename.split('.')[-1].upper() if '.' in filename else 'UNKNOWN'
        
        return f"""Analyze the following content from the file "{filename}" (file type: {file_extension}) and provide a comprehensive analysis.

IMPORTANT: You MUST return a valid JSON object with exactly these three fields:
1. "summary": A concise 2-3 sentence summary of the main content
2. "keywords": An array of 5-10 relevant keywords or key phrases that accurately represent the content. Make sure keywords are specific, meaningful, and cover different aspects of the content.
3. "caption": A brief, descriptive one-sentence caption

GUIDELINES FOR KEYWORDS:
- Provide between 5-10 keywords
- Make keywords specific and relevant to the content
- Include both broad and specific terms
- Use phrases if they better represent concepts
- Avoid generic words like "document", "file", "content"
- Focus on the main topics, entities, and themes

CONTENT TO ANALYZE:
{text}

EXAMPLE RESPONSE:
{{
  "summary": "This document discusses the impact of climate change on coastal ecosystems, highlighting rising sea levels and biodiversity loss. It presents recent research findings and conservation strategies.",
  "keywords": ["climate change", "coastal ecosystems", "sea level rise", "biodiversity loss", "conservation strategies", "marine biology", "environmental impact"],
  "caption": "Analysis of climate change effects on coastal biodiversity and conservation approaches."
}}

YOUR JSON RESPONSE:"""
    
    def _parse_response(self, result_text: str, filename: str) -> dict:
        """Parse the response with multiple fallback strategies"""
        # Strategy 1: Direct JSON parsing
        try:
            # Clean the response - remove markdown code blocks if present
            clean_text = result_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.warning("Direct JSON parsing failed, trying structured parsing")
            pass
        
        # Strategy 2: Extract JSON from text using regex
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning("Regex JSON extraction failed")
                pass
        
        # Strategy 3: Structured parsing of non-JSON response
        logger.info("Using structured parsing for non-JSON response")
        return self._parse_structured_response(result_text, filename)
    
    def _parse_structured_response(self, result_text: str, filename: str) -> dict:
        """Parse structured but non-JSON responses"""
        lines = [line.strip() for line in result_text.split('\n') if line.strip()]
        
        summary = ""
        keywords = []
        caption = ""
        
        current_section = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect sections
            if any(term in line_lower for term in ['summary:', 'analysis:', 'overview:']):
                current_section = 'summary'
                summary = line.split(':', 1)[-1].strip() if ':' in line else ""
            elif any(term in line_lower for term in ['keyword', 'key term', 'key point']):
                current_section = 'keywords'
                if ':' in line:
                    keyword_part = line.split(':', 1)[-1].strip()
                    self._extract_keywords_from_line(keyword_part, keywords)
            elif any(term in line_lower for term in ['caption:', 'description:', 'title:']):
                current_section = 'caption'
                caption = line.split(':', 1)[-1].strip() if ':' in line else line
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                # Bullet points - often used for keywords
                if current_section == 'keywords' or 'keyword' in line_lower:
                    keyword = line[1:].strip()
                    if keyword and len(keyword) > 2:
                        keywords.append(keyword)
            elif current_section == 'summary' and line and not summary:
                summary = line
            elif current_section == 'caption' and line and not caption:
                caption = line
            elif current_section == 'keywords' and line:
                self._extract_keywords_from_line(line, keywords)
        
        # If we found a JSON-like structure but couldn't parse it, try to extract more
        if not keywords:
            # Look for arrays in the text
            array_matches = re.findall(r'\[(.*?)\]', result_text)
            for match in array_matches:
                potential_keywords = [k.strip().strip('"\'') for k in match.split(',')]
                potential_keywords = [k for k in potential_keywords if k and len(k) > 2]
                if potential_keywords:
                    keywords.extend(potential_keywords)
                    break
        
        return {
            "summary": summary,
            "keywords": keywords[:10],  # Limit to 10 keywords
            "caption": caption
        }
    
    def _extract_keywords_from_line(self, line: str, keywords_list: list):
        """Extract keywords from a line of text"""
        # Remove numbers and special characters, split by common separators
        clean_line = re.sub(r'[0-9]', '', line)
        parts = re.split(r'[,;|]', clean_line)
        
        for part in parts:
            keyword = part.strip().strip('"-•*')
            if (keyword and len(keyword) > 2 and 
                keyword.lower() not in ['and', 'the', 'for', 'with', 'that', 'this'] and
                keyword not in keywords_list):
                keywords_list.append(keyword)
    
    def _generate_keywords_from_text(self, text: str, filename: str, max_keywords: int = 8) -> list:
        """Generate keywords from text content when AI fails"""
        try:
            # Extract meaningful words (3+ characters, alphanumeric)
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            
            # Common stop words to exclude
            stop_words = {
                'the', 'and', 'for', 'with', 'that', 'this', 'have', 'from', 'they', 'what',
                'when', 'where', 'which', 'were', 'their', 'there', 'been', 'because', 'into',
                'your', 'have', 'more', 'will', 'about', 'after', 'also', 'than', 'then',
                'some', 'such', 'only', 'other', 'these', 'them', 'would', 'could', 'should',
                'much', 'very', 'upon', 'should', 'each', 'both', 'while', 'like', 'said'
            }
            
            # Filter stop words and count frequency
            filtered_words = [word for word in words if word not in stop_words]
            word_freq = Counter(filtered_words)
            
            # Get most common words
            common_words = word_freq.most_common(max_keywords * 2)  # Get extra for filtering
            
            # Filter and format keywords
            keywords = []
            for word, freq in common_words:
                if (freq >= 2 and  # Appears at least twice
                    len(word) >= 4 and  # At least 4 characters
                    word not in keywords and
                    len(keywords) < max_keywords):
                    keywords.append(word.title())
            
            # If we don't have enough keywords, be less strict
            if len(keywords) < 5:
                for word, freq in common_words:
                    if (freq >= 1 and
                        len(word) >= 3 and
                        word not in keywords and
                        len(keywords) < max_keywords):
                        keywords.append(word.title())
            
            # Add filename-based keyword as fallback
            if len(keywords) < 3:
                base_name = filename.split('.')[0]
                if base_name and base_name not in keywords:
                    keywords.append(base_name)
            
            logger.info(f"Generated {len(keywords)} keywords from text analysis")
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.error(f"Error generating keywords from text: {e}")
            # Ultimate fallback
            return [filename.split('.')[0], "Document", "Content"]
    
    def _ensure_analysis_fields(self, analysis_result: dict, text: str, filename: str) -> dict:
        """Ensure all required fields are present with meaningful content"""
        if not analysis_result:
            analysis_result = {}
        
        file_extension = filename.split('.')[-1].upper() if '.' in filename else 'FILE'
        
        # Ensure summary
        if not analysis_result.get('summary'):
            text_preview = text[:200] + '...' if len(text) > 200 else text
            analysis_result['summary'] = f"This {file_extension.lower()} file contains: {text_preview}"
        
        # Ensure keywords (with fallback generation)
        if not analysis_result.get('keywords') or len(analysis_result.get('keywords', [])) < 3:
            generated_keywords = self._generate_keywords_from_text(text, filename)
            analysis_result['keywords'] = generated_keywords
            if 'keywords_source' not in analysis_result:
                analysis_result['keywords_source'] = 'fallback'
        
        # Ensure caption
        if not analysis_result.get('caption'):
            keyword_str = ', '.join(analysis_result.get('keywords', [])[:3])
            analysis_result['caption'] = f"{file_extension} file: {keyword_str}"
        
        # Clean and validate keywords
        if analysis_result.get('keywords'):
            cleaned_keywords = []
            for keyword in analysis_result['keywords']:
                if isinstance(keyword, str) and keyword.strip():
                    cleaned_keyword = keyword.strip()
                    if (len(cleaned_keyword) >= 2 and 
                        cleaned_keyword.lower() not in ['na', 'n/a', 'none', ''] and
                        cleaned_keyword not in cleaned_keywords):
                        cleaned_keywords.append(cleaned_keyword)
            analysis_result['keywords'] = cleaned_keywords[:10]  # Limit to 10
        
        return analysis_result
    
    def get_available_models(self) -> list:
        """Get list of available models"""
        return self.available_models.copy()