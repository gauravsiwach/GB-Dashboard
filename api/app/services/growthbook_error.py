class GrowthBookError(Exception):
    """Custom exception for GrowthBook API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)
    
    def __str__(self):
        if self.status_code:
            return f"GrowthBookError {self.status_code}: {self.message}"
        return f"GrowthBookError: {self.message}"
