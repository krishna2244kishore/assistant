"""
Utility functions for API responses and error handling.
"""
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Type, Callable
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing_extensions import Literal

from .config import logger

# Type variables for generic response models
T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response model."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None

class ApiError(Exception):
    """Base exception for API errors."""
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str = "An error occurred",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class NotFoundError(ApiError):
    """Raised when a resource is not found."""
    def __init__(self, resource: str = "Resource", **kwargs):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"{resource} not found",
            error_code="not_found",
            **kwargs
        )

class UnauthorizedError(ApiError):
    """Raised when authentication is required or has failed."""
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code="unauthorized",
            **kwargs
        )

class ForbiddenError(ApiError):
    """Raised when the user doesn't have permission to access a resource."""
    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            error_code="forbidden",
            **kwargs
        )

class ValidationError(ApiError):
    """Raised when input validation fails."""
    def __init__(self, errors: List[Dict[str, Any]], **kwargs):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation error",
            error_code="validation_error",
            details={"errors": errors},
            **kwargs
        )

def success_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
    **kwargs
) -> JSONResponse:
    """
    Create a successful API response.
    
    Args:
        data: The response data
        message: Optional success message
        status_code: HTTP status code (default: 200)
        **kwargs: Additional fields to include in the response
        
    Returns:
        JSONResponse: Formatted API response
    """
    response_data = {
        "success": True,
        "data": data,
        "message": message,
        **kwargs
    }
    
    # Remove None values
    response_data = {k: v for k, v in response_data.items() if v is not None}
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )

def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs
) -> JSONResponse:
    """
    Create an error API response.
    
    Args:
        message: Error message
        status_code: HTTP status code (default: 400)
        error_code: Optional error code for programmatic handling
        details: Additional error details
        **kwargs: Additional fields to include in the response
        
    Returns:
        JSONResponse: Formatted error response
    """
    response_data = {
        "success": False,
        "error": message,
        "error_code": error_code,
        "details": details or {},
        **kwargs
    }
    
    # Remove None values
    response_data = {k: v for k, v in response_data.items() if v is not None}
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )

def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator to handle exceptions and return appropriate API responses.
    
    Args:
        func: The function to wrap
        
    Returns:
        Callable: Wrapped function with exception handling
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ApiError as e:
            logger.error(f"API error: {e}", exc_info=True)
            return error_response(
                message=e.message,
                status_code=e.status_code,
                error_code=e.error_code,
                details=e.details
            )
        except ValidationError as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return error_response(
                message="Validation error",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="validation_error",
                details={"errors": e.errors()}
            )
        except HTTPException as e:
            # Re-raise FastAPI HTTP exceptions
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return error_response(
                message="An unexpected error occurred",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="internal_server_error"
            )
    
    # Preserve the original function's name and docstring
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    
    return wrapper

def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a paginated response.
    
    Args:
        items: List of items in the current page
        total: Total number of items
        page: Current page number (1-based)
        page_size: Number of items per page
        **kwargs: Additional metadata to include
        
    Returns:
        Dict: Paginated response data
    """
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
        **kwargs
    }
