import re

class EmailValidator:
    @staticmethod
    def is_valid(email: str) -> bool:
        """
        Validate if a string is a properly formatted email address
        
        Args:
            email: The email address to validate
            
        Returns:
            True if the email is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
            
        # Email validation regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))